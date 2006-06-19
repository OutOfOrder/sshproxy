#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jun 19, 02:48:36 by david
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

import os.path
from ConfigParser import NoOptionError, SafeConfigParser as ConfigParser

import log
from config import get_config, ConfigSection, path

class PasswordDatabase(object):
    backend_id = ''
    backends = {}
    backend = None

    @classmethod
    def register_backend(cls):
        if not cls.backend_id:
            raise AttributeError('Backend error:'
                    ' missing attribute backend_id for %s', cls)
        if not cls.backends.has_key(cls.backend_id):
            cls.backends[cls.backend_id] = cls
        log.info("Registering backend %s" % cls.backend_id)

    def __call__(self):
        if self.backend is None:
            backend = get_config('sshproxy')['pwdb_backend']

            self.backend = self.backends[backend]()
        return self.backend

    def get_console(self):
        return None

get_backend = PasswordDatabase()


class UserEntry(object):
    def __init__(self, uid, password, primary=0):
        self.uid = uid
        self.password = password
        self.primary = primary

    def __repr__(self):
        return str({'uid': self.uid,
                    'password': '*'*len(self.password),
                    'primary': self.primary})

class SiteEntry(object):
    def __init__(self, sid, ip_address=None, port=22, location=None,
                       user_list=None):
        self.sid = sid
        self.ip_address = ip_address
        self.port = port
        self.location = location
        
        self.users = {}
        
        if user_list is None:
            return
        for user in user_list:
            self.users[user.uid] = user

    def default_user(self):
        for u in self.users.keys():
            if self.users[u].primary:
                return u
        return None

    def get_user(self, uid):
        if self.users.has_key(uid):
            return self.users[uid]
        else:
            return None

    def __repr__(self):
        return 'SiteEntry: %s %s:%s (%s) %s' % (self.sid,
                                                self.ip_address,
                                                self.port,
                                                self.location,
                                                repr(self.users))


class FileBackendConfig(ConfigSection):
    section_defaults = {
        'db_path': '@pwdb',
        }
    types = {
        'db_path': path,
    }

class FileBackend(PasswordDatabase):
    backend_id = 'file'

    def __init__(self):
        self.sites = {}
        self.login = None

        Config.register_handler('file', FileBackendConfig)
        self.db_path = get_config('file')['db_path']


    def get_console(self):
        return None


    def get_user_site(self, sid):
        user = None
        site = None
        if sid.find('@') >= 0:
            user, sid = sid.split('@')

        site_file = os.path.join(self.db_path, sid)
        if not os.path.exists(site_file):
            return None, None

        file = ConfigParser()
        file.read(site_file)

        site_section = file.defaults()
        if not len(site_section):
            print "No site section"
            return None, None

        ip_address = site_section['ip_address']
        port       = int(site_section['port'])
        location   = site_section['location']

        user_list = []
        for sect in file.sections():
            try:
                primary = file.getint(sect, 'primary')
            except NoOptionError:
                primary = 0
            user_list.append(UserEntry(
                    sect,
                    file.get(sect, 'password'),
                    primary))

        user_list.sort(cmp=lambda x,y: cmp(x.primary, y.primary), reverse=True)

        if not user:
            user = user_list[0].uid

        site = SiteEntry(sid=sid,
                         ip_address=ip_address,
                         port=port,
                         location=location,
                         user_list=user_list)
            
        return user, site


    def list_sites(self, domain=None):
        sites = []
        for sitename in os.listdir(self.db_path):
            if sitename[0] == '.':
                continue
            user, sdata = self.get_user_site(sitename)
            for uid in sdata.users.keys():
                sites.append({
                    'name': sdata.sid,
                    'ip': sdata.ip_address,
                    'port': sdata.port,
                    'location': sdata.location,
                    'uid': uid,
                    })
        return sites


    def list_allowed_sites(self, user=None, domain=None):
        return self.list_sites()


    def is_admin(self, user=None):
        return True


    def is_allowed(self, username, password=None, key=None):
        return True


    def can_connect(self, user, site):
        return True


FileBackend.register_backend()
