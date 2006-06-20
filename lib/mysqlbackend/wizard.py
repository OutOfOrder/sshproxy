#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jun 20, 02:24:48 by david
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

import getpass

from sshproxy.config import get_config

class Wizard(object):
    def __init__(self, mysql):
        self.mysql = mysql
        
        adminid="root"
        adminpw=""
        self.cfg = cfg = get_config('mysql')
        cfg['host'] = (raw_input("SSHproxy database hostname [%s]: "
                        % cfg['host']) or cfg['host'])
        cfg['port'] = (raw_input("SSHproxy database port [%s]: "
                        % cfg['port']) or cfg['port'])
        cfg['db'] = (raw_input("SSHproxy database name [%s]: "
                        % cfg['db']) or cfg['db'])
        cfg['user'] = (raw_input("SSHproxy database user [%s]: "
                        % cfg['user']) or cfg['user'])
        cfg['password'] = (raw_input("SSHproxy database password [%s]: "
                        % cfg['password']) or cfg['password'])


        self.create_database()

        self.create_dbuser()

        self.add_admin()

        self.add_first_site()
        cfg.write()

    def create_database(self):
        print 'create database'
        pass

    def create_dbuser(self):
        pass

    def add_admin(self):
        pass

    def add_first_site(self):
        pass


