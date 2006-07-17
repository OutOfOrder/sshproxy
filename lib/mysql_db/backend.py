#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 16, 18:10:50 by david
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
from sshproxy.client import ClientDB, ClientInfo
from sshproxy.site import SiteDB, SiteInfo
from sshproxy.util import istrue
from sshproxy.server import Server

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
    This object is meant to be used as a mixin to open only the
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

    def sql_add(self, query):
        sql = self.db.cursor()
        sql.execute(query)
        sql.close()
        result = self.sql_get('select last_insert_id()')
        return result

    def sql_del(self, query):
        sql = self.db.cursor()
        sql.execute(query)
        sql.close()

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
        query = """select id, password from client
                    where uid = '%s'""" % Q(self.username)
        result = self.sql_get(query)
        if not result:
            return

        self._id, password = result

        self.load_tags(self._id, password=password)

    def load_tags(self, id=None, **tokens):
        if id is None:
            id = self._id
        if id is None:
            return
        query = """select tag, value from acltags where object = 'client'
                                                    and id = %d""" % id
        tags = tokens
        for tag, value in self.sql_list(query):
            if len(value):
                tags[tag] = value
            else:
                query = ("delete from acltags where object = 'client'"
                         " and id = %d and tag = '%s'" % (id, Q(tag)))
                self.sql_del(query)

        self.set_tokens(**tags)

    def save(self):
        id = self._id
        if id is None:
            return
        for tag, value in self.tokens.items():
            if tag == 'username':
                continue
            elif tag == 'password':
                self.sql_set('client', **{'id': id, 'uid': self.username,
                                                'password': str(value)})
            elif value and len(str(value)):
                self.sql_set('acltags', **{'object': 'client', 'id': id,
                                       'tag': tag, 'value': str(value)})
            else:
                query = ("delete from acltags where object = 'client'"
                         " and id = %d and tag = '%s'" % (id, Q(tag)))
                self.sql_del(query)

    def auth_token_order(self):
        return ('pkey', 'password')

    def add_pkey(self, pkey, **tokens):
        ring = self.get_token('pkey', '')
        if pkey in ring:
            return False

        ring = [ k.strip() for k in ring.split('\n') if len(k.strip()) ]

        try:
            nbkey = int(get_config('sshproxy')['auto_add_key'])
            if len(ring) >= nbkey:
                return False
        except ValueError:
            # auto_add_key is not an integer, so an infinitie
            # number of keys is allowed
            pass

        ring = '\n'.join(ring + [ '%s %s@%s' % (pkey, self.username,
                                        tokens['ip_addr']) ])

        self.set_tokens(pkey=ring)
        self.save()
        return True

    def authenticate(self, **tokens):
        resp = False
        for token in self.auth_token_order():
            if token in tokens.keys() and tokens[token] is not None:
                if token == 'password':
                    query = """select id from client where uid='%s' and
                            sha1('%s') = password""" % (self.username,
                                                        tokens['password'])
                    if self.sql_get(query):
                        resp = True
                        break
                elif token == 'pkey':
                    pkeys = self.get_token(token, '').split('\n')
                    pkeys = [ pk.split()[0] for pk in pkeys if len(pk) ]
                    for pk in pkeys:
                        if pk == tokens[token]:
                            resp = True
                            break
                    ClientDB()._unauth_pkey = tokens[token]

                elif self.get_token(token) == tokens[token]:
                    resp = True
                    break
        pkey = getattr(ClientDB(), '_unauth_pkey', None)
        if resp and pkey and istrue(get_config('sshproxy')['auto_add_key']):
            tokens['pkey'] = pkey
            if self.add_pkey(**tokens):
                Server().message_client("WARNING: Your public key"
                                        " has been added")
            del ClientDB()._unauth_pkey
        return resp


class MySQLClientDB(ClientDB, MySQLDB):
    _db_handler = 'client_db'
    def __reginit__(self, **tokens):
        self.open_db()
        ClientDB.__reginit__(self, **tokens)

    def exists(self, username, **tokens):
        query = "select id from client where uid = '%s'" % Q(username)
        id = self.sql_get(query)
        if id:
            return id
        return False

    def add_client(self, username, **tokens):
        if self.exists(username, **tokens):
            return 'Client %s does already exist' % username

        query = "insert into client (uid, password) values ('%s', sha1('%s'))"
        id = self.sql_add(query % (Q(username), Q(tokens.get('password', ''))))
        if not id:
            return 'A problem occured when adding client %s' % username
        client = ClientInfo(username, **tokens)
        client.save()
        return 'Client %s added' % username

    def del_client(self, username, **tokens):
        id = self.exists(username, **tokens)
        if not id:
            return 'Client %s does not exist' % username

        query = "delete from acltags where object = 'client' and id = %d" % id
        self.sql_del(query)

        query = "delete from client where id = %d" % id
        self.sql_del(query)
        return 'Client %s deleted' % username

    def list_clients(self, **kw):
        query = "select uid from client order by uid"
        result = []
        for (username,) in self.sql_list(query):
            result.append(username)
        return result



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
        self._sid = 0
        self._lid = 0
        SiteInfo.__reginit__(self, login, name, **kw)

    def load(self):
        tags = {'name': None, 'port': None}
        self.s_tokens.add_tags(tags)
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

        self.s_tokens.add_tags(tags)

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
            self.l_tokens.add_tags(tags)

            query = """select tag, value from acltags where object = 'login'
                                                    and id = %d""" % self._lid
            tags = {}
            for tag, value in self.sql_list(query):
                tags[tag] = value

            self.l_tokens.add_tags(tags)

        tags = {'name': name, 'ip_address': ip_address, 'port': port}
        self.s_tokens.add_tags(tags)

        self.loaded = True


    def save(self):
        sid = self._sid
        if sid is None:
            return
        tok = self.s_tokens
        self.sql_set('site',
                **{'name': self.name,
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
        
        lid = self._lid
        if not lid:
            return

        tok = self.l_tokens
        self.sql_set('login',
                **{'site_id': sid,
                   'login': self.login,
                   'password': tok.get('password', ''),
                   'pkey': tok.get('pkey', ''),
                   'priority': tok.get('priority', ''),
                   })
        for tag, value in self.l_tokens.items():
            if tag in ('login', 'password', 'pkey', 'priority',
                                            'ip_address', 'port'):
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

    def list_site_users(self):
        sites = []
        query = """select id, name from site order by name"""
        for id, name in self.sql_list(query):
            query = """select login from login where site_id = %d 
                                order by priority desc""" % id
            for (login,) in self.sql_list(query):
                sites.append(SiteInfo(login, name))

        return sites

    def exists(self, sitename, **tokens):
        login, site = self.split_user_site(sitename)

        query = "select id from site where name = '%s'" % Q(site)
        id = self.sql_get(query)
        if not id:
            return False

        if not login:
            return id

        query = "select id from login where login = '%s'" % Q(login)
        id = self.sql_get(query)

        return id or False

