#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 03, 00:25:26 by david
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


from util import SSHProxyAuthError

class SiteData(object):
    def __init__(self, client, sitename):
        self.client = client

        rlogin, site = client.pwdb.get_rlogin_site(sitename)

        if not site:
            raise SSHProxyAuthError("ERROR: %s does not exist in the database"
                                                                % sitename)
        self.sid = site.sid
        self.username = rlogin
        self.sitename = '%s@%s' % (rlogin, site.sid)

        self.hostname = site.ip_address
        self.port = site.port
        # TODO: check the hostkey (add a column in mysql.sshproxy.site)
        self.hostkey = None

        self.sitedata = site
        self.password = site.rlogins[rlogin].password
        self.pkey = site.rlogins[rlogin].pkey

        self.cmdline = None
        self.path = None
        self.args = None
    
    def set_cmdline(self, cmdline):
        self.cmdline = cmdline

    def set_sftp_path(self, path):
        self.path = path or '.'

    def set_sftp_args(self, args):
        self.args = args

