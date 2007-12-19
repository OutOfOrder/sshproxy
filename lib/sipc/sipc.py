#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Dec 19, 00:47:44 by david
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

import threading, socket
import paramiko
from sshproxy import get_class, log

class SSHServer(paramiko.ServerInterface):
    def check_auth_publickey(self, username, key):
        log.devdebug("SSHServer[IPC]: check_auth_publickey %s %s", username, key)
        pubkey=key.get_base64()
        if username == "IPC":
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        log.devdebug("SSHServer[IPC]: check_channel_request %s %s", kind, chanid)
        if kind == 'IPC':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED



IPCServer = get_class("IPCServer")

class SIPCServer(IPCServer):
    def _sock_accept(self):
        if self.sock_type == socket.AF_UNIX and self.sock_addr[0] == '\x00':
            return IPCServer._sock_accept(self)

        real_sock, address = self.sock.accept()
        log.info("IPC: Accepting new secure client %s", address)

        host_key = paramiko.DSSKey(filename="/etc/sshproxy/id_dsa")

        transport = paramiko.Transport(real_sock)

        transport.load_server_moduli()
        transport.add_server_key(host_key)

        # start the server interface
        negotiation_ev = threading.Event()

        transport.start_server(negotiation_ev, SSHServer())

        while not negotiation_ev.isSet():
            negotiation_ev.wait(0.5)
        if not transport.is_active():
            raise 'SSH negotiation failed'

        sock = transport.accept(5)

        self.real_sock = real_sock
        self.transport = transport

        return sock, address

    def close(self):
        if not (self.sock_type == socket.AF_UNIX
                and self.sock_addr[0] == '\x00'):
            self.transport.close()
            self.real_sock.close()
        IPCServer.close(self)

SIPCServer.register()


IPCClient = get_class("IPCClient")

class SIPCClient(IPCClient):
    def _sock_connect(self, real_sock, sock_addr):
        if self.sock_type == socket.AF_UNIX and self.sock_addr[0] == '\x00':
            return IPCClient._sock_connect(self, real_sock, sock_addr)

        real_sock.connect(sock_addr)
        log.info("IPC: Connecting to secure server %s", sock_addr)

        transport = paramiko.Transport(real_sock)

        ev = threading.Event()

        transport.start_client(ev)

        while not ev.isSet():
            ev.wait(0.5)
        if not transport.is_active():
            raise 'SSH negotiation failed'

        ev = threading.Event()

        key = paramiko.DSSKey(filename="/etc/sshproxy/id_dsa")

        transport.auth_publickey('IPC', key, ev)

        while not ev.isSet():
            ev.wait(0.5)
        if not transport.is_authenticated():
            raise 'SSH authentication failed'

        sock = transport.open_channel('IPC') #, dest_addr=sock_addr, src_addr=None)
        self.real_sock = real_sock
        self.transport = transport

        return sock

    def close(self):
        if not (self.sock_type == socket.AF_UNIX
                and self.sock_addr[0] == '\x00'):
            self.transport.close()
            self.real_sock.close()
        IPCClient.close(self)

SIPCClient.register()
