#!/usr/bin/python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 jan 20, 23:45:22 by david
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
import sys, os, traceback, select, socket, fcntl

import paramiko

import SSHproxy
import keys as key
import util
import log


class Logger(object):
    def __init__(self, passthru=None, logfile=sys.stderr):
        self.logfile = logfile
        self.passthru = passthru

    
    def closed(self):
        return self.passthru.closed
    closed = property(closed)

    def eof_received(self):
        return self.passthru.eof_received
    eof_received = property(eof_received)

    def set_passthru(self, passthru):
        self.passthru = passthru
        return self

    def send(self, msg):
        ret = self.logfile.write(msg)
        self.flush()
        if self.passthru:
            self.passthru.send(msg)
        return ret

    def recv(self, sz):
        return self.passthru.recv(sz)

    def write(self, msg):
        ret = self.logfile.write(msg)
        self.flush()
        if self.passthru:
            self.passthru.write(msg)
        return ret

    def read(self, sz=None):
        if sz:
            return self.passthru.read(sz)
        else:
            return self.passthru.read()

    def flush(self):
        return self.logfile.flush()

    def fileno(self):
        return self.passthru.fileno()

    def close(self):
        return self.logfile.close()
        
    def active(self):
        try:
            return self.passthru.active()
        except AttributeError:
            return 1
        
    def readline(self):
        return self.passthru.readline()

    def makefile(self, *args, **kwargs):
        return self.passthru.makefile(*args, **kwargs)

oldtty = None
def reset_term(term):
    global oldtty
    return # XXX: deactivated
    if oldtty:
        termios.tcsetattr(term, termios.TCSADRAIN, oldtty)
    mode = fcntl.fcntl(term, fcntl.F_GETFL)
    fcntl.fcntl(term, fcntl.F_SETFL, mode & ~os.O_NDELAY)
    oldtty = None

class ProxyScp(object):
    def __init__(self, userdata):
        self.client = userdata.channel
        self.sitedata = sitedata = userdata.get_site(0)
        try:
            self.transport = paramiko.Transport((sitedata.hostname, sitedata.port))
#            self.transport.set_hexdump(1)
            self.transport.connect(username=sitedata.username, password=sitedata.password, hostkey=sitedata.hostkey)
            self.chan = self.transport.open_session()
        except Exception, e:
            print '*** Caught exception: %s: %s' % (e.__class__, e)
            traceback.print_exc()
            try:
                self.transport.close()
            except:
                pass

    def loop(self):
        t = self.transport
        chan = self.chan
        client = self.client
        sitedata = self.sitedata
        chan.exec_command('scp -t -v %s' % sitedata.path)
        try:
            chan.settimeout(0.0)
            client.settimeout(0.0)
            fd = client
#            fd = logger.set_passthru(fd)
    
            while t.is_active() and client.active:
                r, w, e = select.select([chan, fd], [], [], 0.2)
                if chan in r:
                    x = chan.recv(1024)
                    if len(x) == 0 or chan.closed or chan.eof_received:
                        print 'EOF'
                        break
                    fd.send(x)
                if fd in r:
                    x = fd.recv(1024)
                    if len(x) == 0 or fd.closed or fd.eof_received:
                        print 'EOF'
                        break
                    chan.send(x)
    
        finally:
            pass

        return util.CLOSE


class ProxyClient(object):
    def __init__(self, userdata, sitename=None):
        self.client = userdata.channel
        self.sitedata = sitedata = userdata.get_site(sitename)
        self.name = '%s@%s' % (self.sitedata.username, self.sitedata.sid)

        log.info("Connect to %s@%s by %s\n" % (sitedata.username, sitedata.hostname, userdata.username))

        try:
            self.transport = paramiko.Transport((sitedata.hostname, sitedata.port))
            # XXX: debugging code follows
            #self.transport.set_hexdump(1)
            self.transport.connect(username=sitedata.username, password=sitedata.password, hostkey=sitedata.hostkey)
            self.chan = self.transport.open_session()
            self.chan.get_pty(userdata.term, userdata.width, userdata.height)
            self.chan.invoke_shell()
        except Exception, e:
            log.exception("Unable to set up SSH connection to server")
            try:
                self.transport.close()
            except:
                pass

    def loop(self):
        t = self.transport
        chan = self.chan
        client = self.client
        sitedata = self.sitedata
        try:
            chan.settimeout(0.0)
            client.settimeout(0.0)
            fd = client
#            fd = logger.set_passthru(fd)
    
            while t.is_active() and client.active:
                try:
                    r, w, e = select.select([chan, fd], [], [], 0.2)
                except select.error:
                    # this happens sometimes when returning from console
                    log.exception('select.select() failed')
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
                    if x == key.CTRL_X:
                        return util.SUSPEND
                    #SSHproxy.call_hooks('filter-console', fd, chan, sitedata, x)
                    # XXX: debuging code following
                    #if ord(x[0]) < 0x20:
                    #    fd.send('ctrl char: %s\r\n' % ' '.join([
                    #                    '%02x' % ord(c) for c in x ]))
                    if x in key.ALT_NUMBERS:
                        return key.get_alt_number(x)
                    if x == key.CTRL_K:
                        client.settimeout(None)
                        fd.send('\r\nEnter script name: ')
                        name = fd.makefile('rU').readline().strip()
                        client.settimeout(0.0)
                        SSHproxy.call_hooks('console', fd, chan, name, sitedata)
                        continue
                    chan.send(x)
    
        finally:
            log.debug("Exiting ProxyClient.loop()")

        return util.CLOSE
            
    
    def __del__(self):
        self.chan.close()


    
    


