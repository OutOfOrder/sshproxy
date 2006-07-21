#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 21, 03:08:35 by david
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
from sshproxy.site import SiteDB, SiteInfo

from file import NoSectionError, FileConfigParser as ConfigParser

class FileSiteConfigSection(ConfigSection):
    section_defaults = {
        'db_path': '@site.db',
        }
    types = {
        'db_path': path,
        }

Config.register_handler('site_db.file', FileSiteConfigSection)


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

        self.s_tokens.add_tags(site_section)

        try:
            tags = dict(file.items(self.login))
        except NoSectionError:
            return

        self.l_tokens.add_tags(tags)
        self.loaded = True



    def save(self):
        file = self.get_config_file(self.name)
        if not file:
            return

        if self.login:
            for key, value in self.l_tokens.items():
                file.set(self.login, key, str(value or ''))
        else:
            for key, value in self.s_tokens.items():
                file.set('DEFAULT', key, str(value or ''))

        sitepath = get_config('site_db.file')['db_path']
        sitefile = os.path.join(sitepath, self.name)
        fd = open(sitefile+'.new', 'w')
        file.write(fd)
        fd.close()
        os.rename(sitefile+'.new', sitefile)
        


class FileSiteDB(SiteDB):
    def list_site_users(self, **tokens):
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
            users = file.sections()
            if len(users):
                for user in users:
                    sites.append(SiteInfo(user, sitefile))
            else:
                sites.append(SiteInfo(None, sitefile))


        return sites

    def exists(self, sitename, **tokens):
        login, name = self.split_user_site(sitename)
        sites = self.list_site_users(**tokens)
        for site in sites:
            if site.login == login and site.name == name:
                return True
        return False
