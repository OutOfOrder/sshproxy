#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Mar 23, 11:43:13 by david
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

import telnetlib
import select

from sshproxy import get_class
from sshproxy.registry import Registry
from sshproxy.server import Server
from sshproxy import log

Server = get_class('Server')

class TelnetEnabledServer(Server):

    def do_shell_session(self):
        site = self.args[0]
        if not self.authorize(site, need_login=True):
            self.chan.send(chanfmt("ERROR: %s does not exist in "
                                        "your scope\n" % site))
            return False

        kind = self.get_ns_tag('site', 'kind', '')
        log.devdebug('KIND = %s' % kind)
        if not kind == 'telnet':
            return Server.do_shell_session(self)
        else:
            site = self.args.pop(0)

        if not self.check_acl('shell_session'):
            self.chan.send(chanfmt("ERROR: You are not allowed to"
                                    " open a shell session on %s"
                                    "\n" % site))
            return False
        self.update_ns('client', {
                            'type': 'shell_session'
                            })
        log.info("Connecting to %s", site)
        conn = TelnetProxy(self.chan, self.connect_telnet(), self.monitor)
        try:
            self.exit_status = conn.loop()
        except KeyboardInterrupt:
            return True
        except Exception, e:
            self.chan.send("\r\n ERROR: It seems you found a bug."
                           "\r\n Please report this error "
                           "to your administrator.\r\n"
                           "Exception class: <%s>\r\n\r\n"
                                    % e.__class__.__name__)
            
            raise
        
        # if the direct connection closed, then exit cleanly
        conn = None
        log.info("Exiting %s", site)
        return True

    def connect_telnet(self):
        HOST = "localhost"
        #user = raw_input("Enter your remote account: ")
        #password = getpass.getpass()
        
        user="weblord"
        password="weblord"
        
        tn = telnetlib.Telnet(HOST)
        
        tn.read_until("login: ")
        tn.write(user + "\n")
        if password:
            tn.read_until("Password: ")
            tn.write(password + "\n")

        return tn
        

TelnetEnabledServer.register()


class TelnetProxy(Registry):
    _class_id = 'TelnetProxy'

    def __reginit__(self, chan, tn, monitor):
        self.chan = chan
        self.tn = tn
        self.monitor = monitor

    def loop(self):
        while True:
            r, w, e = select.select([self.chan, self.tn], [], [], 0.1)
            if len(r):
                if self.chan in r:
                    data = self.chan.recv(1)
                    if data == '':
                        break
                    self.tn.write(data)
                if self.tn in r:
                    try:
                        data = self.tn.read_very_eager()
                    except EOFError:
                        break
                    self.chan.send(data)
                    #self.chan.flush()
    

TelnetProxy.register()
