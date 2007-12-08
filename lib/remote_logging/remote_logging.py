#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Dec 08, 23:36:30 by david
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

from sshproxy import get_class

Server = get_class("Server")

class RemoteLoggingServer(Server):
    def connect_site(self, site_tags=None, site_ref=None):
        main_chan = Server.connect_site(self, site_tags, site_ref)

        rlog_chan = main_chan.transport.open_session()
        proxy_user = self.get_ns_tag('client', 'username')
        site_user = self.get_ns_tag('site', 'login')
        client_ip = self.get_ns_tag('client', 'ip_addr')
        cmdline = ('logger -p daemon.notice "User %s logged in as %s from %s"'
                            % (proxy_user, site_user, client_ip))
        rlog_chan.exec_command(cmdline)
        rlog_chan.close()

        return main_chan

RemoteLoggingServer.register()
