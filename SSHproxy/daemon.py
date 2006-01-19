#!/usr/bin/python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 jan 19, 00:43:15 by david
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

from util import PTYWrapper
from plugins import init_plugins, pluginInfo
from console import Console
from message import Message
from data import UserData, SiteData
from sftp import ProxySFTPServer
import proxy, util, pool

paramiko.util.log_to_file('sshproxy.log')



class ProxyServer(paramiko.ServerInterface):
    import base64
    data = "AAAAB3NzaC1yc2EAAAABIwAAAIEAt6qlQ6BjqFmgbbcgYWN+1rOeZCOY/RkIGhBn78Z+cQlQGt+ur+wYa9zot38SUl5z59WRMKofdMWNqF/fhmRmQdvqAgl4Ge8dh/tokho7eHwpFIhLNb3P3RXDP+mg/rb9Gc2Sofa3Fwxnv270aZGGzHhALhb6+jNFafr/D/Katds="
    good_pub_key = paramiko.RSAKey(data=base64.decodestring(data))
    
    def __init__(self, userdata):
        self.userdata = userdata
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        print "check_channel_request", kind, chanid
        if kind in [ 'session' ]:
            return paramiko.OPEN_SUCCEEDED
        print 'Ohoh! What is this "%s" channel type ?' % kind
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        if self.userdata.valid_auth(username=username, password=password):
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        sys.stdout.flush()
        if self.userdata.valid_auth(username=username, key=key.get_base64()):
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'password,publickey'

    def check_channel_shell_request(self, channel):
        print "check_channel_shell_request"
        self.event.set()
        return True

    def check_channel_subsystem_request(self, channel, name):
        print "check_channel_subsystem_request", channel, name
        return paramiko.ServerInterface.check_channel_subsystem_request(self,
                                            channel, name)

    def check_channel_exec_request(self, channel, command):
        print 'check_channel_exec_request', channel, command
        argv = command.split(' ', 1)
        if argv[0] == 'scp':
            while True:
                argv = argv[1].split(' ', 1)
                if argv[0][0] == '-':
                    continue
                break
            site, path = argv[0].split(':', 1)
            self.userdata.add_site(site)
            sitedata = self.userdata.get_site(site)
            sitedata.set_sftp_path(path)
            sitedata.set_type('scp')
            self.event.set()
            return True
        else:
            self.userdata.add_site(argv[0])
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
#    transport.set_log_channel("sshproxy.server")
    transport.set_hexdump(1)

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

    sys.stdout.flush()

    chan = transport.accept(20)
    if chan is None:
        print '*** No channel.'
        sys.exit(1)
        
    print 'Authenticated!'
    server.event.wait(10)
    if not server.event.isSet():
        print '*** Client never asked for a shell.'
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
        cid = cpool.add_connection(conn)
        ret = conn.loop()
        
        if ret == util.CLOSE:
            # if the direct connection closed, then exit cleanly
            cpool.del_connection(cid)
            chan.close()
            transport.close()
            print 'Exiting'
        # else go to the console

    msg = Message()
    def PtyConsole(*args, **kwargs):
        Console(*args, **kwargs).cmdloop()
    main_console = PTYWrapper(chan, PtyConsole, msg)
    data = ''
    confirm = msg.get_parent_fd()
    while 1:
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
                userdata.add_site(sitename)
            except util.SSHProxyError, msg:
                confirm.write('ERR %s' % msg)
                continue
            conn = proxy.ProxyClient(userdata, sitename)
            cid = cpool.add_connection(conn)
            while True:
                if not conn:
                    ret = 'Innexistant connection id: %d' % cid
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
            confirm.write(ret)

        elif action == 'switch' or action == 'back':
            try:
                cid 
            except UnboundLocalError:
                confirm.write('No previous connection open')
                continue
            if action == 'switch':
                cid = int(data.strip())
            while True:
                conn = cpool.get_connection(cid)
                if not conn:
                    ret = 'Innexistant connection id: %d' % cid
                    break
                ret = conn.loop()
                if ret == util.CLOSE:
                    cpool.del_connection(cid)
                elif ret >= 0:
                    cid = ret
                    continue
                ret = 'OK'
                break
            confirm.write(ret)

        elif action == 'list':
            l = []
            i = 0
            for c in cpool.list_connections():
                l.append('%d %s\n' % (i, c.name))
                i = i + 1
            if not len(l):
                confirm.write('No currently open connections')
            else:
                confirm.write(''.join(l))


    chan.close()
    transport.close()
    print 'Exiting'


servers = []
def kill_zombies(signum, frame):
    try:
        pid, status = os.wait()
        if pid in servers:
            del servers[servers.index(pid)]
    except OSError:
        pass

def run_server(ip='', port=2242):
    import signal

    init_plugins()
    # get host key
    host_key_file = os.path.join(os.environ['HOME'], '.sshproxy/id_dsa')
    if not os.path.isfile(host_key_file):
        # generate host key
        cmd =  "ssh-keygen -f %s -t dsa"
        cmd += " -C 'SSH proxy host key' -N '' -q"
        r = os.system(cmd % host_key_file)
        print r

    signal.signal(signal.SIGCHLD, kill_zombies)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip, port))
        sock.listen(100)
        print 'Listening for connection ...'
    except Exception, e:
        print '*** Bind failed: ' + str(e)
        traceback.print_exc()
        raise

    while True:
        try:
            client, addr = sock.accept()
        except KeyboardInterrupt:
            for pid in servers:
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    print 'child pid %s already dead' % pid
            raise
            sys.exit(1)
        except socket.error:
            continue
        except Exception, e:
            print '*** accept failed: ' + str(e)
            traceback.print_exc()
            raise
        
        print 'Got a connection!'
        pid = os.fork()
        if pid == 0:
            # just serve in the child
            service_client(client, addr, host_key_file)
            os._exit(0)
        # probable race condition here !
        # TODO: set an event with kill_zombies or service_client
        servers.append(pid)




if __name__ == '__main__':
    run_server()
