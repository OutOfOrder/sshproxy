#!/usr/bin/python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jan 21, 17:27:36 by david
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307  USA


# Imports from Python
import sys, os.path, socket, threading, traceback

import paramiko

from ptywrap import PTYWrapper
from plugins import init_plugins, pluginInfo
from console import Console
from message import Message
from data import UserData, SiteData
from sftp import ProxySFTPServer
import proxy, util, pool
import config

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
        if argv[0] == 'scp':
            while True:
                argv = argv[1].split(' ', 1)
                if argv[0][0] == '-':
                    continue
                break
            site, path = argv[0].split(':', 1)
            try:
                self.userdata.add_site(site)
            except util.SSHProxyError, msg:
                self.event.set()
                return False
            sitedata = self.userdata.get_site(site)
            sitedata.set_sftp_path(path)
            sitedata.set_type('scp')
            self.event.set()
            return True
        else:
            try:
                self.userdata.add_site(argv[0])
            except util.SSHProxyError, msg:
                self.event.set()
                return False
            sitedata = self.userdata.get_site(argv[0])
            if len(argv) > 1:
                sitedata.set_cmdline(argv[1])
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
    # mega-hyper-duper debug
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
    transport.set_subsystem_handler('sftp', paramiko.SFTPServer, ProxySFTPServer)
    transport.start_server(negotiation_ev, server)

    while not negotiation_ev.isSet():
        negotiation_ev.wait(0.1)
        if not transport.is_active():
            raise 'SSH negotiation failed'

    chan = transport.accept(20)
    if chan is None:
        log.error('*** No channel. Exiting.')
        sys.exit(1)
        
    log.info('Authenticated %s', server.userdata.username)
    server.event.wait(10)
    if not server.event.isSet():
        log.error('*** Client never asked for a shell. Exiting.')
        sys.exit(1)

    userdata.set_channel(chan)

            

    cpool = pool.get_connection_pool()
    # is this a direct connection ?
    if len(userdata.list_sites()):
        try:
            if userdata.get_site().type == 'scp':
                proxy.ProxyScp(userdata).loop()
                chan.close()
                transport.close()
                return
        except AttributeError:
            pass
        conn = proxy.ProxyClient(userdata)
        log.info("Connecting to %s", userdata.get_site().sitename)
        cid = cpool.add_connection(conn)
        ret = conn.loop()
        
        if ret == util.CLOSE:
            # if the direct connection closed, then exit cleanly
            cpool.del_connection(cid)
            chan.close()
            transport.close()
            log.info("Exiting %s", userdata.get_site().sitename)
            return
        # else go to the console

    msg = Message()
    def PtyConsole(*args, **kwargs):
        Console(*args, **kwargs).cmdloop()
    main_console = PTYWrapper(chan, PtyConsole, msg, userdata.is_admin())

    status = msg.get_parent_fd()
    while True:
        data = main_console.loop()
        if data is None:
            break
        try:
            action, data = data.split(' ')
        except ValueError:
            action = data.strip()
            data = ''

        if action == 'connect':
            sitename = data.strip()
            try:
                sitename = userdata.add_site(sitename)
            except util.SSHProxyError, msg:
                status.write('ERR %s' % msg)
                continue
            conn = proxy.ProxyClient(userdata, sitename)
            cid = cpool.add_connection(conn)
            while True:
                if not conn:
                    ret = 'Inexistant connection id: %d' % cid
                    break
                ret = conn.loop()
                if ret == util.CLOSE:
                    cpool.del_connection(cid)
                elif ret >= 0:
                    cid = ret
                    conn = cpool.get_connection(cid)
                    continue
                ret = 'OK'
                break
            status.write(ret)

        elif action == 'switch' or action == 'back':
            try:
                cid 
            except UnboundLocalError:
                status.write('No previous connection open')
                continue
            if action == 'switch':
                cid = int(data.strip())
            while True:
                conn = cpool.get_connection(cid)
                if not conn:
                    ret = 'Inexistant connection id: %d' % cid
                    break
                ret = conn.loop()
                if ret == util.CLOSE:
                    cpool.del_connection(cid)
                elif ret >= 0:
                    cid = ret
                    continue
                ret = 'OK'
                break
            status.write(ret)

        elif action == 'list':
            l = []
            i = 0
            for c in cpool.list_connections():
                l.append('%d %s\n' % (i, c.name))
                i = i + 1
            if not len(l):
                status.write('No currently open connections')
            else:
                status.write(''.join(l))


    chan.close()
    transport.close()
    log.info('Client exiting')


servers = []
def kill_zombies(signum, frame):
    try:
        pid, status = os.wait()
        if pid in servers:
            del servers[servers.index(pid)]
    except OSError:
        pass

def _run_server():
    import signal

    conf = config.SSHproxyConfig()
    ip = conf.bindip
    port = conf.port
    init_plugins()
    # get host key
    host_key_file = os.path.join(os.environ['HOME'], '.sshproxy/id_dsa')
    if not os.path.isfile(host_key_file):
        # XXX: paramiko knows how to do that now, IIRC
        # generate host key
        cmd =  "ssh-keygen -f %s -t dsa"
        cmd += " -C 'SSH proxy host key' -N '' -q"
        r = os.system(cmd % host_key_file)

    signal.signal(signal.SIGCHLD, kill_zombies)


    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip, port))
        sock.listen(100)
        log.debug('Listening for connection ...')
    except Exception, e:
        log.exception('*** Bind failed')
        raise

    try:
        while True:
            try:
                client, addr = sock.accept()
            except KeyboardInterrupt:
                for pid in servers:
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except OSError:
                        log.exception('child pid %s already dead', pid)
                raise
                sys.exit(1)
            except socket.error:
                continue
            except Exception, e:
                log.exception('*** accept failed')
                raise
            
            log.debug('Got a connection!')
            pid = os.fork()
            if pid == 0:
                # just serve in the child
                log.info("Serving %s", addr)
                service_client(client, addr, host_key_file)
                os._exit(0)
            # (im)probable race condition here !
            # TODO: set an event with service_client
            servers.append(pid)
    finally:
        try:
            sock.close()
        except:
            pass


def run_server():
    log.info("SSHproxy starting")
    try:
#        while True:
            try:
                _run_server()
            except KeyboardInterrupt:
                return
            except:
                log.exception("SSHproxy restarting...")
    finally:
        log.info("SSHproxy ending")


if __name__ == '__main__':
    run_server()
