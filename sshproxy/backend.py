#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 08, 14:03:10 by david
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
from acl import ACLDB, ACLTags
from client import ClientDB
from site import SiteDB


class Backend(Registry):
    _class_id = 'Backend'
    _singleton = True

    def __reginit__(self):
        self.authenticated = False
        self.authorized = False
        self.clientdb = ClientDB()
        self.acldb = ACLDB()
        self._site_cache = (None, None)
        self.tags = ACLTags()


    def authenticate(self, username, **tokens):
        if self.clientdb.authenticate(username, **tokens):
            self.authenticated = True
        else:
            self.authenticated = False
        return self.authenticated


    def authorize(self, user_site):
        sitedb = SiteDB()
        if sitedb.authorize(user_site, self.clientdb):
            self.authorized = True
            self.sitedb = sitedb
        else:
            self.authorized = False
        return self.authorized


    def is_admin(self):
        return self.acldb.check(acl='admin', client=self.clientdb.get_tags())


    def get_client(self, username=None, **kw):
        return self.clientdb.get_user_info(username=username, **kw)


    def get_site_tags(self):
        return self.sitedb.get_tags()

    def get_site(self):
        return self.sitedb.get_site()

Backend.register()

def get_backend():
    return Backend()
