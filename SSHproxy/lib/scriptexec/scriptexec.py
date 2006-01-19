#!/usr/bin/python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 jan 19, 00:49:08 by david
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

class PluginScriptExecError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

class PluginScriptExec(object):
    def __init__(self, console, chan, scriptname, sitedata):
        self.console = console
        self.chan = chan
        if not scriptname:
            scriptname = 'script'
        self.scriptname = scriptname
        self.sd = sitedata

#    def send_script(self):
        chan = self.chan
        console = self.console
    
        script = open(os.path.join('scripts', self.scriptname), 'r')
    
        chan.send('\n')
        for line in script.readlines():
            if line.startswith('wait:'):
                if not self.wait_for(line[5:].strip()):
                    raise PluginScriptExecError("Timeout waiting for pattern: %s" % line)
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
            chan.send(line)
    
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


