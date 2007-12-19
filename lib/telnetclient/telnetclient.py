#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Dec 19, 18:20:03 by david
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
from sshproxy.util import chanfmt

Server = get_class('Server')

class TelnetEnabledServer(Server):

    def do_shell_session(self):
        site = self.args[0]
        if not self.authorize(site, need_login=True):
            self.chan.send(chanfmt(_(u"ERROR: %s does not exist in "
                                        "your scope\n") % site))
            return False

        kind = self.get_ns_tag('site', 'kind', '')
        log.devdebug('KIND = %s' % kind)
        if not kind == 'telnet':
            return Server.do_shell_session(self)
        else:
            site = self.args.pop(0)

        if not self.check_acl('telnet_session'):
            self.chan.send(chanfmt("ERROR: You are not allowed to"
                                    " open a telnet session on %s"
                                    "\n" % site))
            return False
        self.update_ns('client', {
                            'type': 'telnet_session'
                            })
        log.info("Connecting to %s (telnet)", site)
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
            log.exception("An unknown exception occured")
            raise
        
        # if the direct connection closed, then exit cleanly
        conn = None
        log.info("Exiting %s", site)
        return True

    def connect_telnet(self):
        tl = telnetlib

        ip_address = self.get_ns_tag("site", "ip_address")
        port = self.get_ns_tag("site", "port")
        user = self.get_ns_tag("site", "login")

        tn = tl.Telnet()

        tn.set_option_negotiation_callback(self.parse_telnet_options)

        tn.open(ip_address, int(port))

        tn.sock.sendall(tl.IAC + tl.WILL + tl.NAWS)
        tn.sock.sendall(tl.IAC + tl.WILL + tl.TTYPE)
        
        timeout = 2
        time = 0
        total_timeout = 30
        while True:
            prompt = tn.expect(["(?i)SW:? ?",
                                "(?i)Login:? ?",
                                "(?i)Username:? ?"], timeout)

            if prompt[0] == -1 and prompt[2] == "":
                tn.write("\n")
                time += timeout
                if time >= total_timeout:
                    raise ValueError("ERROR: Couldn't connect. Timeout reached")
                timeout = 10
                continue

            if prompt[0] < 1:
                tn.write("\031")
                timeout = 10
                time += timeout
                continue

            break

        tn.write(user + "\n")

        password = self.monitor.call("get_site_password", clear=True)

        prompt = tn.expect(["(?i)Password:? ?"], 10)
        if prompt[0] == -1 and prompt[2] == "":
            raise ValueError("ERROR: Couldn't connect. Timeout reached")

        tn.write(password + "\n")

        return tn
    
    def parse_telnet_options(self, sock, command, option):
        tl = telnetlib
        if command == tl.DO and option == tl.NAWS:
            sock.sendall(tl.IAC + tl.SB +
                        tl.NAWS +
                        chr(self.width>>8) + chr(self.width&0xff) +
                        chr(self.height>>8) + chr(self.height&0xff) +
                    tl.IAC + tl.SE)
            return

        if command == tl.DO and option == tl.TTYPE:
            sock.sendall(tl.IAC + tl.SB +
                        tl.TTYPE +
                        tl.theNULL + self.term +
                    tl.IAC + tl.SE)
            return

        if command in (tl.DO, tl.DONT):
            sock.sendall(tl.IAC + tl.WONT + option)
        elif command in (tl.WILL, tl.WONT):
            sock.sendall(tl.IAC + tl.DONT + option)



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
        self.tn.close()
#        if not self.chan.closed and self.chan.transport.is_active():
#            self.chan.close()
        return 0
    

TelnetProxy.register()
