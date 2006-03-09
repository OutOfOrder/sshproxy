#!/usr/bin/python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Mar 09, 15:08:43 by david
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
import os.path, re, StringIO, time, select, socket
from SSHproxy.util import SSHProxyPluginError
from SSHproxy.ptywrap import PTYWrapper
import pexpect

class spawn(pexpect.spawn):
    """This class is a wrapper around pexpect.spawn to be able to talk
    to channels instead of normal file descriptors"""
    def set_channel(self, chan):
        self.child_fd = chan #.fileno()

    def set_console(self, console):
        self.console = console

    def isalive(self):
        try:
            return self.child_fd.get_transport().is_active()
        except AttributeError:
            return False

    def read_nonblocking(self, size=1, timeout=None):
        """
        This reads at most size characters from the child application.
        It includes a timeout. If the read does not complete within the
        timeout period then a TIMEOUT exception is raised.
        If the end of file is read then an EOF exception will be raised.
        If a log file was set using setlog() then all data will
        also be written to the log file.

        Notice that if this method is called with timeout=None 
        then it actually may block.

        This is a non-blocking wrapper around os.read().
        It uses select.select() to implement a timeout. 
        """
        
        if self.child_fd == -1:
            raise ValueError ('I/O operation on closed file')

        # Note that some systems like Solaris don't seem to ever give
        # an EOF when the child dies. In fact, you can still try to read
        # from the child_fd -- it will block forever or until TIMEOUT.
        # For this case, I test isalive() before doing any reading.
        # If isalive() is false, then I pretend that this is the same as EOF.
        if not self.isalive():
            r, w, e = select.select([self.child_fd], [], [], 0)
            if not r:
                self.flag_eof = 1
                raise pexpect.EOF ('End Of File (EOF) in read(). Braindead platform.')
        
        timeout=5.0
        r, w, e = select.select([self.child_fd], [], [], timeout)
        if not r:
            print ('Timeout (%s) exceeded in read().' % str(timeout))
            raise pexpect.TIMEOUT('Timeout (%s) exceeded in read().' % str(timeout))
        if self.child_fd in r:
            try:
                s = self.child_fd.recv(size)
#                s = os.read(self.child_fd, size)
            except OSError, e:
                self.flag_eof = 1
                raise pexpect.EOF('End Of File (EOF) in read(). Exception style platform.')
            if s == '':
                self.flag_eof = 1
                raise pexpect.EOF('End Of File (EOF) in read(). Empty string style platform.')
            
            if self.log_file != None:
                self.log_file.write (s)
                self.log_file.flush()
                
            if hasattr(self, 'console'):
                self.console.send(s)
            return s

        raise pexpect.ExceptionPexpect('Reached an unexpected state in read().')

    def send(self, str):
        print 'SENDING', str
        return self.child_fd.send(str)

class PluginSPexpectError(SSHProxyPluginError):
    def __init__(self, msg):
        self.msg = msg
        SSHProxyPluginError.__init__(self, msg)

    def __str__(self):
        return self.msg

class PluginSPexpect(object):
    def __init__(self, console, chan, scriptname, sitedata):
        self.console = console
        self.chan = chan
        self.xp = spawn(0)
        self.xp.set_channel(chan)
        self.xp.set_console(console)
        if not scriptname:
            scriptname = 'script'
        self.scriptname = scriptname
        self.sd = sitedata

#    def loop(self):
        chan = self.chan
        xp = self.xp
        console = self.console
    
        # send CTRL-U to delete the current line + enter to get the prompt
        #xp.send('\x15\n')
        # send ESC + '#' to comment the current line + enter to get the prompt
        #xp.send('\x1b#\n')
        # send CTRL-C to discard the current line + enter to get the prompt
        xp.send('\x03')
        script = open(os.path.join('scripts', self.scriptname), 'r')
    
        for line in script.readlines():
            if line.startswith('wait:'):
                print 'EXPECT:' + line[5:].strip()
                if xp.expect(line[5:].strip(), timeout=None) < 0:
                    raise SSHProxyPluginError("Timeout waiting for pattern: %s" % line)
                continue
            if line.find('$LOGIN$') >= 0:
                line = line.replace('$LOGIN$', self.sd.login)
            if line.find('$USER$') >= 0:
                line = line.replace('$USER$', self.sd.username)
            if line.find('$IPADDRESS$') >= 0:
                line = line.replace('$IPADDRESS$', self.sd.hostname)
            if line.find('$SITENAME$') >= 0:
                line = line.replace('$SITENAME$', self.sd.sitename)
            if line.find('$PASSWORD$') >= 0:
                line = line.replace('$PASSWORD$', self.sd.password)
            xp.send(line)
    
        script.close()


    def wait_for(self, pattern, timeout=5.0):
        chan = self.chan
        console = self.console
        
        pattern = re.compile(pattern)
        buf = StringIO.StringIO()
        start = time.clock()
        
        while time.clock() - start < timeout:
            r, w, e = select.select([chan], [], [], 0.2)
            if chan in r:
                try:
                    x = chan.recv(1024)
                    if len(x) == 0:
                        print '\r\n*** EOF\r\n',
                        break
                    console.send(x)
                    buf.write(x)
                    buf.flush()
                except socket.timeout:
                    pass
                    
            s = buf.getvalue()
            if pattern.search(s, 1):
                return s
        return None


