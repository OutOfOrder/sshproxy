#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 20, 23:17:57 by david
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
import hooks, keys, cipher, util, log
from util import chanfmt
from acl import ACLDB, ACLTags



class Proxy(Registry):
    def __reginit__(self, proxy_client):
        self.client = proxy_client.chan
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
            chan.settimeout(0.0)
            client.settimeout(0.0)
    
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
                    if len(x) == 0 or client.closed or client.eof_received:
                        log.info("Connection closed by client")
                        break
                if self.msg in r:
                    self.handle_message()
        finally:
            pass
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
            chan.settimeout(0.0)
            client.settimeout(0.0)
    
            size = 40960
            while t.is_active() and client.active and not chan.eof_received:
                try:
                    r, w, e = select.select([self.msg, chan, client],
                                        [chan, client], [], 2)

                except KeyboardInterrupt:
                    log.warning('ERROR ProxyCmd: select.select() was interrupted')
                    continue
                except select.error:
                    # this happens when a signal was caught
                    log.warning('ERROR ProxyCmd: select.select() failed')
                    continue
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
                if self.msg in r:
                    self.handle_message()
        finally:
            pass
        return util.CLOSE

ProxyCmd.register()


class ProxyShell(Proxy):
    _class_id = 'ProxyShell'
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
                    r, w, e = select.select([self.msg, chan, client], [], [], 2)
                except KeyboardInterrupt:
                    log.warning('ERROR: select.select() was interrupted')
                    continue
                except select.error:
                    # this happens when a signal was caught
                    log.warning('ERROR: select.select() failed')
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
                        if not ACLDB().check('console_session',
                                                    **self.tags):
                            client.send(chanfmt("ERROR: You are not allowed to"
                                                " open a console session.\n"))
                            continue
                        else:
                            return util.SUSPEND
                    hooks.call_hooks('filter-proxy', client, chan,
                                                          self.tags, x)
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
                                                       name, self.tags)
                        continue
                    chan.send(x)
                if self.msg in r:
                    self.handle_message()
    
        finally:
            now = time.ctime()
            log.info("Disconnected from %s by %s the %s" %
                                    (self.name, self.tags['site'].login, now))

        return util.CLOSE
            

    def __del__(self):
        if not hasattr(self, 'chan'):
            return
        try:
            self.chan.close()
        except ValueError:
            pass

ProxyShell.register()
    
    


