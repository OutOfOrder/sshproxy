#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 07, 02:25:18 by david
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

import os, os.path

from sshproxy.config import Config, ConfigSection, path, get_config
from sshproxy.acl import ACLDB
from sshproxy.client import ClientInfo

class FileClientConfigSection(ConfigSection):
    section_defaults = {
        'file': '@client.db',
        }
    types = {
        'file': path,
        }

Config.register_handler('client.file', FileClientConfigSection)

class FileACLConfigSection(ConfigSection):
    section_defaults = {
        'file': '@acl.db',
        }
    types = {
        'file': path,
        }

Config.register_handler('acl.file', FileACLConfigSection)


class FileClientInfo(ClientInfo):
    def authenticate(self, **tokens):
        return True
    pass

FileClientInfo.register()

class FileACLDB(ACLDB):
    def load_rules(self):
        rulefile = get_config('acl.file')['file']
        if not os.path.exists(rulefile):
            open(rulefile, 'w').close()

        fd = open(rulefile)
        for line in fd.readlines():
            acl, rule = line.strip().split(' ', 1)
            self.add_rule(acl=acl, rule=rule.lstrip())
        fd.close()

    def save_rules(self):
        fd = open(rulefile+'.new', 'w')
        for acl, rule in self.rules:
            fd.write('%s %s\n' % (acl, rule))
        fd.close()
        os.mv(rulefile+'.new', rulefile)

FileACLDB.register()





