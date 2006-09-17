#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Sep 17, 16:37:37 by david
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

        user = self.tags['client'].username
        path = os.path.join(self.logdir, user)
        if not os.path.isdir(path):
            os.makedirs(path)

        site = '%s@%s' % (self.tags['site'].login, self.tags['site'].name)
        logfile = os.path.join(path, site)
        self.log = open(logfile, 'a')

    def client_to_server(self, rx, tx, rfds, sz=4096):
        x = rx.recv(sz)
        self.log.write(self.translate(x))
        self.log.flush()
        return self.rx_tx(x, 'client', rx, tx, rfds, sz=4096)

    def __del__(self):
        self.log.close()
        ProxyShell.__del__(self)

    def translate(self, char):
        return self.tr_table.get(char, char)
        if self.tr_table.has_key(char):
            return self.tr_table[char]
        return char
        

