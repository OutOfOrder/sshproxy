#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 29, 14:12:23 by david
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

from sshproxy.config import ConfigSection, path


class FileClientConfigSection(ConfigSection):
    section_id = 'client_db.file'
    section_defaults = {
        'file': '@client.db',
        }
    types = {
        'file': path,
        }

class FileSiteConfigSection(ConfigSection):
    section_id = 'site_db.file'
    section_defaults = {
        'db_path': '@site.db',
        }
    types = {
        'db_path': path,
        }

class FileACLConfigSection(ConfigSection):
    section_id = 'acl_db.file'
    section_defaults = {
        'file': '@acl.db',
        }
    types = {
        'file': path,
        }

