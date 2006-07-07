#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 06, 23:04:13 by david
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

from registry import Registry
from acl import ACLTags


class UserInfo(Registry):
    _class_id = 'UserInfo'
    def __init__(self, **kw):
        self.tags = ACLTags(obj=self)

UserInfo.register()

class SiteInfo(Registry):
    _class_id = 'SiteInfo'
    def __init__(self, **kw):
        self.tags = ACLTags(obj=self)

SiteInfo.register()


class SiteDB(Registry):
    _class_id = 'SiteDB'
    _singleton = True

    def __init__(self, **kw):
        self.tags = ACLTags(obj=self)

    def get_rlogin(self, uid=None):
        pass

    def get_rlogin_site(self, site_id):
        pass

    def list_sites(self, **kw):
        return SiteInfo.get_instance()

    def list_allowed_sites(self, login=None, **kw):
        pass

    def is_admin(self, login=None):
        pass

    def can_connect(self, rlogin, site):
        pass

    def get_console(self):
        return None

    def get_wizard(self):
        return None


SiteDB.register()


if __name__ == '__main__':
    class MySiteInfo(SiteInfo):
        pass
    MySiteInfo.register()

    class MyPwDb(SiteDB):
        def list_sites(self):
            s = SiteInfo.get_instance()
            s.toto = 'titi'
            return s
    MyPwDb.register()

    

    pwdb = SiteDB.get_instance()
    pwdb.toto='pwdb'

    pwdb = SiteDB.get_instance()
    print pwdb.toto
    sites = pwdb.list_sites()
    print sites.toto
    print sites.__class__.__name__




