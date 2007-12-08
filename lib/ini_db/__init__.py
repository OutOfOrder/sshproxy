#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Dec 08, 20:01:24 by david
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

__plugin_name__ = "File Backend"
__description__ = """
    The File backend can handle the client database,
    the ACL rules database, and the site database.
    You can optionnaly choose either both three of them,
    or one or two only.
"""
__backend__ = True

def __init_plugin__():
    from sshproxy.config import get_config
    cfg = get_config('sshproxy')
    if cfg['acl_db'] == 'ini_db':
        from acl import FileACLDB
        FileACLDB.register()
    if cfg['client_db'] == 'ini_db':
        from client import FileClientDB, FileClientInfo
        FileClientDB.register()
        FileClientInfo.register()
    if cfg['site_db'] == 'ini_db':
        from site import FileSiteInfo, FileSiteDB
        FileSiteInfo.register()
        FileSiteDB.register()

def __setup__():
    from sshproxy import menu
    from sshproxy.config import get_config

    cfg = get_config('sshproxy')
    items = []

    if cfg['acl_db'] == 'ini_db':
        import acl
        def update(value):
            get_config('acl_db.ini')['file'] = value
        items.append(menu.MenuInput('ACL database file',
                    "",
                    get_config('acl_db.ini').get('file', raw=True),
                    cb=update))

    if cfg['client_db'] == 'ini_db':
        import client
        def update(value):
            get_config('client_db.ini')['file'] = value
        items.append(menu.MenuInput('Client database file',
                    "",
                    get_config('client_db.ini').get('file', raw=True),
                    cb=update))

    if cfg['site_db'] == 'ini_db':
        import site
        def update(value):
            get_config('site_db.ini')['db_path'] = value
        items.append(menu.MenuInput('Site database directory',
                    "",
                    get_config('site_db.ini').get('db_path', raw=True),
                    cb=update))

    return menu.MenuSub("FileDB", "", *items)

