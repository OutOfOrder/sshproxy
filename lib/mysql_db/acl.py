#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 30, 23:48:23 by david
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

from config import MySQLACLConfigSection
from mysql import MySQLDB, Q

MySQLACLConfigSection.register()

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



