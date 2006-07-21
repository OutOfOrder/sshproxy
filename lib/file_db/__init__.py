#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 21, 02:15:22 by david
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


def __init_plugin__():
    from sshproxy.config import get_config
    cfg = get_config('sshproxy')
    if cfg['acl_db'] == 'file_db':
        from acl import FileACLDB
        FileACLDB.register()
    if cfg['client_db'] == 'file_db':
        from client import FileClientDB, FileClientInfo
        FileClientDB.register()
        FileClientInfo.register()
    if cfg['site_db'] == 'file_db':
        from site import FileSiteInfo, FileSiteDB
        FileSiteInfo.register()
        FileSiteDB.register()

