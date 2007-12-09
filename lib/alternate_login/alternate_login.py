#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Dec 09, 11:22:04 by david
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

class AlternateLoginServer(Server):
    alternate_login_sep = '?'
    alternate_login_at = '='

    def set_exec_args(self, argstr):
        args = self.args
        value = Server.set_exec_args(self, argstr)
        self.args = args + self.args
        return value

    def check_auth_password(self, username, password):
        if self.alternate_login_sep in username:
            username, site = username.split(self.alternate_login_sep, 1)
            site = site.replace(self.alternate_login_at, '@')
            if not len(self.args) or self.args[0] != site:
                self.args.insert(0, site)
        return Server.check_auth_password(self, username, password)

    def check_auth_publickey(self, username, key):
        if self.alternate_login_sep in username:
            username, site = username.split(self.alternate_login_sep, 1)
            site = site.replace(self.alternate_login_at, '@')
            if not len(self.args) or self.args[0] != site:
                self.args.insert(0, site)
        return Server.check_auth_publickey(self, username, key)

AlternateLoginServer.register()
