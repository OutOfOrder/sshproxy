#!/usr/bin/python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 jan 12, 16:17:13 by david
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
#from paramiko.util import unhexify

def unhexify(s):
    "turn a hex sequence back into a string"
    return ''.join([chr(int(s[i:i+2], 16)) for i in range(0, len(s), 2)])



from SSHproxy import pwdb, proxy
from SSHproxy.util import FreeStructure, PTYWrapper
from SSHproxy.plugins import init_plugins, pluginInfo
from SSHproxy import console
from SSHproxy.console import Console
from SSHproxy.proxy import set_term, reset_term

paramiko.util.log_to_file('sshproxy.log')


class ProxySFTPServer(paramiko.SFTPServerInterface):
    pass

class ProxyServer(paramiko.ServerInterface):
    import base64
    data = "AAAAB3NzaC1yc2EAAAABIwAAAIEAt6qlQ6BjqFmgbbcgYWN+1rOeZCOY/RkIGhBn78Z+cQlQGt+ur+wYa9zot38SUl5z59WRMKofdMWNqF/fhmRmQdvqAgl4Ge8dh/tokho7eHwpFIhLNb3P3RXDP+mg/rb9Gc2Sofa3Fwxnv270aZGGzHhALhb6+jNFafr/D/Katds="
    good_pub_key = paramiko.RSAKey(data=base64.decodestring(data))
    
    def __init__(self, pwdb):
        self.pwdb = pwdb
        self.event = threading.Event()
        sitedata = FreeStructure()
        self.sitedata = sitedata
        self.sitedata.sitename = None

    def check_channel_request(self, kind, chanid):
        if kind in [ 'session' ]:
            return paramiko.OPEN_SUCCEEDED
        print 'Ohoh! What is this "%s" channel type ?' % kind
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        if self.pwdb.is_allowed(username=username, password=password):
            self.sitedata.login = username
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        sys.stdout.flush()
        if self.pwdb.is_allowed(username=username, key=key.get_base64()):
            self.sitedata.login = username
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'password,publickey'

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_subsystem_request(self, channel, name):
        return paramiko.ServerInterface.check_channel_subsystem_request(self,
                                            channel, name)

    def check_channel_exec_request(self, channel, command):
        name_cmd = command.split(' ', 1)
        self.sitedata.sitename = name_cmd[0]
        if len(name_cmd) > 1:
            self.sitedata.cmdline = name_cmd[1]
        else:
            self.sitedata.cmdline = ''
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height,
                                  pixelwidth, pixelheight, modes):
        self.sitedata.term = term
        self.sitedata.width = width
        self.sitedata.height = height
        return True


def service_client(client, addr, host_key_file):
    
    host_key = paramiko.DSSKey(filename=host_key_file)

    # start transport for the client
    transport = paramiko.Transport(client)
    transport.set_log_channel("sshproxy.server")
#    transport.set_hexdump(1)

    try:
        transport.load_server_moduli()
    except:
        raise

    transport.add_server_key(host_key)
    
    # start the server interface
    from SSHproxy import pwdb
    server = ProxyServer(pwdb)
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


    sitedata = server.sitedata
    sitedata.hostkey  = None
    sitedata.chan = chan
    if sitedata.sitename:
        user, site = pwdb.get_site(sitedata.sitename)

        sitedata.hostname = site.ip_address
        sitedata.port = site.port
        sitedata.username = user
        sitedata.password = site.users[user].password

        proxy.ProxyClient(chan, sitedata).proxyloop()

    else:
        from SSHproxy.console import Console as Console
        from SSHproxy.message import Message
        def PtyConsole(*args, **kwargs):
            Console(*args, **kwargs).cmdloop()
        msg = Message()
        ptywrapped = PTYWrapper(chan, PtyConsole, msg, sitedata=sitedata)
        data = ''
        confirm = msg.get_parent_fd()
        while 1:
            data = ptywrapped.loop()
            if data is None:
                break
            action, data = data.split(' ')
            if action == 'connect':
                sitedata.sitename = data.strip()
                if sitedata.sitename:
                    print sitedata.sitename
                    user, site = pwdb.get_site(sitedata.sitename)

                    sitedata.hostname = site.ip_address
                    sitedata.port = site.port
                    sitedata.username = user
                    print site.users.keys()
                    sitedata.password = site.users[user].password

                    proxy.ProxyClient(chan, sitedata).proxyloop()
                    confirm.write('ok')

    chan.close()
    transport.close()
    print 'Exiting'


servers = []
def kill_zombies(signum, frame):
    pid, status = os.wait()
    if pid in servers:
        del servers[servers.index(pid)]

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
