#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Mar 20, 15:34:48 by david
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
from sshproxy.site import SiteDB, SiteInfo

from file import NoSectionError, FileConfigParser as ConfigParser

class FileSiteConfigSection(ConfigSection):
    section_id = 'site_db.file'
    section_defaults = {
        'db_path': '@site.db',
        }
    types = {
        'db_path': path,
        }

FileSiteConfigSection.register()

def get_config_file(name):
    sitepath = get_config('site_db.file')['db_path']
    if not os.path.exists(sitepath):
        os.makedirs(sitepath)
        # no need to search for the site file
        return None
    sitefile = os.path.join(sitepath, name)
    if not os.path.exists(sitefile):
        return None

    file = ConfigParser()
    file.read(sitefile)
    return file


class FileSiteInfo(SiteInfo):
    def load(self):
        file = get_config_file(self.name)
        if not file:
            return

        site_section = file.defaults()
        if not len(site_section):
            return

        self.s_tokens.update(site_section)

        try:
            tags = dict(file.items(self.login))
        except NoSectionError:
            tags = {}

        self.l_tokens.update(tags)
        self.loaded = True



    def save(self):
        file = get_config_file(self.name)
        if not file:
            return

        if self.login:
            if not file.has_section(self.login):
                file.add_section(self.login)
            for tag, value in self.l_tokens.items():
                file.set(self.login, tag, str(value or ''))
        else:
            for tag, value in self.s_tokens.items():
                file.set('DEFAULT', tag, str(value or ''))

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
        if login == '*':
            login = None
        sites = self.list_site_users(**tokens)
        for site in sites:
            if login in (None, site.login) and site.name == name:
                return True
        return False

    def add_site(self, sitename, **tokens):
        sitepath = get_config('site_db.file')['db_path']
        if not os.path.exists(sitepath):
            os.makedirs(sitepath)
        
        login, name = self.split_user_site(sitename)
        if login == '*':
            return "'*' is not allowed, be more specific."

        if self.exists(sitename, **tokens):
            return 'Site %s does already exist' % sitename


        sitefile = os.path.join(sitepath, name)
        if not os.path.exists(sitefile):
            if login:
                return 'Site %s does not exist. Please create it first.' % name
            # touch the file
            open(sitefile, 'w').close()

        siteinfo = SiteInfo(login, name, **tokens)
        siteinfo.save()
        return 'Site %s added' % sitename


    def del_site(self, sitename, **tokens):
        sitepath = get_config('site_db.file')['db_path']

        login, name = self.split_user_site(sitename)

        if login == '*':
            sitename = name

        if not os.path.exists(sitepath) or not self.exists(sitename, **tokens):
            return 'Site %s does not exist' % sitename

        sitefile = os.path.join(sitepath, name)
        file = get_config_file(name)

        if login:
            ret = False
            if login == '*':
                for login in file.sections():
                    file.remove_section(login)
                    ret = True
                sitename = '*@%s' % name
            else:
                file.remove_section(login)
                ret = True

            fd = open(sitefile+'.new', 'w')
            file.write(fd)
            fd.close()
            os.rename(sitefile+'.new', sitefile)

            if not ret:
                return 'Site %s does not exist' % sitename

            return 'Site %s deleted.' % sitename

        count = len(file.sections())
        if count > 0:
            return "Site %s has still %d logins" % (sitename, count)

        os.unlink(sitefile)
        return 'Site %s deleted' % sitename


