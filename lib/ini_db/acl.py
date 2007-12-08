#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Dec 08, 20:11:32 by david
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

from sshproxy.config import ConfigSection, path, get_config
from sshproxy.acl import ACLDB
from sshproxy import log


class FileACLConfigSection(ConfigSection):
    section_id = 'acl_db.ini'
    section_defaults = {
        'file': '@acl.db',
        }
    types = {
        'file': path,
        }

FileACLConfigSection.register()

class FileACLDB(ACLDB):
    def load_rules(self):
        rulefile = get_config('acl_db.ini')['file']
        if not os.path.exists(rulefile):
            open(rulefile, 'w').close()
            os.chmod(rulefile, 0600)
            # no need to parse an empty file
            return None

        fd = open(rulefile)
        nline = []
        line = []
        for linepart in fd.readlines():
            if not linepart.strip() or linepart.strip()[0] == '#':
                continue

            if linepart[0] not in (' ', '\t'):
                nline = [ linepart.strip() ]
                if not line:
                    line = nline
                    continue
            else:
                line.append(linepart.strip())
                continue

            try:
                acl, rule = (' '.join(line)).split(':', 1)
                if rule is None or not rule.strip():
                    raise ValueError
            except ValueError:
                # drop rule, it won't parse anyway
                log.warning('Dropped unparseable rule %s' % acl)
                line = nline
                continue
            self.add_rule(acl=acl, rule=rule.lstrip())
            line = nline

        if line:
            try:
                acl, rule = (' '.join(line)).split(':', 1)
                if rule is None or not rule.strip():
                    raise ValueError
                self.add_rule(acl=acl, rule=rule.lstrip())
            except ValueError:
                # drop rule, it won't parse anyway
                log.warning('Dropped unparseable rule %s' % acl)
                pass
        fd.close()

    def save_rules(self):
        rulefile = get_config('acl_db.ini')['file']
        if not os.path.exists(rulefile):
            open(rulefile, 'w').close()

        fd = open(rulefile+'.new', 'w')
        for acl in self.rules.keys():
            for rule in self.rules[acl]:
                fd.write('%s:\n    %s\n\n'
                                % (acl, rule.rule.replace('\n', '\n    ')))
        fd.close()
        os.rename(rulefile+'.new', rulefile)

