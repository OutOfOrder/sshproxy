#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Sep 17, 10:55:44 by david
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

from sshproxy.config import ConfigSection, get_config
from sshproxy.acl import ACLDB

from config import MySQLConfigSection
from mysql import MySQLDB, Q

class MySQLACLConfigSection(MySQLConfigSection):
    section_id = 'acl_db.mysql'

MySQLACLConfigSection.register()


class MySQLACLDB(ACLDB, MySQLDB):
    _db_handler = 'acl_db'
    def __reginit__(self):
        self.open_db()
        ACLDB.__reginit__(self)

    def load_rules(self):
        query = """select name, rule from aclrules
                    order by weight asc"""
        for acl, rule in self.sql_list(query):
            self.add_rule(acl=acl, rule=rule.strip(), updatedb=False)

    def save_rules(self):
        pass

    def add_rule(self, acl, rule=None, index=None, updatedb=True):
        index = ACLDB.add_rule(self, acl, rule, index)
        if not updatedb:
            return index
        if index < len(self.rules[acl]):
            query = """update aclrules set weight = weight+1
                                where name = '%s' and weight >= %d"""
            self.sql_update(query % (Q(acl), index))

        query = """insert into aclrules (name, rule, weight)
                                 values ('%s', '%s', %d)"""
        self.sql_add(query % (Q(acl), Q(rule), index))
        return index

    def set_rule(self, acl, rule, index):
        if not ACLDB.set_rule(self, acl, rule, index):
            return False
        query = """update aclrules set rule = '%s'
                    where name = '%s' and weight = %d"""
        self.sql_update(query % (Q(rule), Q(acl), index))
        return True

    def del_rule(self, acl, index):
        if index is not None:
            query = """delete from aclrules
                        where name = '%s' and weight = %d"""
            self.sql_del(query % (Q(acl), index))
            query = """update aclrules set weight = weight-1
                        where name = '%s' and weight >= %d"""
            self.sql_update(query % (Q(acl), index))

        return ACLDB.del_rule(self, acl, index)


