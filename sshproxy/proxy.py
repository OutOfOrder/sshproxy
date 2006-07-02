#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 03, 00:00:17 by david
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


import sys, os, select, socket, fcntl, time
import threading

import paramiko
from paramiko.transport import SSHException, DEBUG
from paramiko import AuthenticationException

import hooks, keys, cipher, util, log



class Proxy(object):
    def __init__(self, proxy_client):
        self.client = proxy_client.chan
        self.remote = remote = proxy_client.remote
        self.proxy_client = proxy_client
        self.name = '%s@%s' % (self.remote.username, self.remote.sid)
        now = time.ctime()
        log.info("Connecting to %s by %s on %s" %
                                    (self.name, proxy_client.username, now))
        try:
            self.transport = paramiko.Transport((remote.hostname,
                                                 remote.port))
            # XXX: debugging code follows
            #self.transport.set_hexdump(1)

            self.connect()

            self.chan = self.transport.open_session()
            self.open_connection()

        except Exception, e:
            log.exception("Unable to set up SSH connection to server")
            try:
                self.transport.close()
            except:
                pass
            del self.transport
            return
        now = time.ctime()
        log.info("Connected to %s by %s on %s\n" %
                                    (self.name, proxy_client.username, now))


    def connect(self):
        remote = self.remote
        hostkey = remote.hostkey
        transport = self.transport

        transport.start_client()

        if hostkey is not None:
            transport._preferred_keys = [ hostkey.get_name() ]

            key = transport.get_remote_server_key()
            if (key.get_name() != hostkey.get_name() 
                                                or str(key) != str(hostkey)):
                log.error('Bad host key from server (%s).' % self.name)
                raise AuthenticationError('Bad host key from server (%s).'
                                                                % self.name)
            log.info('Server host key verified (%s) for %s' % (key.get_name(), 
                                                           self.name))

        pkey = cipher.decipher(remote.pkey)
        password = cipher.decipher(remote.password)
        if pkey:
            pkey = util.get_dss_key_from_string(pkey)
            try:
                transport.auth_publickey(remote.username, pkey)
                return True
            except AuthenticationException:
                log.warning('PKey for %s was not accepted' % self.name)

        if password:
            try:
                transport.auth_password(remote.username, password)
                return True
            except AuthenticationException:
                log.error('Password for %s is not valid' % self.name)
                raise

        raise AuthenticationException('No password for %s' % self.name)
                
            

class ProxyScp(Proxy):
    def open_connection(self):
        log.info('Executing: scp %s %s' % (self.remote.args, 
                                           self.remote.path))
        self.chan.exec_command('scp %s %s' % (self.remote.args,
                                              self.remote.path))

    def loop(self):
        if not hasattr(self, 'transport'):
            raise AuthenticationException('Could not authenticate %s'
                                                                % self.name)
        t = self.transport
        chan = self.chan
        client = self.client
        try:
            chan.settimeout(0.0)
            client.settimeout(0.0)
    
            size = 4096
            while t.is_active() and client.active and not chan.eof_received:
                r, w, e = select.select([chan, client], [chan, client], [], 0.2)

                if chan in r:
                    if client.out_window_size > 0:
                        x = chan.recv(size)
                        client.send(x)
                    if len(x) == 0 or chan.closed or chan.eof_received:
                        log.info("Connection closed by server")
                        break
                if client in r:
                    if chan.out_window_size > 0:
                        x = client.recv(size)
                        chan.send(x)
                    if len(x) == 0 or client.closed or client.eof_received:
                        log.info("Connection closed by client")
                        break
        finally:
            pass
        return util.CLOSE


class ProxyCmd(Proxy):
    def open_connection(self):
        log.info('Executing: %s' % (self.remote.cmdline))
        if hasattr(self.proxy_client, 'term'):
            self.chan.get_pty(self.proxy_client.term,
                              self.proxy_client.width,
                              self.proxy_client.height)
        self.chan.exec_command(self.remote.cmdline)

    def loop(self):
        if not hasattr(self, 'transport'):
            raise AuthenticationException('Could not authenticate %s'
                                                                % self.name)
        t = self.transport
        chan = self.chan
        client = self.client
        try:
            chan.settimeout(0.0)
            client.settimeout(0.0)
    
            size = 40960
            while t.is_active() and client.active and not chan.eof_received:
                r, w, e = select.select([chan, client], [chan, client], [], 0.2)

                if chan in r:
                    if client.out_window_size > 0:
                        x = chan.recv(size)
                        client.send(x)
                    if len(x) == 0 or chan.closed or chan.eof_received:
                        log.info("Connection closed by server")
                        break
                if client in r:
                    if chan.out_window_size > 0:
                        x = client.recv(size)
                        chan.send(x)
                    if len(x) == 0 or client.closed or client.eof_received:
                        log.info("Connection closed by client")
                        break
        finally:
            pass
        return util.CLOSE



class ProxyClient(Proxy):
    def open_connection(self):
        self.chan.get_pty(self.proxy_client.term,
                          self.proxy_client.width,
                          self.proxy_client.height)
        self.chan.invoke_shell()


    def loop(self):
        if not hasattr(self, 'transport'):
            raise AuthenticationException('Could not authenticate %s'
                                                                % self.name)
        t = self.transport
        chan = self.chan
        client = self.client
        try:
            chan.settimeout(0.0)
            client.settimeout(0.0)
    
            while t.is_active() and client.active and not chan.eof_received:
                try:
                    r, w, e = select.select([chan, client], [], [], 0.2)
                except select.error:
                    # this happens sometimes when returning from console
                    log.exception('ERROR: select.select() failed')
                    continue
                if chan in r:
                    try:
                        x = chan.recv(1024)
                        if len(x) == 0 or chan.closed or chan.eof_received:
                            log.info("Connection closed by server")
                            break
                        client.send(x)
                    except socket.timeout:
                        pass
                if client in r:
                    x = client.recv(1024)
                    if len(x) == 0 or client.closed or client.eof_received:
                        log.info("Connection closed by client")
                        break
                    if x == keys.CTRL_X:
                        return util.SUSPEND
                    hooks.call_hooks('filter-proxy', client, chan,
                                                          self.remote, x)
                    # XXX: debuging code following
                    #if ord(x[0]) < 0x20 or ord(x[0]) > 126:
                    #    client.send('ctrl char: %s\r\n' % ''.join([
                    #                    '\\x%02x' % ord(c) for c in x ]))
                    if x in keys.ALT_NUMBERS:
                        return keys.get_alt_number(x)
                    if x == keys.CTRL_K:
                        client.settimeout(None)
                        client.send('\r\nEnter script name: ')
                        name = client.makefile('rU').readline().strip()
                        client.settimeout(0.0)
                        hooks.call_hooks('console', client, chan,
                                                       name, self.remote)
                        continue
                    chan.send(x)
    
        finally:
            now = time.ctime()
            log.info("Disconnected from %s by %s the %s" %
                                    (self.name, self.remote.username, now))

        return util.CLOSE
            

    def __del__(self):
        if not hasattr(self, 'chan'):
            return
        try:
            self.chan.close()
        except ValueError:
            pass


    
    


