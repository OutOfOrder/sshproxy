#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 31, 00:04:53 by david
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

__plugin_name__ = "MySQL Backend"
__description__ = """
    The MySQL backend can handle the client database,
    the ACL rules database, and the site database.
    You can optionnaly choose either both three of them,
    or one or two only.
"""
__backend__ = True

def __init_plugin__():
    from sshproxy.config import get_config
    cfg = get_config('sshproxy')
    if cfg['acl_db'] == 'mysql_db':
        from acl import MySQLACLDB
        MySQLACLDB.register()
    if cfg['client_db'] == 'mysql_db':
        from client import MySQLClientInfo, MySQLClientDB
        MySQLClientInfo.register()
        MySQLClientDB.register()
    if cfg['site_db'] == 'mysql_db':
        from site import MySQLSiteInfo, MySQLSiteDB
        MySQLSiteInfo.register()
        MySQLSiteDB.register()

def get_menu_items(db_type):
    from sshproxy import menu
    from sshproxy.config import get_config
    def update(value, item, db_type):
        cfg = get_config('%s.mysql' % db_type)
        cfg[item] = value
    cfg = get_config('%s.mysql' % db_type)
    return [ menu.MenuInput(title,
                           "",
                           cfg[name],
                           update,
                           item=name,
                           db_type=db_type)
            for name, title in (('host', 'Database host'),
                                ('user', 'Database user'),
                                ('password', 'Database password'),
                                ('db', 'Database name'),
                                ('port', 'Database port')) ]
def __setup__():
    from sshproxy import menu
    from sshproxy.config import get_config
    import config

    cfg = get_config('sshproxy')
    items = []

    if cfg['acl_db'] == 'mysql_db':
        config.MySQLACLConfigSection.register(True)
        items.append(menu.Menu('ACL database',
                    "",
                    *get_menu_items('acl_db')))

    if cfg['client_db'] == 'mysql_db':
        config.MySQLClientConfigSection.register(True)
        items.append(menu.Menu('Client database file',
                    "",
                    *get_menu_items('client_db')))

    if cfg['site_db'] == 'mysql_db':
        config.MySQLSiteConfigSection.register(True)
        items.append(menu.Menu('Site database directory',
                    "",
                    *get_menu_items('site_db')))

    return menu.MenuSub("MySQLDB", "", *items)

