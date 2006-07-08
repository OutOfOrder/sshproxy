#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 08, 02:39:40 by david
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
from acl import ACLTags, ACLDB


#class UserInfo(Registry):
#    _class_id = 'UserInfo'
#    def __init__(self, login, **kw):
#        self.login = login
#        self.tags = ACLTags.get_instance()
#
#    def get_tags(self):
#        tags = ACLTags.get_instance()
#        tags.add_tag('login', self.login)
#        return tags
#
#UserInfo.register()

class SiteInfo(Registry):
    _class_id = 'SiteInfo'
    def __init__(self, login, name, **kw):
        self.tags = ACLTags.get_instance(kw)
        self.login = login
        self.name = name
        self.loaded = False
        self.load()

    def load(self):
        pass

    def save(self):
        pass

    def get_tags(self):
        tags = ACLTags.get_instance()
        tags.update(self.tags)
        tags.add_tag('login', self.login or '')
        tags.add_tag('name', self.name)
        return tags


SiteInfo.register()


class SiteDB(Registry):
    _class_id = 'SiteDB'
    _singleton = True

    def __init__(self, **kw):
        self.siteinfo = None
        self.userinfo = None

    @staticmethod
    def split_user_site(user_site):
        s = user_site.split('@')
        if len(s) >= 2:
            return '@'.join(s[:-1]), s[-1]
        else:
            return None, s[0]


    def authorize(self, user_site, client, **tokens):
        user, site = self.split_user_site(user_site)
        siteinfo = SiteInfo.get_instance(user, site, **tokens)

        if not siteinfo.loaded:
            return False

        if not ACLDB.get_instance().check(acl='authorize',
                                                    client=client.get_tags(),
                                                    site=siteinfo.get_tags()):
            return False

        self.siteinfo = siteinfo
        return True


    def get_tags(self):
        tags = ACLTags.get_instance()
        tags.update(self.siteinfo.get_tags())
        #tags.update(self.userinfo.get_tags())
        return tags

    def get_site(self):
        return self.siteinfo

################################################################
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


