#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jun 21, 01:00:26 by david
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


import sys, os.path, socket, threading, traceback, signal

import paramiko

from ptywrap import PTYWrapper
from plugins import init_plugins, pluginInfo
from console import Console
from message import Message
from data import UserData, SiteData
from sftp import ProxySFTPServer
import proxy, util, pool, cipher
import config
from backend import get_backend

#paramiko.util.log_to_file('paramiko.log')

import log


class ProxyServer(paramiko.ServerInterface):
    
    def __init__(self, userdata):
        self.userdata = userdata
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        log.devdebug("check_channel_request %s %s", kind, chanid)
        if kind in [ 'session' ]:
            return paramiko.OPEN_SUCCEEDED
        log.debug('Ohoh! What is this "%s" channel type ?', kind)
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        if self.userdata.valid_auth(username=username, password=password):
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        if self.userdata.valid_auth(username=username, key=key.get_base64()):
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
        argv = command.split(' ', 1)
        print argv
        args = []
        if argv[0] == 'scp':
            while True:
                argv = argv[1].split(' ', 1)
                if argv[0][0] == '-':
                    args.append(argv[0])
                    continue
                break
            site, path = argv[0].split(':', 1)
            try:
                self.userdata.add_site(site)
            except util.SSHProxyError, msg:
                # we cannot explain here why the user gets rejected so we
                # just close the channel
                log.error('Site %s is not in your scope' % site)
                channel.close()
                self.event.set()
                return False
            sitedata = self.userdata.get_site(site)
            sitedata.set_sftp_path(path)
            sitedata.set_sftp_args(' '.join(args))
            sitedata.set_type('scp')
            self.event.set()
            return True
        elif argv[0][0] == '-':
            self.userdata.set_actions(argv)
            self.event.set()
            return True
        else:
            try:
                self.userdata.add_site(argv[0])
            except util.SSHProxyError, msg:
                channel.send("ERROR: %s does not exist in your scope\r\n" %
                                                                    argv[0])
                channel.close()
                self.event.set()
                return False
            sitedata = self.userdata.get_site(argv[0])
            if len(argv) > 1:
                sitedata.set_type('cmd')
                sitedata.set_cmdline(' '.join(argv[1:]))
            else:
                sitedata.set_type('shell')
            self.event.set()
            return True

    def check_channel_pty_request(self, channel, term, width, height,
                                  pixelwidth, pixelheight, modes):
        self.userdata.term = term
        self.userdata.width = width
        self.userdata.height = height
        return True




def service_client(client, addr, host_key_file):


    host_key = paramiko.DSSKey(filename=host_key_file)

    # start transport for the client
    transport = paramiko.Transport(client)
    transport.set_log_channel("paramiko")
    # debug !!
    #transport.set_hexdump(1)

    try:
        transport.load_server_moduli()
    except:
        raise

    transport.add_server_key(host_key)
    
    # start the server interface
    userdata = UserData()
    server = ProxyServer(userdata)
    negotiation_ev = threading.Event()
    transport.set_subsystem_handler('sftp', paramiko.SFTPServer,
                                            ProxySFTPServer)
    transport.start_server(negotiation_ev, server)

    while not negotiation_ev.isSet():
        negotiation_ev.wait(0.5)
        if not transport.is_active():
            raise 'ERROR: SSH negotiation failed'

    chan = transport.accept(20)
    if chan is None:
        log.error('ERROR: cannot open the channel. '
                  'Check the transport object. Exiting..')
        sys.exit(1)
    log.info('Authenticated %s', server.userdata.username)
    server.event.wait(15)
    if not server.event.isSet():
        log.error('ERROR: client never asked for a shell or a command.'
                    ' Exiting.')
        sys.exit(1)

    userdata.set_channel(chan)



    conn = None
    # is this a direct connection ?
    if len(userdata.list_sites()):
        if userdata.get_site().type == 'scp':
            proxy.ProxyScp(userdata).loop()
            chan.close()
            transport.close()
            return
        if userdata.get_site().type == 'cmd':
            proxy.ProxyCmd(userdata).loop()
            chan.close()
            transport.close()
            return
        conn = proxy.ProxyClient(userdata)
        log.info("Connecting to %s", userdata.get_site().sitename)
        try:
            ret = conn.loop()
        except:
            chan.send("\r\n ERROR: seems you found a bug"
                      "\r\n Please report it to sshproxy-dev@penguin.fr\r\n")
            chan.close()
            raise
        
        if ret == util.CLOSE:
            # if the direct connection closed, then exit cleanly
            conn = None
            chan.close()
            transport.close()
            log.info("Exiting %s", userdata.get_site().sitename)
            return
        # else go to the console
    
    if userdata.actions:
        for action in userdata.actions:
            if action in ('-l', '--list-sites'):
                sites = get_backend().list_allowed_sites()
                print sites
                for site in sites:
                    chan.send('%s@%s [%s]\r\n' % (
                                                site['uid'],
                                                site['name'],
                                                site['location'])) 
            else:
                chan.send("Unknown option %s\r\n" % action)

        chan.close()
        transport.close()
        return

    console = ConsoleBackend(conn, chan, userdata)
    console.loop()

    transport.close()

class ConsoleBackend(object):
    def __init__(self, conn, chan, userdata):
        conf = config.get_config('sshproxy')
        self.maxcon = conf['max_connections']

        self.userdata = userdata
        self.chan = chan

        self.msg = Message()

        self.main_console = PTYWrapper(chan, self.PtyConsole, self.msg,
                                    userdata.is_admin())
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
        try:
            sitename = self.userdata.add_site(sitename)
        except util.SSHProxyAuthError, msg:
            log.error("ERROR(open): %s", msg)
            return ("ERROR: site does not exist or you don't "
                            "have sufficient rights")

        conn = proxy.ProxyClient(self.userdata, sitename)

        cid = self.cpool.add_connection(conn)
        while True:
            if not conn:
                ret = 'ERROR: no connection id %s' % cid
                break
            try:
                ret = conn.loop()
            except:
                self.chan.send("\r\n ERROR: seems you found a bug"
                      "\r\n Please report it to sshproxy-dev@penguin.fr\r\n")
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
            return 'ERROR: no opened connection'
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
        return '%s' % (self.userdata.username)

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


servers = []
def kill_zombies(signum, frame):
    try:
        pid, status = os.wait()
        if pid in servers:
            del servers[servers.index(pid)]
    except OSError:
        pass
        


def _run_server():
    conf = config.get_config('sshproxy')
    ip = conf['bindip']
    port = conf['port']


    init_plugins()

    # get host key
    host_key_file = os.path.join(os.environ['HOME'], '.sshproxy/id_dsa')
    if not os.path.isfile(host_key_file):
        # XXX: paramiko knows how to do that now, IIRC
        # generate host key
        cmd =  "ssh-keygen -f %s -t dsa -C 'SSH proxy host key' -N '' -q"
        r = os.system(cmd % host_key_file)

    # set up the child killer handler
    signal.signal(signal.SIGCHLD, kill_zombies)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip, port))
        sock.listen(100)
        print "Server ready, clients may login now ..."
        log.debug('Listening for connection ...')
    except Exception, e:
        log.exception("ERROR: Couldn't bind on port %s" % port)
        print "ERROR: Couldn't bind on port %s" % port
        sys.exit(0)

    try:
        while True:
            try:
                client, addr = sock.accept()
            except KeyboardInterrupt:
                for pid in servers:
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except OSError:
                        log.exception('ERROR: child pid %s already dead', pid)
                raise
                sys.exit(1)
            except socket.error:
                continue
            except Exception, e:
                log.exception('ERROR: socket accept failed')
                raise
            log.debug('Got a connection!')
            pid = os.fork()
            if pid == 0:
                # just serve in the child
                log.info("Serving %s", addr)
                service_client(client, addr, host_key_file)
                os._exit(0)
            # (im)probable race condition here !
            servers.append(pid)
    finally:
        try:
            sock.close()
        except:
            pass
            



def run_server():
    log.info("sshproxy starting")
    try:
        try:
            _run_server()
        except KeyboardInterrupt:
            return
        except:
            log.exception("ERROR: sshproxy may have crashed:"
                                                    " AUTORESTARTING...")
    finally:
        log.info("sshproxy ending")

if __name__ == '__main__':
    run_server()