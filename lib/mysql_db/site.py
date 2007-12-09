#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Dec 09, 04:02:36 by david
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

from sshproxy.acl import ACLRule
from sshproxy.site import SiteDB, SiteInfo

from config import MySQLConfigSection
from mysql import MySQLDB, Q

class MySQLSiteConfigSection(MySQLConfigSection):
    section_id = 'site_db.mysql'

MySQLSiteConfigSection.register()


class MySQLSiteInfo(SiteInfo, MySQLDB):
    _db_handler = 'site_db'
    def __reginit__(self, login, name, **kw):
        self.open_db()
        self._sid = 0
        self._lid = 0
        SiteInfo.__reginit__(self, login, name, **kw)

    def load(self):
        query = """select id, name, ip_address, port from site
                                        where name = '%s'""" % Q(self.name)
        site = self.sql_get(query)
        if not site:
            return
        self._sid, name, ip_address, port = site

        query = """select tag, value from acltags where object = 'site'
                                                and id = %d""" % self._sid
        tags = {}
        for tag, value in self.sql_list(query):
            tags[tag] = value

        self.s_tokens.update(tags)

        tags = {'name': name, 'ip_address': ip_address, 'port': port}
        self.s_tokens.update(tags)

        # TODO: handle the default case, see also in file backend
        query = """select id, login, password, pkey, priority from login
                    where site_id = %d and ('%s' = 'None' or '%s' = login)
                    order by priority desc""" % (self._sid, Q(self.login),
                                                Q(self.login))

        login = self.sql_get(query)
        if login:
        
            self._lid, login, password, pkey, priority = login

            tags = {'login': login, 'password': password,
                    'priority': priority, 'pkey': pkey}
            self.l_tokens.update(tags)

            query = """select tag, value from acltags where object = 'login'
                                                    and id = %d""" % self._lid
            tags = {}
            for tag, value in self.sql_list(query):
                tags[tag] = value

            self.l_tokens.update(tags)

        self.loaded = True


    def save(self):
        sid = self._sid
        if sid is None:
            return

        if not self.login:
            tok = self.s_tokens
            self.sql_set('site',
                    **{'id': sid,
                       'name': self.name,
                       'ip_address': tok.get('ip_address', ''),
                       'port': tok.get('port', '22'),
                       })
            for tag, value in self.s_tokens.items():
                if tag in ('name', 'ip_address', 'port'):
                    continue
                elif value and len(str(value)):
                    self.sql_set('acltags', **{'object': 'site', 'id': sid,
                                           'tag': tag, 'value': str(value)})
                else:
                    query = ("delete from acltags where object = 'site'"
                             " and id = %d and tag = '%s'" % (sid, Q(tag)))
                    self.sql_del(query)
        
        else:
            lid = self._lid
            if not lid:
                return
    
            tok = self.l_tokens
            self.sql_set('login',
                    **{'id': lid,
                       'site_id': sid,
                       'login': self.login,
                       'password': tok.get('password', ''),
                       'pkey': tok.get('pkey', ''),
                       'priority': tok.get('priority', ''),
                       })
            for tag, value in self.l_tokens.items():
                if tag in ('name', 'login', 'password', 'pkey', 'priority'):
                    continue
                elif value and len(str(value)):
                    self.sql_set('acltags', **{'object': 'login', 'id': lid,
                                           'tag': tag, 'value': str(value)})
                else:
                    query = ("delete from acltags where object = 'login'"
                             " and id = %d and tag = '%s'" % (lid, Q(tag)))
                    self.sql_del(query)


class MySQLSiteDB(SiteDB, MySQLDB):
    _db_handler = 'site_db'
    def __reginit__(self, **kw):
        self.open_db()
        SiteDB.__reginit__(self, **kw)

    def list_site_users(self, **tokens):
        sites = []
        query = """select id, name from site order by name"""
        for id, name in self.sql_list(query):
            query = """select login from login where site_id = %d 
                                order by priority desc""" % id
            logins = []
            for (login,) in self.sql_list(query):
                logins.append(SiteInfo(login, name))

            if not len(logins):
                logins.append(SiteInfo('ORPHAN', name, priority=0))

            sites += logins

        filter = tokens.get('filter', tokens.get('f', None))
        if filter:
            siteinfos = []
            for site in sites:
                if ACLRule('list_site_users_filter',
                            filter).eval(namespace={'site':site.get_tags()}):
                    siteinfos.append(site)

            sites = siteinfos

        return sites

    def exists(self, sitename, **tokens):
        login, site = self.split_user_site(sitename)

        if login == '*':
            login = None

        query = "select id from site where name = '%s'" % Q(site)
        id = self.sql_get(query)
        if not id:
            return False

        if not login:
            return id

        query = "select id from login where login = '%s' and site_id = %d"
        id = self.sql_get(query % (Q(login), id))

        return id or False

    def add_site(self, sitename, **tokens):
        login, site = self.split_user_site(sitename)

        if login == '*':
            return "'*' is not allowed, be more specific."

        if not login:
            if self.exists(site, **tokens):
                return 'Site %s does already exist' % site
            # create site
            port = tokens.get('port', 22)
            try:
                port = int(port)
                if not (0 < port < 65536):
                    raise ValueError
            except ValueError:
                return ('Port must be numeric and have a strictly positive '
                        'value inferior to 65536')

            query = ("insert into site (name, ip_address, port) "
                               "values ('%s', '%s', '%s')")
            sid = self.sql_add(query % (Q(site),
                                       Q(tokens.get('ip_address', '')),
                                       port))
            if not sid:
                return 'A problem occured when adding site %s' % sitename

        elif not self.exists(site, **tokens):
            # if site does not exist and a login was given, exit with an error
            return 'Please create site %s first' % site
        
        else:
            if self.exists(sitename, **tokens):
                return 'Site %s does already exist' % sitename

            sid = self.sql_get("select id from site where name = '%s'"
                                                                    % Q(site))
            query = ("insert into login (site_id, login, password) "
                               "values (%d, '%s', '%s')")
            lid = self.sql_add(query % (sid,
                                       Q(login),
                                       Q(tokens.get('password', ''))))
            if not lid:
                return 'A problem occured when adding site %s' % sitename

        site = SiteInfo(login, site, **tokens)
        site.save()
        return 'Site %s added' % sitename

    def _del_login(self, login_id, **tokens):
        query = "delete from acltags where object = 'login' and id = %d"
        self.sql_del(query % login_id)

        query = "delete from login where id = %d"
        self.sql_del(query % login_id)

    def del_site(self, sitename, **tokens):
        login, site = self.split_user_site(sitename)

        if login == '*':
            sitename = name

        sid = self.exists(sitename, **tokens)
        if not sid:
            return 'Site %s does not exist' % sitename

        if login:
            ret = False
            if login == '*':
                query = "select login from login where site_id = %d" % sid
                for lid in self.sql_list(query):
                    self._del_login(lid, **tokens)
                    ret = True
                sitename = '*@%s' % name

            else:
                lid = self.exists(sitename, **tokens)
                if lid:
                    self._del_login(lid, **tokens)
                    ret = True

            if not ret:
                return 'Site %s does not exist' % sitename

            return 'Site %s deleted' % sitename

        else:
            query = "select count(*) from login where site_id = %d"
            count = self.sql_get(query % sid)
            if count > 0:
                return "Site %s has still %d logins" % (sitename, count)

            query = "delete from acltags where object = 'site' and id = %d"
            self.sql_del(query % sid)

            query = "delete from site where id = %d"
            self.sql_del(query % sid)

