#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Dec 19, 23:21:49 by david
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

import threading, socket, os.path
import paramiko
from sshproxy import get_class, log
from sshproxy.config import ConfigSection, path, get_config


class SIPCConfigSection(ConfigSection):
    section_id = 'sipc'
    section_defaults = {
        'authorized_keys': '@authorized_keys',
        'key_file': '@ipc.id_dsa',
        }
    types = {
        'authorized_keys': path,
        'key_file': path,
        }

SIPCConfigSection.register()

class SSHServer(paramiko.ServerInterface):
    def __init__(self, addr):
        self.sock_addr = addr
        paramiko.ServerInterface.__init__(self)

    def check_auth_publickey(self, username, key):
        pubkey = key.get_base64()
        addr = self.sock_addr[0]

        if username == "sshproxy-IPC":
            try:
                hostkey_file = get_config('sshproxy').get('hostkey_file')
                hostkey = paramiko.DSSKey(filename=hostkey_file).get_base64()

                auth_keys_file = get_config('sipc')['authorized_keys']
                if os.path.isfile(auth_keys_file):
                    authorized_keys = open(auth_keys_file).readlines()
                else:
                    authorized_keys = []

                authorized_keys.append(hostkey)
                if not len([ k for k in authorized_keys if pubkey in k ]):
                    log.error("ATTENTION: unauthorized attempt to connect "
                              "on IPC channel from %s@%s" % (username, addr))
                    return paramiko.AUTH_FAILED

            except:
                log.exception("SIPC: exception in check_auth_pubkey")
                return paramiko.AUTH_FAILED

            self.username = username
            return paramiko.AUTH_SUCCESSFUL

        log.error("ATTENTION: unauthorized attempt to connect "
                  "on IPC channel from %s@%s" % (username, addr))
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        if kind == 'sshproxy-IPC':
            return paramiko.OPEN_SUCCEEDED

        addr = self.sock_addr[0]
        log.error("ATTENTION: unauthorized attempt to connect "
                  "on IPC channel type '%s' from %s@%s" %
                    (kind, self.username, addr))

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

        transport.start_server(negotiation_ev, SSHServer(self.sock_addr))

        while not negotiation_ev.isSet():
            negotiation_ev.wait(0.5)
        if not transport.is_active():
            log.error("SIPC: SSH negotiation failed")
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
            log.error("SIPC: SSH negotiation failed")
            raise 'SSH negotiation failed'

        ev = threading.Event()

        key_file = get_config("sipc").get("key_file")
        if not os.path.isfile(key_file):
            key_file = get_config("sshproxy").get("hostkey_file")

        key = paramiko.DSSKey(filename=key_file)

        transport.auth_publickey('sshproxy-IPC', key, ev)

        while not ev.isSet():
            ev.wait(0.5)
        if not transport.is_authenticated():
            log.error("SIPC: SSH authentication failed")
            raise 'SSH authentication failed'

        sock = transport.open_channel('sshproxy-IPC')
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
