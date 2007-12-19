#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Dec 19, 22:45:05 by david
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

import os, sys, threading, socket

import paramiko
from paramiko import AuthenticationException

from registry import Registry
import cipher, util, log, proxy
import ipc
from options import OptionParser
from util import chanfmt, SSHProxyError
from config import get_config
from dispatcher import Dispatcher


class IPCClientInterface(ipc.IPCInterface):
    def __init__(self, server):
        self.server = server

    def __call__(self, chan):
        # simulate an instanciation
        ipc.IPCInterface.__init__(self, chan)
        return self


class Server(Registry, paramiko.ServerInterface):
    _class_id = "Server"
    _singleton = True

    def __reginit__(self, client, addr, host_key_file):
        self.client = client
        self.client_addr = addr
        ipc_address = get_config('sshproxy').get('ipc_address',
                                                'sshproxy-control')
        handler = IPCClientInterface(self)
        try:
            self.monitor = ipc.IPCClient(ipc_address, handler=handler)
        except:
            log.exception("Couldn't create IPC channel to monitor")
            raise
        self.host_key = paramiko.DSSKey(filename=host_key_file)
        #self.ip_addr, self.port = client.getsockname()
        self.event = threading.Event()
        self.args = []
        self._remotes = {}
        self.exit_status = -1

    def get_ns_tag(self, namespace, tag, default=None):
        return self.monitor.call('get_ns_tag', namespace=namespace,
                                               tag=tag,
                                               default=default)

    def update_ns(self, name, value):
        return self.monitor.call('update_ns', name=name, value=value)

    def check_acl(self, acl_name):
        return self.monitor.call('check_acl', acl_name)

    def authorize(self, user_site, need_login=True):
        return self.monitor.call('authorize', user_site=user_site,
                                              need_login=need_login)


    def setup_forward_handler(self, check_channel_direct_tcpip_request):
        if check_channel_direct_tcpip_request:
            self.check_channel_direct_tcpip_request = \
                                        check_channel_direct_tcpip_request  

    def check_direct_tcpip_acl(self, chanid, origin, destination):
        o_ip, o_port = origin
        d_ip, d_port = destination
        self.update_ns('proxy', {
                                'forward_ip': origin[0],
                                'forward_port': origin[1]
                                })
        if not (self.check_acl('local_forwarding')):
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
        if not (self.check_acl('x11_forwarding')):
            log.debug("X11Forwarding not allowed by ACLs")
            return False
        log.debug("X11Forwarding allowed by ACLs")
        return True

    def check_remote_port_forwarding(self):
        if (hasattr(self, 'tcpip_forward_ip') and
            hasattr(self, 'tcpip_forward_port')):
            self.update_ns('proxy', {
                                    'forward_ip': self.tcpip_forward_ip,
                                    'forward_port': self.tcpip_forward_port
                                    })
            if not (self.check_acl('remote_forwarding')):
                log.debug("Remote Port Forwarding not allowed by ACLs")
                self.chan_send("Remote Port Forwarding not allowed by ACLs\n")
                return False
            log.debug("Remote Port Forwarding allowed by ACLs")
            return True
        return False

    ### STANDARD PARAMIKO SERVER INTERFACE
    
    def check_unhandled_channel_request(self, channel, kind, want_reply, m):
        log.debug("check_unhandled_channel_request %s", kind)
        if kind == "auth-agent-req@openssh.com":
            return True
        return False


    def check_global_request(self, kind, m):
        log.devdebug("check_global_request %s", kind)
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED


    def check_port_forward_request(self, address, port):
        log.devdebug("check_port_forward_request %s %s", address, port)
        self.tcpip_forward_ip = address
        self.tcpip_forward_port = port
        log.debug('tcpip-forward %s:%s' % (self.tcpip_forward_ip,
                                                    self.tcpip_forward_port))
        return str(self.tcpip_forward_port)


    def check_channel_request(self, kind, chanid):
        log.devdebug("check_channel_request %s %s", kind, chanid)
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        if self.valid_auth(username=username, password=password):
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED


    def check_auth_publickey(self, username, key):
        if self.valid_auth(username=username, pubkey=key.get_base64()):
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

    def window_change_handler(self):
        return False

    def setup_window_change_handler(self, window_change_handler):
        self.window_change_handler = window_change_handler

    def check_channel_window_change_request(self, channel, width, height,
                                                pixelwidth, pixelheight):
        log.devdebug('window_change: %s %s' % (width, height))
        self.set_term(self.term, width, height)
        return self.window_change_handler()

    ### SSHPROXY SERVER INTERFACE
    def valid_auth(self, username, password=None, pubkey=None):
        if not self.monitor.call('authenticate',
                                    username=username,
                                    password=password,
                                    pubkey=pubkey,
                                    ip_addr=self.client_addr[0]):
            self._unauth_pubkey = pubkey
            return False

        self.username = username
        self.monitor.call('update_ns', 'client', {'username': username})

        if hasattr(self, '_unauth_pubkey') and self._unauth_pubkey:
            if self.monitor.call('add_client_pubkey', self._unauth_pubkey):
                self.message_client("WARNING: Your public key"
                                        " has been added to the keyring\n")

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
        return self.is_authenticated() and self.monitor.call('is_admin')

            
    def is_authenticated(self):
        return hasattr(self, 'username')


    def add_cmdline_options(self, parser):
        if self.check_acl('admin'):
            parser.add_option("", "--admin", dest="action",
                    help=_(u"run administrative commands"),
                    action="store_const",
                    const='admin',
                    )
        if self.check_acl('console_session'):
            parser.add_option("", "--console", dest="action",
                    help=_(u"open administration console"),
                    action="store_const",
                    const='console',
                    )
        if self.check_acl('opt_list_sites'):
            parser.add_option("-l", "--list-sites", dest="action",
                    help=_(u"list allowed sites"),
                    action="store_const",
                    const='list_sites',
                    )
        if self.check_acl('opt_get_pubkey') or self.check_acl('opt_get_pkey'):
            parser.add_option("", "--get-pubkey", dest="action",
                    help=_(u"display public key for user@host."),
                    action="store_const",
                    const="get_pubkey",
                    )

    def parse_cmdline(self, args):
        usage = u"""
        pssh [options]
        pssh [user@site [cmd]]
        """
        parser = OptionParser(self.chan, usage=usage)
        # add options from a mapping or a Registry callback
        self.add_cmdline_options(parser)
        return parser.parse_args(args)


    def opt_admin(self, options, *args):
        if not len(args):
            self.chan.send(chanfmt(_(u'Missing argument, try --admin help '
                                   'to get a list of commands.\n')))
            return

        resp = self.dispatcher.console('%s' % ' '.join(args)) or ''
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
        result = self.dispatcher.dispatch(cmd) or ''
        return result + '\n'

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



    def opt_get_pubkey(self, options, *args):
        result = []
        for site in args:
            spubkey = util.get_site_pubkey(site)
            if spubkey is None:
                result.append(_(u"%s: No privkey tag found") % site)
                continue
        
            if len(spubkey):
                result.append('%s: %s' % (site, ' '.join(spubkey)))
            else:
                result.append(_(u"%s: No privkey found") % site)

        if not result:
            result.append(_(u'Please give at least a site.'))
        self.chan.send(chanfmt('\n'.join(result)+'\n'))


    def do_eval_options(self, options, args):
        if options.action and hasattr(self, 'opt_%s' % options.action):
            getattr(self, 'opt_%s' % options.action)(options, *args)

    def init_subsystems(self):
        #self.transport.set_subsystem_handler('sftp', paramiko.SFTPServer,
        #                                               ProxySFTPServer)
        pass

    def start(self):
        # start transport for the client
        self.transport = paramiko.Transport(self.client)
        self.transport.set_log_channel("paramiko")
        # debug !!
        #self.transport.set_hexdump(1)
    
        try:
            self.transport.load_server_moduli()
        except:
            raise
    
        self.transport.add_server_key(self.host_key)
    
        # start the server interface
        negotiation_ev = threading.Event()

        self.init_subsystems()

        self.transport.start_server(negotiation_ev, self)

        while not negotiation_ev.isSet():
            negotiation_ev.wait(0.5)
        if not self.transport.is_active():
            raise 'SSH negotiation failed'

        chan = self.transport.accept(60)
        if chan is None:
            log.error('cannot open the channel. '
                      'Check the transport object. Exiting..')
            return
        log.info('Authenticated %s', self.username)
        self.event.wait(15)
        if not self.event.isSet():
            log.error('client never asked for a shell or a command.'
                        ' Exiting.')
            sys.exit(1)

        self.set_channel(chan)
        namespace = self.monitor.call('get_namespace')
        self.dispatcher = Dispatcher(self.monitor, namespace)
        
        try:
            try:
                # this is the entry point after initialization have been done
                self.do_work()
                # after this point, client is disconnected
            except SSHProxyError, msg:
                log.exception(msg)
                chan.send(chanfmt(str(msg)+'\n'))
            except Exception, msg:
                log.exception("An error occured: %s" % msg)
                chan.send(chanfmt(_(u"An error occured: %s\n") % msg))
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
        if not self.check_acl('console_session'):
            self.chan.send(chanfmt(_(u"ERROR: You are not allowed to"
                                    " open a console session.\n")))
            return False
        self.monitor.call('update_ns', 'client', {'type': 'console'})
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

        if not self.authorize(site, need_login=True):
            self.chan.send(chanfmt(_(u"ERROR: %s does not exist "
                                      "in your scope\n") % site))
            return False

        if '-t' in args:
            upload = True
            scpdir = 'upload'
        else:
            upload = False
            scpdir = 'download'

        self.update_ns('proxy', {
                                'scp_dir': scpdir,
                                'scp_path': path or '.',
                                'scp_args': ' '.join(args)
                                })

        # check ACL for the given direction, then if failed, check general ACL
        if not ((self.check_acl('scp_' + scpdir)) or
                self.check_acl('scp_transfer')):
            self.chan.send(chanfmt(_(u"ERROR: You are not allowed to"
                                    " do scp file transfert in this"
                                    " directory or direction on %s\n") % site))
            return False

        self.update_ns('client', {
                            'type': 'scp_%s' % scpdir,
                            })
        conn = proxy.ProxyScp(self.chan, self.connect_site(), self.monitor)
        try:
            self.exit_status = conn.loop()
        except AuthenticationException, msg:
            self.chan.send("\r\n ERROR: %s." % msg +
                      "\r\n Please report this error "
                      "to your administrator.\r\n\r\n")
            return False
        return True


    def do_remote_execution(self):
        site = self.args.pop(0)
        if not self.authorize(site, need_login=True):
            self.chan.send(chanfmt(_(u"ERROR: %s does not exist in "
                                            "your scope\n") % site))
            return False

        self.update_ns('proxy', {'cmdline': (' '.join(self.args)).strip()})
        if not self.check_acl('remote_exec'):
            self.chan.send(chanfmt(_(u"ERROR: You are not allowed to"
                                    " exec that command on %s"
                                    "\n") % site))
            return False
        self.update_ns('client', {
                        'type': 'remote_exec',
                        })
        conn = proxy.ProxyCmd(self.chan, self.connect_site(), self.monitor)
        try:
            self.exit_status = conn.loop()
        except AuthenticationException, msg:
            self.chan.send(_(u"\r\n ERROR: %s.") % msg +
                      _(u"\r\n Please report this error "
                      "to your administrator.\r\n\r\n"))
            return False
        conn = None
        log.info("Exiting %s", site)
        return True


    def do_shell_session(self):
        log.devdebug(str(self.__class__))
        site = self.args.pop(0)
        if not self.authorize(site, need_login=True):
            self.chan.send(chanfmt(_(u"ERROR: %s does not exist in "
                                        "your scope\n") % site))
            return False

        if not self.check_acl('shell_session'):
            self.chan.send(chanfmt(_(u"ERROR: You are not allowed to"
                                    " open a shell session on %s"
                                    "\n") % site))
            return False
        self.update_ns('client', {
                            'type': 'shell_session'
                            })
        log.info("Connecting to %s", site)
        conn = proxy.ProxyShell(self.chan, self.connect_site(), self.monitor)
        try:
            self.exit_status = conn.loop()
        except AuthenticationException, msg:
            self.chan.send(_(u"\r\n ERROR: %s.") % msg +
                           _(u"\r\n Please report this error "
                           "to your administrator.\r\n\r\n"))
            return False

        except KeyboardInterrupt:
            return True
        except Exception, e:
            self.chan.send(_(u"\r\n ERROR: It seems you found a bug."
                           "\r\n Please report this error "
                           "to your administrator.\r\n"
                           "Exception class: <%s>\r\n\r\n")
                                    % e.__class__.__name__)
            
            raise
        
        # if the direct connection closed, then exit cleanly
        conn = None
        log.info("Exiting %s", site)
        return True


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
        tags = self.monitor.call('get_namespace')
        if site_tags:
            tags['site'] = site_tags

        name = '%s@%s' % (tags['site']['login'],
                          tags['site']['name'])
        hostkey = tags['proxy'].get('hostkey', None) or None

        if site_ref is None:
            if not tags['site'].get('ip_address'):
                raise ValueError('Missing site address in database')
            site_ref = (tags['site']['ip_address'],
                        int(tags['site'].get('port', 22)))

        import socket
        try:
            transport = paramiko.Transport(site_ref)
        except socket.error, msg:
            raise SSHProxyError("Could not connect to site %s: %s"
                                                % (name, msg[1]))
        except Exception, msg:
            raise SSHProxyError("Could not connect to site %s: %s"
                                                % (name, str(msg)))
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

        pubkey = cipher.decipher(tags['site'].get('pkey', ''))
        password = cipher.decipher(tags['site'].get('password', ''))

        authentified = False
        if pubkey:
            pubkey = util.get_dss_key_from_string(pubkey)
            try:
                transport.auth_publickey(tags['site']['login'], pubkey)
                authentified = True
            except AuthenticationException:
                log.warning('PKey for %s was not accepted' % name)

        if not authentified and password:
            try:
                transport.auth_password(tags['site']['login'], password)
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


