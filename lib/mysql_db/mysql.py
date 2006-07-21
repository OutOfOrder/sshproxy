#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 21, 02:32:52 by david
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

import os
import MySQLdb

from sshproxy.config import get_config

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

