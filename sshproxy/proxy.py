#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Sep 20, 18:20:47 by david
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


import sys, os, select, socket, fcntl, time, signal
import threading

import paramiko
from paramiko.transport import SSHException, DEBUG
from paramiko import AuthenticationException

from registry import Registry
import cipher, util, log
from util import chanfmt
from acl import ACLDB, ACLTags



class Proxy(Registry):
    def __reginit__(self, proxy_client):
        self.client = proxy_client.chan
        self.client.settimeout(1.0)
        self.tags = {
                'client': proxy_client.pwdb.get_client_tags(),
                'site': proxy_client.pwdb.get_site_tags(),
                'proxy': proxy_client.pwdb.tags,
                }
        self.proxy_client = proxy_client
        self.msg = self.proxy_client.msg
        self.name = '%s@%s' % (self.tags['site'].login,
                               self.tags['site'].name)
        now = time.ctime()
        log.info("Connecting to %s by %s on %s" %
                    (self.name, proxy_client.pwdb.get_client().username, now))
        try:
            self.transport = paramiko.Transport((self.tags['site'].ip_address,
                                                 int(self.tags['site'].port)))
            # XXX: debugging code follows
            #self.transport.set_hexdump(1)

            self.connect()

            self.chan = self.transport.open_session()
            self.chan.settimeout(1.0)
            self.open_connection()

        except Exception, e:
            log.exception("Unable to set up SSH connection to server")
            try:
                self.transport.close()
                del self.transport
            except:
                pass
            return
        now = time.ctime()
        log.info("Connected to %s by %s on %s\n" %
                                    (self.name, proxy_client.username, now))

############################################################################

    def kill(self):
        self.transport.close()

    def handle_message(self):
        msg = self.msg.read()

        parts = msg.split(':', 1)
        if hasattr(self, 'msg_%s' % parts[0]):
            if len(parts) > 1:
                message = parts[1]
            else:
                message = ''
            return getattr(self, 'msg_%s' % parts[0])(message)

    def msg_alert(self, msg):
        self.msg_announce('\007%s' % msg)

    def msg_announce(self, msg):
        self.client.send(chanfmt(msg))

    def msg_kill(self, msg):
        if not msg:
            msg = ("\n\nOn administrative request, "
                   "your session is immediately closed.\n\n")
        self.msg_alert(msg)
        self.proxy_client.exit_status = 254
        self.kill()

############################################################################

    def connect(self):
        hostkey = self.tags['proxy'].get('hostkey', None) or None
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

        pkey = cipher.decipher(self.tags['site'].get('pkey', ''))
        password = cipher.decipher(self.tags['site'].get('password', ''))
        if pkey:
            pkey = util.get_dss_key_from_string(pkey)
            try:
                transport.auth_publickey(self.tags['site'].login, pkey)
                return True
            except AuthenticationException:
                log.warning('PKey for %s was not accepted' % self.name)

        if password:
            try:
                transport.auth_password(self.tags['site'].login, password)
                return True
            except AuthenticationException:
                log.error('Password for %s is not valid' % self.name)
                raise

        raise AuthenticationException('No valid authentication token for %s'
                                                                % self.name)
                
    def rx_tx(self, x, name, rx, tx, rfds, sz=4096):
        if len(x) == 0 or rx.closed:
            if rx.closed:
                log.info("Connection closed by %s" % name)
                return False
            elif rx.eof_received:
                # XXX: logging is commented out for half-close
                # because select always returns with rx.recv() == '' (EOF)
                # and this makes too much verbose logs
                #log.info("Connection half-closed by %s" % name)
                rx.shutdown_read()
                tx.shutdown_write()
                if name == 'client' and rx in rfds:
                    del rfds[rfds.index(rx)]
                elif name == 'server':
                    rx.shutdown_write()
            return True
        else:
            try:
                self.chan_send(tx, x)
            except ValueError:
                tx.shutdown_write()
                rx.shutdown_read()
                if name == 'client' and rx in rfds:
                    del rfds[rfds.index(rx)]
                elif name == 'server':
                    rx.shutdown_write()
            return True

    def server_to_client(self, rx, tx, rfds, sz=4096):
        x = rx.recv(sz)
        return self.rx_tx(x, 'server', rx, tx, rfds, sz=4096)

    def client_to_server(self, rx, tx, rfds, sz=4096):
        x = rx.recv(sz)
        return self.rx_tx(x, 'client', rx, tx, rfds, sz=4096)

    def chan_send(self, chan, s):
        SZ = sz = len(s)
        while sz:
            sent = chan.send(s)
            if sent:
                s = s[sent:]
                sz = sz - sent
            else:
                # this is a close on chan
                raise ValueError


    def __del__(self):
        if not hasattr(self, 'chan'):
            return
        try:
            self.chan.close()
        except ValueError:
            pass
            

class ProxyScp(Proxy):
    _class_id = 'ProxyScp'
    def open_connection(self):
        log.info('Executing: scp %s %s' % (self.tags['proxy'].scp_args, 
                                           self.tags['proxy'].scp_path))
        self.chan.exec_command('scp %s %s' % (self.tags['proxy'].scp_args, 
                                              self.tags['proxy'].scp_path))

    def loop(self):
        if not hasattr(self, 'transport'):
            raise AuthenticationException('Could not authenticate %s'
                                                                % self.name)
        t = self.transport
        chan = self.chan
        client = self.client
        try:
            size = 4096
            while t.is_active() and client.active and not chan.eof_received:
                r, w, e = select.select([self.msg, chan, client],
                                        [chan, client], [], 0.2)

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
                    if len(x) == 0:
                        self.chan.shutdown_write()
                        if client.closed:
                            log.info("Connection closed by client")
                            break
                        continue
                if self.msg in r:
                    self.handle_message()

        finally:
            self.chan.shutdown_write()
            exit_status = chan.recv_exit_status()
            self.proxy_client.exit_status = exit_status
            now = time.ctime()
            log.info("Disconnected from %s by %s on %s" %
                                    (self.name, self.tags['site'].login, now))

        self.chan.close()
        return util.CLOSE

ProxyScp.register()


class ProxyCmd(Proxy):
    _class_id = 'ProxyCmd'
    def open_connection(self):
        log.info('Executing: %s' % (self.tags['proxy'].cmdline))
        if hasattr(self.proxy_client, 'term'):
            self.chan.get_pty(self.proxy_client.term,
                              self.proxy_client.width,
                              self.proxy_client.height)
        self.chan.exec_command(self.tags['proxy'].cmdline)

    def loop(self):
        if not hasattr(self, 'transport'):
            raise AuthenticationException('Could not authenticate %s'
                                                                % self.name)
        t = self.transport
        chan = self.chan
        client = self.client
        try:
            listen_fd = [self.msg, chan, client]

            size = 40960
            while t.is_active():
                try:
                    r, w, e = select.select(listen_fd, [], [], 2)

                except KeyboardInterrupt:
                    log.warning('ERROR ProxyCmd: select.select() was interrupted')
                    continue
                except select.error:
                    # this happens when a signal was caught
                    log.warning('ERROR ProxyCmd: select.select() failed')
                    continue

                if chan in r:
                    if not self.server_to_client(chan, client,
                                                        listen_fd, size):
                        break

                if client in r:
                    if not self.client_to_server(client, chan,
                                                        listen_fd, size):
                        break

                if self.msg in r:
                    self.handle_message()
        finally:
            self.chan.shutdown_write()
            exit_status = chan.recv_exit_status()
            self.proxy_client.exit_status = exit_status
            now = time.ctime()
            log.info("Disconnected from %s by %s on %s" %
                                    (self.name, self.tags['site'].login, now))

        #self.chan.close()
        return util.CLOSE

ProxyCmd.register()


class ProxyShell(Proxy):
    _class_id = 'ProxyShell'
    def open_connection(self):
        if hasattr(self.proxy_client, 'term'):
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
            listen_fd = [self.msg, chan, client]
            while t.is_active():
                try:
                    r, w, e = select.select(listen_fd, [], [], 2)
                except KeyboardInterrupt:
                    log.warning('ERROR: select.select() was interrupted')
                    continue
                except select.error:
                    # this happens when a signal was caught
                    log.warning('ERROR: select.select() failed')
                    continue

                if chan in r:
                    if not self.server_to_client(chan, client,
                                                            listen_fd):
                        break

                if client in r:
                    if not self.client_to_server(client, chan,
                                                            listen_fd):
                        break

                if self.msg in r:
                    self.handle_message()
    
        finally:
            self.chan.shutdown_write()
            exit_status = chan.recv_exit_status()
            self.proxy_client.exit_status = exit_status
            now = time.ctime()
            log.info("Disconnected from %s by %s on %s" %
                                    (self.name, self.tags['site'].login, now))

        return util.CLOSE
            

ProxyShell.register()
    
    


