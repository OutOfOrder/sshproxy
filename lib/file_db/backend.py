#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 10, 00:43:07 by david
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
from sshproxy.site import SiteDB, SiteInfo

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




class FileACLDB(ACLDB):
    def load_rules(self):
        rulefile = get_config('acl_db.file')['file']
        if not os.path.exists(rulefile):
            open(rulefile, 'w').close()

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
                if rule is None:
                    raise ValueError
            except ValueError:
                # drop rule, it won't parse anyway
                continue
            self.add_rule(acl=acl, rule=rule.lstrip())
            line = nline
        fd.close()

    def save_rules(self):
        fd = open(rulefile+'.new', 'w')
        for acl, rule in self.rules:
            fd.write('%s %s\n' % (acl, rule))
        fd.close()
        os.mv(rulefile+'.new', rulefile)



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
        


class FileSiteDB(SiteDB):
    def list_site_users(self):
        sitepath = get_config('site_db.file')['db_path']
        if not os.path.exists(sitepath):
            os.makedirs(sitepath)
            # no need to search for the site files
            return []
        sitefiles = os.listdir(sitepath)
        sites = []
        for sitefile in sitefiles:
            if sitefile[0] == '.':
                continue
            file = ConfigParser()
            file.read(os.path.join(sitepath, sitefile))
            for user in file.sections():
                sites.append(SiteInfo(user, sitefile))

        return sites

