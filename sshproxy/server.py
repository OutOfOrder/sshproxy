#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Nov 20, 23:34:43 by david
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

import paramiko
from paramiko import AuthenticationException

from registry import Registry
import cipher, util, log, proxy
from options import OptionParser
from util import chanfmt
from backend import Backend
from config import get_config
from acl import ACLDB, ProxyNamespace
from dispatcher import Dispatcher


class Server(Registry, paramiko.ServerInterface):
    _class_id = "Server"
    _singleton = True

    def __reginit__(self, client, addr, ipc, host_key_file):
        self.pwdb = Backend()
        self.client = client
        self.client_addr = addr
        self.ipc = ipc
        self.host_key = paramiko.DSSKey(filename=host_key_file)
        self.ip_addr, self.port = client.getsockname()
        self.event = threading.Event()
        self.args = []
        self._remotes = {}
        self.exit_status = -1

    def setup_forward_handler(self, check_channel_direct_tcpip_request):
        if check_channel_direct_tcpip_request:
            self.check_channel_direct_tcpip_request = \
                                        check_channel_direct_tcpip_request  

    def check_direct_tcpip_acl(self, chanid, origin, destination):
        o_ip, o_port = origin
        d_ip, d_port = destination
        proxyns = ProxyNamespace()
        proxyns['forward_ip'] = origin[0]
        proxyns['forward_port'] = origin[1]
        namespace = {
                'client': Backend().get_client_tags(),
                'site': Backend().get_site_tags(),
                'proxy': proxyns,
                }
        if not (ACLDB().check('local_forwarding', **namespace)):
            log.debug("Local Port Forwarding not allowed by ACLs")
            self.chan_send("Local Port Forwarding not allowed by ACLs\n")
            return False
        log.debug("Local Port Forwarding allowed by ACLs")
        return True

    def check_channel_x11_request(self, channel, single_connection,
                        x11_auth_proto, x11_auth_cookie, x11_screen_number):
        class X11Channel(object):
            pass
        x11 = X11Channel()
        x11.single_connection = single_connection
        x11.x11_auth_proto = x11_auth_proto
        x11.x11_auth_cookie = x11_auth_cookie
        x11.x11_screen_number = x11_screen_number
        self.x11 = x11
        return True

    def check_x11_acl(self):
        if not hasattr(self, 'x11'):
            log.debug("X11Forwarding not requested by the client")
            return False
        proxyns = ProxyNamespace()
        namespace = {
                'client': Backend().get_client_tags(),
                'site': Backend().get_site_tags(),
                'proxy': proxyns,
                }
        if not (ACLDB().check('x11_forwarding', **namespace)):
            log.debug("X11Forwarding not allowed by ACLs")
            return False
        log.debug("X11Forwarding allowed by ACLs")
        return True

    def check_remote_port_forwarding(self):
        if (hasattr(self, 'tcpip_forward_ip') and
            hasattr(self, 'tcpip_forward_port')):
            proxyns = ProxyNamespace()
            proxyns['forward_ip'] = self.tcpip_forward_ip
            proxyns['forward_port'] = self.tcpip_forward_port
            namespace = {
                    'client': Backend().get_client_tags(),
                    'site': Backend().get_site_tags(),
                    'proxy': proxyns,
                    }
            if not (ACLDB().check('remote_forwarding', **namespace)):
                log.debug("Remote Port Forwarding not allowed by ACLs")
                self.chan_send("Remote Port Forwarding not allowed by ACLs\n")
                return False
            log.debug("Remote Port Forwarding allowed by ACLs")
            return True
        return False

    ### STANDARD PARAMIKO SERVER INTERFACE
    
    def check_channel_unhandled_request(self, channel, kind, want_reply, m):
        log.devdebug("check_unhandled_channel_request %s", kind)
        return False


    def check_global_request(self, kind, m):
        log.devdebug("check_global_request %s", kind)
        if kind in [ 'tcpip-forward' ]:
            self.tcpip_forward_ip = m.get_string()
            self.tcpip_forward_port = m.get_int()
            log.debug('tcpip-forward %s:%s' % (self.tcpip_forward_ip,
                                                    self.tcpip_forward_port))
            # TODO: check ACL
            return (self.tcpip_forward_port,)
        log.debug('Ohoh! What is this "%s" channel type ?', kind)
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED


    def check_channel_request(self, kind, chanid):
        log.devdebug("check_channel_request %s %s", kind, chanid)
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        if kind == 'direct-tcpip':
            # TODO: check ACL
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

    def _valid_auth(self, username, password=None, pkey=None):
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
                    client.set_tokens(pkey='%s %s@%s' % (self.unauth_key,
                                                username, self.client_addr[0]))
                    client.save()
            self.username = username
            self.ipc.request('set_client username=%s' % username)
            return True

    def valid_auth(self, username, password=None, pkey=None):
        if not Backend().authenticate(username=username, auth_tokens={
                                            'password': password,
                                            'pkey': pkey,
                                            'ip_addr': self.client_addr[0]},
                                      ip_addr=self.client_addr[0]):
            return False

        self.username = username
        self.ipc.request('set_client username=%s' % username)
        return True

    def message_client(self, msg):
        self.queue_message(msg)

    def queue_message(self, msg=None):
        chan = getattr(self, 'chan', None)
        if not hasattr(self, 'qmsg'):
            self.qmsg = []
        if msg is not None:
            self.qmsg.append(msg)
        if not chan:
            return
        while len(self.qmsg): 
            chan.send(chanfmt(self.qmsg.pop(0)))



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
        if ACLDB().check('admin', **namespace):
            parser.add_option("", "--admin", dest="action",
                    help="run administrative commands",
                    action="store_const",
                    const='admin',
                    )
        if ACLDB().check('console_session', **namespace):
            parser.add_option("", "--console", dest="action",
                    help="open administration console",
                    action="store_const",
                    const='console',
                    )
        if ACLDB().check('opt_list_sites', **namespace):
            parser.add_option("-l", "--list-sites", dest="action",
                    help="list allowed sites",
                    action="store_const",
                    const='list_sites',
                    )
        if ACLDB().check('opt_get_pkey', **namespace):
            parser.add_option("", "--get-pkey", dest="action",
                    help="display public key for user@host.",
                    action="store_const",
                    const="get_pkey",
                    )

    def parse_cmdline(self, args):
        usage = """
        pssh [options]
        pssh [user@site [cmd]]
        """
        parser = OptionParser(self.chan, usage=usage)
        # add options from a mapping or a Registry callback
        self.add_cmdline_options(parser)
        return parser.parse_args(args)


    def opt_admin(self, options, *args):
        if not len(args):
            self.chan.send(chanfmt('Missing argument, try --admin help '
                                   'to get a list of commands.\n'))
            return

        resp = self.ipc.request('%s' % ' '.join(args))
        self.chan.send(chanfmt(resp+'\n'))


    def opt_console(self, options, *args):
        return self.do_console()

    def opt_list_sites(self, options, *args):
        self.chan_send(self.run_cmd('list_sites %s'% ' '.join(args)))

    def chan_send(self, s):
        chan = self.chan
        s = chanfmt(s)
        sz = len(s)
        while sz:
            sent = chan.send(s)
            if sent:
                s = s[sent:]
                sz = sz - sent

    def run_cmd(self, cmd):
        return self.dispatcher.dispatch(cmd) + '\n'

    def readlines(self):
        buffer = []
        chan = self.chan
        chan.setblocking(True)
        while True:
            data = chan.recv(4096)
            if not data:
                chan.shutdown_read()
                yield ''.join(buffer)
                break

            if '\n' in data:
                yield ''.join(buffer) + data[:data.index('\n')+1]
                buffer = [ data[data.index('\n')+1:] ]

            else:
                buffer.append(data)


    def console_no_pty(self):
        from server import Server
        chan = self.chan
        for data in self.readlines():
            if not data:
                continue
            response = self.run_cmd(data)
            self.chan_send(response)



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
        namespace = { 'client': Backend().get_client_tags(), }
        self.dispatcher = Dispatcher(self.ipc, namespace)
        
        try:
            self.do_work()
        finally:
            if self.chan.active:
                self.chan.send_exit_status(self.exit_status)
            # close what we can
            for item in ('chan', 'transport', 'ipc'):
                try:
                    getattr(self, item).close()
                except:
                    pass

        return


    def do_console(self):
        namespace = {
                'client': self.pwdb.clientdb.get_tags(),
                }
        if not ACLDB().check('console_session', **namespace):
            self.chan.send(chanfmt("ERROR: You are not allowed to"
                                    " open a console session.\n"))
            return False
        self.ipc.request("set_client type=console")
        if hasattr(self, 'term'):
            return self.dispatcher.console()
        else:
            return self.console_no_pty()


    def do_scp(self):
        args = []
        argv = self.args[1:]
        while True:
            if argv[0][0] == '-':
                args.append(argv.pop(0))
                continue
            break
        site, path = argv[0].split(':', 1)

        if not self.pwdb.authorize(site, need_login=True):
            self.chan.send(chanfmt("ERROR: %s does not exist in your scope\n" %
                                                                    site))
            return False

        if '-t' in args:
            upload = True
            scpdir = 'upload'
        else:
            upload = False
            scpdir = 'download'

        proxyns = ProxyNamespace()
        proxyns['scp_dir'] = scpdir
        proxyns['scp_path'] = path or '.'
        proxyns['scp_args'] = ' '.join(args)

        namespace = {
                'client': self.pwdb.clientdb.get_tags(),
                'site': self.pwdb.sitedb.get_tags(),
                }
        # check ACL for the given direction, then if failed, check general ACL
        if not ((ACLDB().check('scp_' + scpdir, **namespace)) or
                ACLDB().check('scp_transfer', **namespace)):
            self.chan.send(chanfmt("ERROR: You are not allowed to"
                                    " do scp file transfert in this"
                                    " directory or direction on %s\n" % site))
            return False

        self.ipc.request("set_client type=scp_%s login=%s name=%s" % (scpdir,
                                         self.pwdb.sitedb.get_tags()['login'],
                                         self.pwdb.sitedb.get_tags()['name']))
        conn = proxy.ProxyScp(self.chan, self.connect_site(), self.ipc)
        try:
            conn.loop()
        except AuthenticationException, msg:
            self.chan.send("\r\n ERROR: %s." % msg +
                      "\r\n Please report this error "
                      "to your administrator.\r\n\r\n")
            return False
        return True


    def do_remote_execution(self):
        site = self.args.pop(0)
        if not self.pwdb.authorize(site, need_login=True):
            self.chan.send(chanfmt("ERROR: %s does not exist in "
                                            "your scope\n" % site))
            return False

        proxyns = ProxyNamespace()
        proxyns['cmdline'] = ' '.join(self.args)
        if not ACLDB().check('remote_exec',
                                client=self.pwdb.clientdb.get_tags(),
                                site=self.pwdb.sitedb.get_tags()):
            self.chan.send(chanfmt("ERROR: You are not allowed to"
                                    " exec that command on %s"
                                    "\n" % site))
            return False
        self.ipc.request("set_client type=remote_exec login=%s name=%s" % 
                                        (self.pwdb.sitedb.get_tags()['login'],
                                         self.pwdb.sitedb.get_tags()['name']))
        conn = proxy.ProxyCmd(self.chan, self.connect_site(), self.ipc)
        try:
            ret, self.exit_status = conn.loop()
        except AuthenticationException, msg:
            self.chan.send("\r\n ERROR: %s." % msg +
                      "\r\n Please report this error "
                      "to your administrator.\r\n\r\n")
            return False
        conn = None
        log.info("Exiting %s", site)
        return True


    def do_shell_session(self):
        site = self.args.pop(0)
        if not self.pwdb.authorize(site, need_login=True):
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
        self.ipc.request("set_client type=shell_session login=%s name=%s" % 
                                        (self.pwdb.sitedb.get_tags()['login'],
                                         self.pwdb.sitedb.get_tags()['name']))
        log.info("Connecting to %s", site)
        conn = proxy.ProxyShell(self.chan, self.connect_site(), self.ipc)
        try:
            ret, self.exit_status = conn.loop()
        except AuthenticationException, msg:
            self.chan.send("\r\n ERROR: %s." % msg +
                           "\r\n Please report this error "
                           "to your administrator.\r\n\r\n")
            return False

        except KeyboardInterrupt:
            return True
        except Exception, e:
            self.chan.send("\r\n ERROR: It seems you found a bug."
                           "\r\n Please report this error "
                           "to your administrator.\r\n"
                           "Exception class: <%s>\r\n\r\n"
                                    % e.__class__.__name__)
            
            raise
        
        if ret == util.CLOSE:
            # if the direct connection closed, then exit cleanly
            conn = None
            log.info("Exiting %s", site)
            return True
        # else go to the console
        return self.do_console()


    # XXX: stage2: make it easier to extend
    # make explicit the stage automaton
    def do_work(self):
        # empty the message queue now we've got a valid channel
        self.queue_message()
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

    def connect_site(self, site_tags=None, site_ref=None):
        tags = {
                'client': Backend().get_client_tags(),
                'site': site_tags or Backend().get_site_tags(),
                'proxy': ProxyNamespace(),
                }
        name = '%s@%s' % (tags['site'].login,
                          tags['site'].name)
        hostkey = tags['proxy'].get('hostkey', None) or None

        if site_ref is None:
            site_ref = (tags['site'].ip_address, int(tags['site'].port))

        transport = paramiko.Transport(site_ref)
        transport.start_client()

        if hostkey is not None:
            transport._preferred_keys = [ hostkey.get_name() ]

            key = transport.get_remote_server_key()
            if (key.get_name() != hostkey.get_name() 
                                                or str(key) != str(hostkey)):
                log.error('Bad host key from server (%s).' % name)
                raise AuthenticationError('Bad host key from server (%s).'
                                                                    % name)
            log.info('Server host key verified (%s) for %s' % (key.get_name(), 
                                                                    name))

        pkey = cipher.decipher(tags['site'].get('pkey', ''))
        password = cipher.decipher(tags['site'].get('password', ''))

        authentified = False
        if pkey:
            pkey = util.get_dss_key_from_string(pkey)
            try:
                transport.auth_publickey(tags['site'].login, pkey)
                authentified = True
            except AuthenticationException:
                log.warning('PKey for %s was not accepted' % name)

        if not authentified and password:
            try:
                transport.auth_password(tags['site'].login, password)
                authentified = True
            except AuthenticationException:
                log.error('Password for %s is not valid' % name)
                raise

        if not authentified:
            raise AuthenticationException('No valid authentication token for %s'
                                                                % name)

        chan = transport.open_session()
        chan.settimeout(1.0)

        return chan





Server.register()


