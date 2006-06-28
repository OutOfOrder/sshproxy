#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jun 28, 02:37:40 by david
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

import hooks, keys, cipher, util, log



class Proxy(object):
    def __init__(self, userdata, sitename=None):
        self.client = userdata.channel
        self.sitedata = sitedata = userdata.get_site(sitename)
        self.userdata = userdata
        self.name = '%s@%s' % (self.sitedata.username, self.sitedata.sid)
        now = time.ctime()
        print ("\nConnecting to %s by %s on %s" %
                                    (self.name, userdata.username, now))
        log.info("Connecting to %s by %s on %s" %
                                    (self.name, userdata.username, now))
        try:
            self.transport = paramiko.Transport((sitedata.hostname,
                                                 sitedata.port))
            # XXX: debugging code follows
            #self.transport.set_hexdump(1)
            if sitedata.pkey:
                pkey = cipher.decipher(sitedata.pkey)
                password, pkey = None, util.get_dss_key_from_string(pkey)
            else:
                password, pkey = cipher.decipher(sitedata.password), None
            self.transport.connect(username=sitedata.username,
                                   password=password,
                                   hostkey=sitedata.hostkey,
                                   pkey=pkey)
            del password
            del pkey

            self.chan = self.transport.open_session()
            self.open_connection()

        except Exception, e:
            log.exception("Unable to set up SSH connection to server")
            try:
                self.transport.close()
            except:
                pass
        now = time.ctime()
        print ("Connected to %s by %s the %s" %
                                    (sitename, userdata.username, now))
        log.info("Connected to %s by %s the %s\n" %
                                    (sitename, userdata.username, now))



class ProxyScp(Proxy):
    def open_connection(self):
        log.info('Executing: scp %s %s' % (self.sitedata.args, 
                                           self.sitedata.path))
        self.chan.exec_command('scp %s %s' % (self.sitedata.args,
                                              self.sitedata.path))

    def loop(self):
        t = self.transport
        chan = self.chan
        client = self.client
        sitedata = self.sitedata
        try:
            chan.settimeout(0.0)
            client.settimeout(0.0)
            fd = client
    
            size = 4096
            while t.is_active() and client.active and not chan.eof_received:
                r, w, e = select.select([chan, fd], [chan, fd], [], 0.2)

                if chan in r:
                    if fd.out_window_size > 0:
                        x = chan.recv(size)
                        fd.send(x)
                    if len(x) == 0 or chan.closed or chan.eof_received:
                        log.info("Connection closed by server")
                        break
                if fd in r:
                    if chan.out_window_size > 0:
                        x = fd.recv(size)
                        chan.send(x)
                    if len(x) == 0 or fd.closed or fd.eof_received:
                        log.info("Connection closed by client")
                        break
        finally:
            pass
        return util.CLOSE


class ProxyCmd(Proxy):
    def open_connection(self):
        log.info('Executing: %s' % (self.sitedata.cmdline))
        self.chan.get_pty(self.userdata.term,
                          self.userdata.width,
                          self.userdata.height)
        self.chan.exec_command(self.sitedata.cmdline)

    def loop(self):
        t = self.transport
        chan = self.chan
        client = self.client
        sitedata = self.sitedata
        userdata = self.userdata
        try:
            chan.settimeout(0.0)
            client.settimeout(0.0)
            fd = client
    
            size = 40960
            while t.is_active() and client.active and not chan.eof_received:
                r, w, e = select.select([chan, fd], [chan, fd], [], 0.2)

                if chan in r:
                    if fd.out_window_size > 0:
                        x = chan.recv(size)
                        fd.send(x)
                    if len(x) == 0 or chan.closed or chan.eof_received:
                        log.info("Connection closed by server")
                        break
                if fd in r:
                    if chan.out_window_size > 0:
                        x = fd.recv(size)
                        chan.send(x)
                    if len(x) == 0 or fd.closed or fd.eof_received:
                        log.info("Connection closed by client")
                        break
        finally:
            pass
        return util.CLOSE



class ProxyClient(Proxy):
    def open_connection(self):
        self.chan.get_pty(self.userdata.term,
                          self.userdata.width,
                          self.userdata.height)
        self.chan.invoke_shell()


    def loop(self):
        t = self.transport
        chan = self.chan
        client = self.client
        sitedata = self.sitedata
        try:
            chan.settimeout(0.0)
            client.settimeout(0.0)
            fd = client
    
            while t.is_active() and client.active and not chan.eof_received:
                try:
                    r, w, e = select.select([chan, fd], [], [], 0.2)
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
                        fd.send(x)
                    except socket.timeout:
                        pass
                if fd in r:
                    x = fd.recv(1024)
                    if len(x) == 0 or fd.closed or fd.eof_received:
                        log.info("Connection closed by client")
                        break
                    if x == keys.CTRL_X:
                        return util.SUSPEND
                    hooks.call_hooks('filter-proxy', fd, chan,
                                                          sitedata, x)
                    # XXX: debuging code following
                    #if ord(x[0]) < 0x20 or ord(x[0]) > 126:
                    #    fd.send('ctrl char: %s\r\n' % ''.join([
                    #                    '\\x%02x' % ord(c) for c in x ]))
                    if x in keys.ALT_NUMBERS:
                        return keys.get_alt_number(x)
                    if x == keys.CTRL_K:
                        client.settimeout(None)
                        fd.send('\r\nEnter script name: ')
                        name = fd.makefile('rU').readline().strip()
                        client.settimeout(0.0)
                        hooks.call_hooks('console', fd, chan,
                                                       name, sitedata)
                        continue
                    chan.send(x)
    
        finally:
            now = time.ctime()
            print ("Disconnected from %s by %s the %s" %
                                    (self.name, self.sitedata.username, now))
            log.debug("Exiting ProxyClient.loop()")

        return util.CLOSE
            

    def __del__(self):
        if not hasattr(self, 'chan'):
            return
        try:
            self.chan.close()
        except ValueError:
            pass


    
    


