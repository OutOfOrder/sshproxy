#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 09, 17:16:43 by david
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA

import sys, threading
import optparse

import paramiko
from paramiko import AuthenticationException

from registry import Registry
import util, log, proxy, pool
from options import OptionParser
from util import chanfmt
from backend import get_backend
from config import get_config
from message import Message
from ptywrap import PTYWrapper
from console import Console
from acl import ACLDB


class Server(Registry, paramiko.ServerInterface):
    _class_id = "Server"
    def __reginit__(self, client, addr, host_key_file):
        self.pwdb = get_backend()
        self.client = client
        self.client_addr = addr
        self.host_key = paramiko.DSSKey(filename=host_key_file)
        self.event = threading.Event()
        self.args = []
        self._remotes = {}

    ### STANDARD PARAMIKO SERVER INTERFACE

    def check_global_request(self, kind, chanid):
        log.devdebug("check_global_request %s %s", kind, chanid)
        # XXX: disabled for the moment
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
        if kind in [ 'tcpip-forward' ]:
            return paramiko.OPEN_SUCCEEDED
        log.debug('Ohoh! What is this "%s" channel type ?', kind)
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED


    def check_channel_request(self, kind, chanid):
        log.devdebug("check_channel_request %s %s", kind, chanid)
        if kind in [ 'session', 'direct-tcpip', 'tcpip-forward' ]:
            return paramiko.OPEN_SUCCEEDED
        log.debug('Ohoh! What is this "%s" channel type ?', kind)
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED


    def check_auth_password(self, username, password):
        if self.valid_auth(username=username, password=password):
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED


    def check_auth_publickey(self, username, key):
        if self.valid_auth(username=username, pkey=key.get_base64()):
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'password,publickey'

    def check_channel_shell_request(self, channel):
        log.devdebug("check_channel_shell_request")
        self.event.set()
        return True

    def check_channel_subsystem_request(self, channel, name):
        log.devdebug("check_channel_subsystem_request %s %s", channel, name)
        return paramiko.ServerInterface.check_channel_subsystem_request(self,
                                            channel, name)

    def check_channel_exec_request(self, channel, command):
        log.devdebug('check_channel_exec_request %s %s', channel, command)
        self.set_channel(channel)
        value = self.set_exec_args(command)
        self.event.set()
        return value

    def check_channel_pty_request(self, channel, term, width, height,
                                  pixelwidth, pixelheight, modes):
        self.set_term(term, width, height)
        return True


    ### SSHPROXY SERVER INTERFACE

    def valid_auth(self, username, password=None, pkey=None):
        if not self.pwdb.authenticate(username=username,
                                      auth_tokens={'password': password,
                                                   'pkey': pkey},
                                      ip_addr=self.client_addr[0]):
            if pkey is not None:
                self.unauth_key = pkey
            return False
        else:
            if pkey is None and hasattr(self, 'unauth_key'):
                if util.istrue(get_config('sshproxy')['auto_add_key']):
                    client = self.pwdb.get_client()
                    client.set_tokens(pkey=self.unauth_key)
                    client.save()
            self.username = username
            return True


    def set_username(self, username):
        self.username = username


    def set_channel(self, chan):
        self.chan = chan


    def set_term(self, term, width, height):
        self.term, self.width, self.height = term, width, height


    def set_exec_args(self, argstr):
        # XXX: naive arguments splitting
        self.args = argstr.strip().split()
        return True


    def is_admin(self):
        return self.is_authenticated() and self.pwdb.is_admin()

            
    def is_authenticated(self):
        return hasattr(self, 'username')


    def add_cmdline_options(self, parser):
        namespace = {
                'client': self.pwdb.clientdb.get_tags(),
                }
        if ACLDB().check('opt_list_sites', **namespace):
            parser.add_option("-l", "--list-sites", dest="action",
                    help="list allowed sites",
                    action="store_const",
                    const='list_sites',
                    )
        if ACLDB().check('opt_get_pkey', **namespace):
            parser.add_option("-g", "--get-pkey", dest="action",
                    help="display public key for user@host.",
                    action="store_const",
                    const="get_pkey",
                    )

    def parse_cmdline(self, args):
        parser = OptionParser(self.chan)
        # add options from a mapping or a Registry callback
        self.add_cmdline_options(parser)
        return parser.parse_args(args)


    def opt_list_sites(self, options, *args):
        result = []
        sites = self.pwdb.list_allowed_sites()
        if len(sites):
            name_width = max([ len(e.get_tags().login) + len(e.get_tags().name)
                                            for e in sites ])
            for site in sites:
                sid = '%s@%s' % (site.get_tags().login, site.get_tags().name)
                result.append('%s %s\n' % (sid,
                                    ' '*(name_width + 1 - len(sid)))) 
        result.append('\nTOTAL: %d\n' % len(sites))

        self.chan.send(chanfmt(''.join(result)))


    def opt_get_pkey(self, options, *args):
        result = []
        for site in args:
            spkey = util.get_site_pkey(site)
            if spkey is None:
                result.append("%s: No such entry" % site)
                continue
        
            if len(spkey):
                result.append('%s: %s' % (site, ' '.join(spkey)))
            else:
                result.append("%s: No pkey found" % site)

        if not result:
            result.append('Please give at least a site.')
        self.chan.send(chanfmt('\n'.join(result)+'\n'))


    def do_eval_options(self, options, args):
        if options.action and hasattr(self, 'opt_%s' % options.action):
            getattr(self, 'opt_%s' % options.action)(options, *args)


    def start(self):
        # start transport for the client
        self.transport = paramiko.Transport(self.client)
        self.transport.set_log_channel("paramiko")
        # debug !!
        #transport.set_hexdump(1)
    
        try:
            self.transport.load_server_moduli()
        except:
            raise
    
        self.transport.add_server_key(self.host_key)
    
        # start the server interface
        negotiation_ev = threading.Event()
        #self.transport.set_subsystem_handler('sftp', paramiko.SFTPServer,
        #                                               ProxySFTPServer)
        #self.transport.set_subsystem_handler('tcpip-forward',
        #                                     ForwardHandler,
        #                                     ProxyForward)

        self.transport.start_server(negotiation_ev, self)

        while not negotiation_ev.isSet():
            negotiation_ev.wait(0.5)
        if not self.transport.is_active():
            raise 'ERROR: SSH negotiation failed'

        chan = self.transport.accept(60)
        if chan is None:
            log.error('ERROR: cannot open the channel. '
                      'Check the transport object. Exiting..')
            return
        log.info('Authenticated %s', self.username)
        self.event.wait(15)
        if not self.event.isSet():
            log.error('ERROR: client never asked for a shell or a command.'
                        ' Exiting.')
            sys.exit(1)

        self.set_channel(chan)
        
        try:
            self.do_work()
        finally:
            # close what we can
            for item in ('chan', 'transport'):
                try:
                    getattr(self, item).close()
                except:
                    pass

        return


    def do_console(self, conn=None):
        namespace = {
                'client': self.pwdb.clientdb.get_tags(),
                }
        if not ACLDB().check('console_session', **namespace):
            self.chan.send(chanfmt("ERROR: You are not allowed to"
                                    " open a console session.\n"))
            return False
        return ConsoleBackend(self, conn).loop()


    def do_scp(self):
        args = []
        argv = self.args[1:]
        while True:
            if argv[0][0] == '-':
                args.append(argv.pop(0))
                continue
            break
        site, path = argv[0].split(':', 1)

        if not self.pwdb.authorize(site):
            self.chan.send(chanfmt("ERROR: %s does not exist in your scope\n" %
                                                                    site))
            return False

        if '-t' in args:
            upload = True
        else:
            upload = False

        (upload and self.pwdb.tags.add_tag('scp_dir', 'upload')
                 or self.pwdb.tags.add_tag('scp_dir', 'download'))
        self.pwdb.tags.add_tag('scp_path', path or '.')
        self.pwdb.tags.add_tag('scp_args', ' '.join(args))

        namespace = {
                'client': self.pwdb.clientdb.get_tags(),
                'site': self.pwdb.sitedb.get_tags(),
                'proxy': self.pwdb.tags,
                }
        # check ACL for the given direction, then if failed, check general ACL
        if not (((upload and ACLDB().check('scp_upload', **namespace)) or
                (not upload and ACLDB().check('scp_download', **namespace))) or
                ACLDB().check('scp_transfer', **namespace)):
            self.chan.send(chanfmt("ERROR: You are not allowed to"
                                    " do scp file transfert in this"
                                    " directory or direction on %s\n" % site))
            return False

        try:
            proxy.ProxyScp(self).loop()
        except AuthenticationException, msg:
            self.chan.send("\r\n ERROR: %s." % msg +
                      "\r\n Please report this error "
                      "to your administrator.\r\n\r\n")
            return False
        return True


    def do_remote_execution(self):
        site = self.args.pop(0)
        if not self.pwdb.authorize(site):
            self.chan.send(chanfmt("ERROR: %s does not exist in "
                                            "your scope\n" % site))
            return False

        self.pwdb.tags.add_tag('cmdline', ' '.join(self.args))
        if not ACLDB().check('remote_exec',
                                client=self.pwdb.clientdb.get_tags(),
                                site=self.pwdb.sitedb.get_tags(),
                                proxy=self.pwdb.tags):
            self.chan.send(chanfmt("ERROR: You are not allowed to"
                                    " exec that command on %s"
                                    "\n" % site))
            return False
        try:
            proxy.ProxyCmd(self).loop()
        except AuthenticationException, msg:
            self.chan.send("\r\n ERROR: %s." % msg +
                      "\r\n Please report this error "
                      "to your administrator.\r\n\r\n")
            return False
        return True


    def do_shell_session(self):
        site = self.args.pop(0)
        if not self.pwdb.authorize(site):
            self.chan.send(chanfmt("ERROR: %s does not exist in "
                                            "your scope\n" % site))
            return False

        if not ACLDB().check('shell_session',
                            client=self.pwdb.clientdb.get_tags(),
                            site=self.pwdb.sitedb.get_tags()):
            self.chan.send(chanfmt("ERROR: You are not allowed to"
                                    " open a shell session on %s"
                                    "\n" % site))
            return False
        conn = proxy.ProxyShell(self)
        log.info("Connecting to %s", site)
        try:
            ret = conn.loop()
        except AuthenticationException, msg:
            self.chan.send("\r\n ERROR: %s." % msg +
                           "\r\n Please report this error "
                           "to your administrator.\r\n\r\n")
            return False

        except:
            self.chan.send("\r\n ERROR: It seems you found a bug."
                           "\r\n Please report this error "
                           "to your administrator.\r\n\r\n")
            raise
        
        if ret == util.CLOSE:
            # if the direct connection closed, then exit cleanly
            conn = None
            log.info("Exiting %s", site)
            return True
        # else go to the console
        return self.do_console(conn)


    def do_work(self):
        # this is a connection to the proxy console
        if not len(self.args):
            return self.do_console()

        else:
            # this is an option list
            if len(self.args[0]) and self.args[0][0] == '-':
                try:
                    options, args = self.parse_cmdline(self.args)
                except 'EXIT':
                    return False
                
                return self.do_eval_options(options, args)
    
    
            # this is an scp file transfer
            elif self.args[0] == 'scp':
                return self.do_scp()

            else:
                site = self.args[0]

                # this is a remote command execution
                if len(self.args) > 1:
                    return self.do_remote_execution()

                # this is a shell session
                else:
                    return self.do_shell_session()

        # Should never get there
        return False

Server.register()


class ConsoleBackend(Registry):
    _class_id = "ConsoleBackend"
    def __reginit__(self, client, conn=None):
        conf = get_config('sshproxy')
        self.maxcon = conf['max_connections']

        self.client = client
        self.chan = client.chan

        self.msg = Message()

        self.main_console = PTYWrapper(self.chan, self.PtyConsole, self.msg,
                                    client.is_admin())
        self.status = self.msg.get_parent_fd()

        self.cpool = pool.get_connection_pool()
        self.cid = None
        if conn is not None:
            self.cid = self.cpool.add_connection(conn)

    @staticmethod
    def PtyConsole(*args, **kwargs):
        Console(*args, **kwargs).cmdloop()

    def loop(self):
        while True:

            self.status.reset()
        
            data = self.main_console.loop()
            if data is None:
                break
            try:
                action, data = data.split(' ', 1)
            except ValueError:
                action = data.strip()
                data = ''

            method = 'cmd_'+action
            if hasattr(self, method):
                method = getattr(self, method)
                if callable(method):
                    response = method(data)
                    if response is None:
                        break
            # status.response() absolutely NEEDS to be called once an action
            # has been processed, otherwise you may experience hang ups.
                    self.status.response(response)
                    continue
            # if inexistant or no callable
            self.status.response('ERROR: Unknown action %s' % action)
            log.error('ERROR: Unknown action %s' % action)

        self.close()

    def cmd_open(self, args):
        if self.maxcon and len(self.cpool) >= self.maxcon:
            return 'ERROR: Max connection count reached'
        sitename = args.strip()
        if sitename == "":
            return 'ERROR: where to?'
        #try:
        #    sitename = self.client.set_remote(sitename)
        #except util.SSHProxyAuthError, msg:
        if not self.client.pwdb.authorize(sitename):
            log.error("ERROR(open): %s", msg)
            return ("ERROR: site does not exist or you don't "
                            "have sufficient rights")

        conn = proxy.ProxyShell(self.client)

        cid = self.cpool.add_connection(conn)
        while True:
            if not conn:
                ret = 'ERROR: no connection id %s' % cid
                break
            try:
                ret = conn.loop()
            except:
                self.chan.send("\r\n ERROR: It seems you found a bug."
                               "\r\n Please report this error "
                               "to your administrator.\r\n\r\n")
                self.chan.close()
                raise
            if ret == util.CLOSE:
                self.cpool.del_connection(cid)
            elif ret >= 0:
                self.cid = cid = ret
                conn = self.cpool.get_connection(cid)
                continue
            ret = 'OK'
            break
        if not ret:
            ret = 'OK'
        return ret

    def cmd_switch(self, args):
        # switch between one connection to the other
        if not self.cpool:
            return 'ERROR: no opened connection.'
        args = args.strip()
        if args:
            cid = int(args)
        else:
            if self.cid is not None:
                cid = self.cid
            else:
                cid = 0
        while True:
            conn = self.cpool.get_connection(cid)
            if not conn:
                ret = 'ERROR: no id %d found' % cid
                break
            ret = conn.loop()
            if ret == util.CLOSE:
                self.cpool.del_connection(cid)
            elif ret >= 0:
                self.cid = cid = ret
                continue
            ret = 'OK'
            break
        return ret

    def cmd_close(self, args):
        # close connections
        args = args.strip()

        # there must exist open connections
        if self.cpool:
            # close all connections
            if args == 'all':
                l = len(self.cpool)
                while len(self.cpool):
                    self.cpool.del_connection(0)
                return '%d connections closed' % l
            # argument must be a digit
            elif args != "":
                if args.isdigit():
                    try:
                        cid = int(args)
                        self.cpool.del_connection(cid)
                        msg="connection %d closed" % cid
                    except UnboundLocalError:
                        msg = 'ERROR: unknown connection %s' % args
                    return msg
                else:
                    return 'ERROR: argument must be a digit'
            else:
                return 'ERROR: give an argument'
        else:
            return 'ERROR: no open connection'

    def cmd_list_conn(self, args):
        # show opened connections
        l = []
        i = 0
        # list the open connections
        for c in self.cpool.list_connections():
            l.append('%d %s\n' % (i, c.name))
            i = i + 1
        if not len(l):
            return 'ERROR: no opened connections'
        else:
            # send the connection list
            return ''.join(l)

    def cmd_whoami(self, args):
        # whoami command
        return '%s' % (self.client.username)

    def cmd_exit_verify(self, args):
        # check open connections for exit
        if self.cpool:
            return 'ERROR: close all connections first!'
        else:
            return None

    def cmd_sites(self, args):
        # dump the listing of all sites we're allowed to connect to
        # TODO: see console.py : Console._sites()
        return 'OK'

    def close(self):
        self.chan.close()
        log.info('Client exits now!')


ConsoleBackend.register()
