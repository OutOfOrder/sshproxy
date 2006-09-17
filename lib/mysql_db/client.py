#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Sep 17, 10:56:25 by david
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

import sha

from sshproxy.config import get_config
from sshproxy.client import ClientDB, ClientInfo
from sshproxy.util import istrue
from sshproxy.server import Server

from config import MySQLConfigSection
from mysql import MySQLDB, Q

class MySQLClientConfigSection(MySQLConfigSection):
    section_id = 'client_db.mysql'

MySQLClientConfigSection.register()


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


    def authenticate(self, **tokens):
        resp = False
        for token in self.auth_token_order():
            if token in tokens.keys() and tokens[token] is not None:
                if token == 'password':
                    query = """select id from client where uid='%s' and
                            '%s' = password""" % (Q(self.username),
                                    Q(sha.new(tokens['password']).hexdigest()))
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
                                        " has been added to the keyring\n")
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

        query = "insert into client (uid, password) values ('%s', '%s')"
        id = self.sql_add(query % (Q(username), Q(tokens.get('password', ''))))
        if not id:
            return 'A problem occured when adding client %s' % username
        client = ClientInfo(username, **tokens)
        client.save()
        return 'Client %s added' % username

    def del_client(self, username, **tokens):
        if self.clientinfo.username == username:
            return "Don't delete yourself!"
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

