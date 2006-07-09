#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 08, 03:10:35 by david
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
from ConfigParser import NoSectionError, SafeConfigParser as ConfigParser

from sshproxy.config import Config, ConfigSection, path, get_config
from sshproxy.acl import ACLDB
from sshproxy.client import ClientInfo
from sshproxy.site import SiteInfo

class FileClientConfigSection(ConfigSection):
    section_defaults = {
        'file': '@client.db',
        }
    types = {
        'file': path,
        }

Config.register_handler('client_db.file', FileClientConfigSection)

class FileACLConfigSection(ConfigSection):
    section_defaults = {
        'file': '@acl.db',
        }
    types = {
        'file': path,
        }

Config.register_handler('acl_db.file', FileACLConfigSection)

class FileSiteConfigSection(ConfigSection):
    section_defaults = {
        'db_path': '@site.db',
        }
    types = {
        'db_path': path,
        }

Config.register_handler('site_db.file', FileSiteConfigSection)

class FileClientInfo(ClientInfo):
    def get_config_file(self):
        clientfile = get_config('client_db.file')['file']
        if not os.path.exists(clientfile):
            open(clientfile, 'w').close()
            # no need to parse an empty file
            return None

        file = ConfigParser()
        file.read(clientfile)
        return file

    def load(self):
        file = self.get_config_file()
        if not file:
            return

        try:
            tokens = dict(file.items(self.username))
        except NoSectionError:
            return

        self.set_tokens(**tokens)


    def save(self):
        file = self.get_config_file()
        if not file:
            return

        for key, value in self.tokens.items():
            file.set(self.username, key, value)

        clientfile = get_config('client_db.file')['file']
        fd = open(clientfile+'.new', 'w')
        file.write(fd)
        fd.close()
        os.rename(clientfile+'.new', clientfile)
        

    def auth_token_order(self):
        return ('pkey', 'password')


FileClientInfo.register()


class FileACLDB(ACLDB):
    def load_rules(self):
        rulefile = get_config('acl_db.file')['file']
        if not os.path.exists(rulefile):
            open(rulefile, 'w').close()

        fd = open(rulefile)
        for line in fd.readlines():
            line = line.strip()
            if not line or line[0] == '#':
                continue
            try:
                acl, rule = line.split(' ', 1)
            except ValueError:
                acl, rule = line.strip(), None
            self.add_rule(acl=acl, rule=rule.lstrip())
        fd.close()

    def save_rules(self):
        fd = open(rulefile+'.new', 'w')
        for acl, rule in self.rules:
            fd.write('%s %s\n' % (acl, rule))
        fd.close()
        os.mv(rulefile+'.new', rulefile)

FileACLDB.register()


class FileSiteInfo(SiteInfo):
    def get_config_file(self, sitename):
        sitepath = get_config('site_db.file')['db_path']
        if not os.path.exists(sitepath):
            os.makedirs(sitepath)
            # no need to search for the site file
            return None
        sitefile = os.path.join(sitepath, sitename)
        if not os.path.exists(sitefile):
            return None

        file = ConfigParser()
        file.read(sitefile)
        return file

    def load(self):
        file = self.get_config_file(self.name)
        if not file:
            return

        site_section = file.defaults()
        if not len(site_section):
            return

        self.tags.add_tags(site_section)

        try:
            tags = dict(file.items(self.login))
        except NoSectionError:
            return

        self.tags.add_tags(tags)
        self.loaded = True



    def save(self):
        file = self.get_config_file(self.name)
        if not file:
            return

        for key, value in self.tokens.items():
            file.set(self.username, key, value)

        sitepath = get_config('site_db.file')['db_path']
        sitefile = os.path.join(sitepath, sitename)
        fd = open(sitefile+'.new', 'w')
        file.write(fd)
        fd.close()
        os.rename(sitefile+'.new', sitefile)
        

FileSiteInfo.register()




