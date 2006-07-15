#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 15, 01:02:01 by david
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

import MySQLdb
import os, os.path

from sshproxy.config import Config, ConfigSection, path, get_config
from sshproxy.acl import ACLDB
from sshproxy.client import ClientInfo
from sshproxy.site import SiteDB, SiteInfo

class MySQLConfigSection(ConfigSection):
    section_defaults = {
        'host': 'localhost',
        'user': 'sshproxy',
        'password': 'sshproxypw',
        'db': 'sshproxy',
        'port': 3306,
        }
    types = {
        'port': int,
        }

Config.register_handler('client_db.mysql', MySQLConfigSection)
Config.register_handler('acl_db.mysql', MySQLConfigSection)
Config.register_handler('site_db.mysql', MySQLConfigSection)


def Q(item):
    """Safe quote mysql values"""
    if item is None:
        return ''
    return str(item).replace("'", "\\'")

class MySQLDB(object):
    """
    This object is a meant to be used as a mixin to open only the
    necessary number of connections to the database.

    It implements the open_db method, that should be called from __reginit__.
    """
    __db = {}
    def open_db(self):
        cfg = get_config('%s.mysql' % self._db_handler)
        conid = 'mysql://%s@%s:%s/%s' % (cfg['user'], cfg['host'],
                                         cfg['port'], cfg['db'])
        if not self.__db.has_key(conid):
            try:
                MySQLDB.__db[conid] = MySQLdb.connect(host=cfg['host'],
                                                      port=cfg['port'],
                                                      db=cfg['db'],
                                                      user=cfg['user'],
                                                      passwd=cfg['password'])
            except:
                if not os.environ.has_key('SSHPROXY_WIZARD'):
                    raise

        self.db = self.__db[conid]

    def sql_get(self, query):
        sql = self.db.cursor()
        sql.execute(query)
        result = sql.fetchone()
        sql.close()
        if not result or not len(result):
            return None
        if len(result) == 1:
            return result[0]
        return result

    def sql_list(self, query):
        sql = self.db.cursor()
        sql.execute(query)
        for result in sql.fetchall():
            yield result
        sql.close()
        return

    def sql_set(self, table, **fields):
        query = """replace %s set %s"""
        q = []
        for field, value in fields.items():
            q.append("%s='%s'" % (field, Q(value)))
        sql = self.db.cursor()
        sql.execute(query % (table, ', '.join(q)))
        sql.close()




class MySQLClientInfo(ClientInfo, MySQLDB):
    _db_handler = 'client_db'
    def __reginit__(self, username, **tokens):
        self.open_db()
        ClientInfo.__reginit__(self, username, **tokens)


    def load(self):
        query = """select id from client
                    where uid = '%s'""" % Q(self.username)
        self._id = self.sql_get(query)

        self.load_tags()

    def load_tags(self, id=None):
        if id is None:
            id = self._id
        if id is None:
            return
        query = """select tag, value from acltags where object = 'client'
                                                    and id = %d""" % id
        tags = {}
        for tag, value in self.sql_list(query):
            tags[tag] = value

        self.set_tokens(**tags)

    def save(self):
        for key, value in self.tokens.items():
            if key in ('username', 'password'):
                continue
            self.sql_set('acltags', **{'object': 'client', 'id': self._id,
                                       'tag': key, 'value': value})

    def auth_token_order(self):
        return ('pkey', 'password')

    def authenticate(self, **tokens):
        for token in self.auth_token_order():
            if token in tokens.keys() and tokens[token] is not None:
                if token == 'password':
                    query = """select id from client where uid='%s' and
                            sha1('%s') = password""" % (self.username,
                                                        tokens['password'])
                    if self.sql_get(query):
                        return True
                elif self.get_token(token) == tokens[token]:
                    return True
        return False



class MySQLACLDB(ACLDB, MySQLDB):
    _db_handler = 'acl_db'
    def __reginit__(self):
        self.open_db()
        ACLDB.__reginit__(self)

    def load_rules(self):
        query = """select name, rule from aclrules
                    order by weight desc"""
        for acl, rule in self.sql_list(query):
            self.add_rule(acl=acl, rule=rule.strip())

    def save_rules(self):
        pass



class MySQLSiteInfo(SiteInfo, MySQLDB):
    _db_handler = 'site_db'
    def __reginit__(self, login, name, **kw):
        self.open_db()
        SiteInfo.__reginit__(self, login, name, **kw)

    def load(self):
        tags = {'name': None, 'port': None, 'pkey': None}
        self.tags.add_tags(tags)
        query = """select id, name, ip_address, port from site
                                        where name = '%s'""" % Q(self.name)
        site = self.sql_get(query)
        if not site:
            return
        id, name, ip_address, port = site

        query = """select tag, value from acltags where object = 'site'
                                                    and id = %d""" % id
        tags = {}
        for tag, value in self.sql_list(query):
            tags[tag] = value

        self.tags.add_tags(tags)

        # TODO: handle the default case, see also in file backend
        query = """select id, login, password, pkey, priority from login
                    where site_id = %d and ('%s' = 'None' or '%s' = login)
                    order by priority desc""" % (id, Q(self.login), Q(self.login))

        login = self.sql_get(query)
        if not login:
            self.site = None
            return
        
        id, login, password, pkey, priority = login

        tags = {'login': login, 'password': password,
                'priority': priority, 'pkey': pkey}
        self.tags.add_tags(tags)

        query = """select tag, value from acltags where object = 'login'
                                                    and id = %d""" % id
        tags = {}
        for tag, value in self.sql_list(query):
            tags[tag] = value

        self.tags.add_tags(tags)

        tags = {'name': name, 'ip_address': ip_address, 'port': port}
        self.tags.add_tags(tags)

        self.loaded = True


    def save(self):
       pass 


class MySQLSiteDB(SiteDB, MySQLDB):
    _db_handler = 'site_db'
    def __reginit__(self, **kw):
        self.open_db()
        SiteDB.__reginit__(self, **kw)

    def list_site_users(self):
        sites = []
        query = """select id, name from site order by name"""
        for id, name in self.sql_list(query):
            query = """select login from login where site_id = %d 
                                order by priority desc""" % id
            for (login,) in self.sql_list(query):
                sites.append(SiteInfo(login, name))

        return sites

