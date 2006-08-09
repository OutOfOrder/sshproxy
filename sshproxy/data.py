#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Aug 09, 18:11:07 by david
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


from util import SSHProxyError, SSHProxyAuthError, istrue
from config import get_config
from backend import get_backend

# XXX: this class should be a singleton
class UserData(object):
    def __init__(self):
        self.pwdb = get_backend()
        self.sitelist = []
        self.sitedict = {}
        self.actions = None
        self.exit_status = 0

    def set_actions(self, actions):
        self.actions = actions

    def valid_auth(self, username, password=None, key=None):
        if not self.pwdb.is_allowed(username=username,
                                    password=password,
                                    key=key):
            if key is not None:
                self.unauth_key = key
            return False
        else:
            if key is None and hasattr(self, 'unauth_key'):
                if istrue(get_config('sshproxy')['auto_add_key']):
                    self.pwdb.set_login_key(self.unauth_key)
            self.username = username
            return True

    def is_admin(self):
        return self.is_authenticated() and self.pwdb.is_admin()
            
    def is_authenticated(self):
        return hasattr(self, 'username')
        
    def set_channel(self, channel):
        self.channel = channel

    def add_site(self, sitename):
        sitedata = SiteData(self, sitename)
        self.sitedict[sitedata.sitename] = sitedata
        self.sitedict[sitename] = sitedata
        self.sitelist.append(sitedata.sitename)
        # return real sitename (user@sid)
        return sitedata.sitename

    def get_site(self, sitename=None, index=0):
        if not sitename:
            if len(self.sitelist):
                return self.sitedict[self.sitelist[index]]
            else:
                return None
        elif sitename in self.sitedict.keys():
            return self.sitedict[sitename]
        else:
            return None

    def list_sites(self):
        return self.sitelist

class SiteData(object):
    def __init__(self, userdata, sitename):
        self.userdata = userdata

        rlogin, site = userdata.pwdb.get_rlogin_site(sitename)

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

        self.type = 'shell'
        self.cmdline = None
        self.path = None
        self.args = None
    
    def set_type(self, type):
        # 'shell' or 'scp' or 'cmd'
        self.type = type
        
    def set_cmdline(self, cmdline):
        self.cmdline = cmdline

    def set_sftp_path(self, path):
        self.path = path or '.'

    def set_sftp_args(self, args):
        self.args = args

