#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Oct 29, 01:13:17 by david
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

from sshproxy import get_class
from sshproxy.config import get_config, ConfigSection, path
from sshproxy import keys
from sshproxy.proxy import ProxyShell
from sshproxy.backend import Backend

class LogUsersConfigSection(ConfigSection):
    section_id = 'logusers'
    section_defaults = {
        'logdir': '@logusers',
        }
    types = {
        'logdir': path,
        }

LogUsersConfigSection.register()


ProxyShell = get_class('ProxyShell')

class LoggedProxyShell(ProxyShell):
    tr_table = {}
    _tr_table = {
            '\r\n':         '\n',
            '\r':           '\n',
            '\n':           '\n',
            '<':            '<INF>',
            '>':            '<SUP>',
        }
    def __reginit__(self, *args, **kw):
        conf = get_config('logusers')
        if not os.path.isdir(conf['logdir']):
            os.makedirs(conf['logdir'])
        
        self.logdir = conf['logdir']

        # fill our translation table
        for key in dir(keys):
            if key[0] == '_' or not isinstance(getattr(keys, key), str):
                continue
            self.tr_table[getattr(keys, key)] = '<%s>' % key

        for key, value in self._tr_table.items():
            self.tr_table[key] = value

        ProxyShell.__reginit__(self, *args, **kw)

        user = Backend().get_client_tags().username
        path = os.path.join(self.logdir, user)
        if not os.path.isdir(path):
            os.makedirs(path)

        site_tags = Backend().get_site_tags()
        site = '%s@%s' % (site_tags.login, site_tags.name)
        logfile = os.path.join(path, site)
        self.log = open(logfile, 'a')

    def client_recv_data(self, source, name):
        data = ProxyShell.recv_data(self, source, name)
        #if name == 'client_chan':
        if True:
            for x in data:
                self.log.write(self.translate(x))
            self.log.flush()
        return data

    def copy_client(self, source, event, destination,
                                         recv_data=None, send_data=None):
        return self.copy(source, event, destination,
                recv_data=LoggedProxyShell.client_recv_data)

    def __del__(self):
        self.log.close()
        ProxyShell.__del__(self)

    def translate(self, char):
        return self.tr_table.get(char, char)
        

