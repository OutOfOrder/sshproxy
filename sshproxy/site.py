#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Mar 20, 15:07:09 by david
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


class SiteInfo(Registry):
    _class_id = 'SiteInfo'
    def __reginit__(self, login, name, **kw):
        self.login = login
        self.name = name
        self.loaded = False
        self.s_tokens = ACLTags()
        self.l_tokens = ACLTags()
        self.load()
        self.set_tokens(**kw)


    def load(self):
        pass


    def save(self):
        pass


    def get_token(self, token, default=None):
        if self.login:
            toks = self.l_tokens
        else:
            toks = self.s_tokens
        return toks.get(token, default)


    def get_tags(self, strict=False):
        tags = ACLTags()
        if not strict or not self.login:
            tags.update(self.s_tokens)
        if not strict or self.login:
            tags.update(self.l_tokens)
        if not strict or not self.login:
            # ip_address should not be overriden by the login tags
            tags['ip_address'] = self.s_tokens.get('ip_address', '')
        if self.login:
            tags['login'] = self.login
        tags['name'] = self.name
        return tags

    def set_tokens(self, **tokens):
        """
        Set the authentication or context token of the site.

        @param **tokens: the tokens to be set.
        @type **tokens: dict
        @return: None
        """
        if self.login:
            toks = self.l_tokens
        else:
            toks = self.s_tokens
        for token, value in tokens.items():
            # XXX: how to encrypt the tokens ? encrypt them all ?
            toks[token] = str(value)


SiteInfo.register()


class SiteDB(Registry):
    _class_id = 'SiteDB'

    def __reginit__(self, **kw):
        self.siteinfo = None
        self.userinfo = None

    @staticmethod
    def split_user_site(user_site):
        s = user_site.split('@')
        if len(s) >= 2:
            login = '@'.join(s[:-1])
            if not len(login):
                login = None
            return login, s[-1]
        else:
            return None, s[-1]


    def authorize(self, user_site, client, need_login=False):
        if not isinstance(user_site, SiteInfo):
            user, site = self.split_user_site(user_site)
            siteinfo = SiteInfo(user, site)
        else:
            siteinfo = user_site

        if not siteinfo.loaded:
            return False

        if not ACLDB().check(acl='authorize', client=client.get_tags(),
                                              site=siteinfo.get_tags()):
            return False

        self.siteinfo = siteinfo
        if need_login and siteinfo.login is None:
            self.select_login()

        return True


    def get_tags(self):
        tags = ACLTags()
        tags.update(self.siteinfo.get_tags())
        return tags

    def get_site(self, user_site=None):
        if user_site is not None:
            user, site = self.split_user_site(user_site)
            return SiteInfo(user, site)
        return self.siteinfo

    def select_login(self, login=None):
        if not self.siteinfo:
            return
        if login is None:
            logins = []
            for l in self.list_site_users():
                if l.login and l.name == self.siteinfo.name:
                    priority = l.get_token('priority')
                    try:
                        priority = int(priority)
                    except ValueError:
                        pass
                    except TypeError:
                        priority = 0
                    logins.append((priority, l))
            logins.sort(reverse=True)
            self.siteinfo = logins[0][1]
        elif self.exists('%s@%s' % (login, self.siteinfo.name)):
            self.siteinfo = SiteInfo(login, self.siteinfo.name)

    def list_site_users(self, **tokens):
        """
        List all login@site.
        Return a list of SiteInfo instances.
        """
        return []

    def exists(self, sitename, **tokens):
        return False

    def add_site(self, sitename, **tokens):
        return "Not implemented"

    def del_site(self, sitename, **tokens):
        return "Not implemented"

    def tag_site(self, sitename, **tokens):
        login, site = self.split_user_site(sitename)

        if login == '*':
            return "'*' is not allowed, be more specific."

        if 'port' in tokens.keys():
            port = tokens.get('port')
            try:
                port = int(port)
                if not (0 < port < 65536):
                    raise ValueError
            except ValueError:
                return ('Port must be numeric and have a strictly positive '
                        'value inferior to 65536')
        #    tokens['port'] = port

        site = SiteInfo(login, site, **tokens)
        if tokens:
            #site.set_tokens(**tokens)
            site.save()
        return site.get_tags(strict=True)

SiteDB.register()
