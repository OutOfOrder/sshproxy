#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jun 19, 00:15:03 by david
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


import os, os.path, sys
from ConfigParser import ConfigParser
from StringIO import StringIO


class ConfigSection(object):
    section_defaults = {}
    types = {}

    def __init__(self, config, section):
        self._config = config
        self._parser = config._parser
        self._section = section
        if not self._parser.has_section(section):
            self._parser.add_section(section)
            self._config.touch()
        self.init_section()

    def init_section(self):
        for k, v in self.section_defaults.items():
            value = self.get(k, None)
            if value is None:
                self.set(k, str(v))
                self._config.touch()
        self._config.write()

    def get_default(self, option, default=None):
        return self.section_defaults.get(option, default)

    def __getitem__(self, option):
        return self.types.get(option, str)(self._parser.get(self._section,
                                                            option))

    def __setitem__(self, option, value):
        self._config.touch()
        return self._parser.set(self._section, option, str(value))

    def __delitem__(self, option):
        self._config.touch()
        return self._parser.remove_option(self._section, option)

    def keys(self):
        return self._parser.options(self._section)

    def has_key(self, option):
        return self._parser.has_option(self._section, option)

    def get(self, option, default=None):
        if self.has_key(option):
            return self.types.get(option, str)(self._parser.get(self._section,
                                                                option))
        else:
            return default

    def set(self, option, value):
        self._config.touch()
        return self._parser.set(self._section, option, str(value))

    def pop(self, option):
        self._config.touch()
        return self.types.get(option, str)(self._parser.remove_option(
                                                    self._section, option))

    def items(self):
        return self._parser.items(self._section)

    def write(self):
        self._config.write()

    def __str__(self):
        return str(self._config)


class Config(object):
    section_handlers = {}


    @classmethod
    def register_handler(cls, name, handler):
        cls.section_handlers[name] = handler


    @classmethod
    def get_handler(cls, name):
        return cls.section_handlers.get(name, ConfigSection)


    def __init__(self, inifile):
        self._inifile = inifile
        self._parser = None
        self._sections = {}
        self._dirty = False
        self.check_mode()


    def check_mode(self):
        try:
            mode = os.stat(self._inifile)[0] & 0777
        except OSError:
            # file does not exist, this is ok
            return False

        if mode & 0177:
            print ("File mode %o for %s is not enough restrictive and is a "
                                "security threat." % (mode, self._inifile))
            print "Please chmod it to 600."
            sys.exit(1)

        return True


    def __call__(self, section=None):
        if not self._parser:
            from ConfigParser import SafeConfigParser as ConfigParser
            self._parser = ConfigParser()
            self._parser.read(self._inifile)

        if not section:
            return self
        else:
            return self[section]


    def __getitem__(self, section):
        if not self._sections.has_key(section):
            self._sections[section] = self.get_handler(section)(self, section)
        return self._sections[section]


    def __setitem__(self, section, options):
        if not self._parser.has_section(section):
            self._parser.add_section(section)
            self._sections[section] = self.get_handler(section)(self, section)
        sect = self._sections[section]

        for option in sect.keys():
            sect.pop(option)
        for option, value in options:
            sect[option] = value
        self.touch()


    def __delitem__(self, section):
        self.touch()
        return self._parser.remove_section(section)


    def pop(self, section):
        self.touch()
        return self._parser.remove_section(section)


    def keys(self):
        return self._parser.sections()


    def has_key(self, section):
        return self._parser.has_section(section)


    def defaults(self):
        return self._parser.defaults()


    def touch(self):
        self._dirty = True


    def write(self, inifile=None):
        if not self._dirty:
            return
        if inifile is None:
            inifile = self._inifile

        try:
            ini = open(inifile, 'w')
            #print 'writing', inifile
            return self._parser.write(ini)
        finally:
            self._dirty = False
            ini.close()
            os.chmod(self._inifile, 0600)


    def __str__(self):
        fp = StringIO()
        self._parser.write(fp)
        fp.seek(0L)
        return fp.read()



inipath = '%s/.sshproxy' % os.environ['HOME']
inifile = '%s/sshproxy.ini' % inipath
get_config = Config(inifile)



class SSHproxyConfigSection(ConfigSection):
    section_defaults = {
        'port': 2242,
        'bindip': '', # listen on all interfaces
        'max_connections': 0, # default is unlimited
        'auto_add_key': 'no', # do not auto add key when connecting
        'cipher_type': 'blowfish', # see cipher.py for available values
        'logger_conf': '/usr/share/sshproxy/logger.conf'
        'plugin_dir': '/usr/lib/sshproxy',
        'plugin_list': 'logusers mysqlbackend',
        'pwdb_backend': 'mysql', # file or mysql
        }
    types = {
        'port': int,
        'max_connections': int,
        }

Config.register_handler('sshproxy', SSHproxyConfigSection)
