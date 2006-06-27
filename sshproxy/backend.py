#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jun 26, 23:26:39 by david
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
from config import get_config, Config, ConfigSection, path

class PasswordDatabase(object):
    backend_id = ''
    backends = {}
    backend = None

    @classmethod
    def register_backend(cls):
        if not cls.backend_id:
            raise AttributeError('Backend error:'
                    ' missing attribute backend_id for %s', cls)
        if not PasswordDatabase.backends.has_key(cls.backend_id):
            PasswordDatabase.backends[cls.backend_id] = cls
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
    def __init__(self, uid, password, pkey='', priority=0):
        self.uid = uid
        self.password = password
        self.pkey = pkey
        self.priority = priority

    def __repr__(self):
        return str({'uid': self.uid,
                    'password': '*'*len(self.password),
                    'pkey': ['no', 'yes'][bool(self.pkey)],
                    'priority': self.priority})

class SiteEntry(object):
    def __init__(self, sid, ip_address=None, port=22, location=None,
                       rlogin_list=None):
        self.sid = sid
        self.ip_address = ip_address
        self.port = port
        self.location = location
        
        self.rlogins = {}
        
        if rlogin_list is None:
            return
        for rlogin in rlogin_list:
            self.rlogins[rlogin.uid] = rlogin

    def default_rlogin(self):
        for u in self.rlogins.keys():
            if self.rlogins[u].priority:
                return u
        return None

    def get_rlogin(self, uid):
        if self.rlogins.has_key(uid):
            return self.rlogins[uid]
        else:
            return None

    def __repr__(self):
        return 'SiteEntry: %s %s:%s (%s) %s' % (self.sid,
                                                self.ip_address,
                                                self.port,
                                                self.location,
                                                repr(self.rlogins))


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

    def get_wizard(self):
        # XXX: put this in the wizard when available
        if not os.path.isdir(self.db_path):
            os.mkdir(self.db_path)

    def get_rlogin_site(self, sid):
        rlogin = None
        site = None
        if sid.find('@') >= 0:
            rlogin, sid = sid.split('@')

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

        rlogin_list = []
        for sect in file.sections():
            try:
                priority = file.getint(sect, 'priority')
            except NoOptionError:
                priority = 0
            rlogin_list.append(UserEntry(
                    uid=sect,
                    password=file.get(sect, 'password'),
                    pkey=file.get(sect, 'pkey'),
                    priority=priority))

        rlogin_list.sort(cmp=lambda x,y: cmp(x.priority, y.priority),
                                                    reverse=True)

        if not rlogin:
            rlogin = rlogin_list[0].uid

        site = SiteEntry(sid=sid,
                         ip_address=ip_address,
                         port=port,
                         location=location,
                         rlogin_list=rlogin_list)
            
        return rlogin, site


    def list_sites(self, domain=None):
        sites = []
        for sitename in os.listdir(self.db_path):
            if sitename[0] == '.':
                continue
            rlogin, sdata = self.get_rlogin_site(sitename)
            for uid in sdata.rlogins.keys():
                sites.append({
                    'name': sdata.sid,
                    'ip': sdata.ip_address,
                    'port': sdata.port,
                    'location': sdata.location,
                    'uid': uid,
                    })
        return sites


    def list_allowed_sites(self, domain=None, login=None):
        return self.list_sites(domain)


    def is_admin(self, login=None):
        return True


    def is_allowed(self, username, password=None, key=None):
        return True


    def can_connect(self, rlogin, site):
        return True

    def set_rlogin_password(self, rlogin, site, password):
        site_file = os.path.join(self.db_path, site)
        if not os.path.exists(site_file):
            return None, None

        file = ConfigParser()
        file.read(site_file)

        if not file.has_section(rlogin):
            return False

        file.set(rlogin, 'password', password)

        file.write(open(site_file, 'w'))
        return True



FileBackend.register_backend()
