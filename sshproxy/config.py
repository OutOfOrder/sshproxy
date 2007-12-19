#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Dec 19, 01:18:53 by david
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

from sshproxy import __version__, __version_info__

minimum_version = (0, 6)

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

    def get(self, option, default=None, raw=False):
        if self.has_key(option):
            if not raw:
                return self.types.get(option, str)(
                            self._parser.get(self._section, option))
            else:
                return self._parser.get(self._section, option)
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

    @classmethod
    def register(cls, force=False):
        Config.register_handler(cls.section_id, cls, force=force)

class Config(object):
    section_handlers = {}


    @classmethod
    def register_handler(cls, name, handler, force=False):
        if not force and cls.section_handlers.get(name):
            # if it happens, don't avoid it but be verbose unless force is True
            print 'Warning: duplicate registration of ConfigSection %s' % name
            raise ValueError
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
        except IOError:
            if os.environ.get('SSHPROXY_WIZARD', None):
                return
            print "Could not write configuration file: %s" % inifile
            print "Make sure %s is writable" % inifile
            print "If this is the first time you're running the program, try"
            print "the following command:"
            print 'sshproxy-setup'
            sys.exit(1)
        try:
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



def path(path):
    if path[0] == '@':
        path = os.path.join(inipath, path[1:])
    return path

class SSHproxyConfigSection(ConfigSection):
    section_id = 'sshproxy'
    section_defaults = {
        'port': 2242,
        'listen_on': '', # listen on all IPs, all interfaces
        'max_connections': 0, # default is unlimited
        'auto_add_key': 'no', # do not auto add key when connecting
        'cipher_type': 'blowfish', # see cipher.py for available values
        'logger_conf': '/usr/share/sshproxy/logger.conf',
        'log_dir': '@log', # defaults in %(inipath)s/log
        'plugin_dir': '/usr/lib/sshproxy',
        'plugin_list': 'ini_db',
        'client_db': 'ini_db', # ini_db or mysql_db
        'acl_db': 'ini_db', # ini_db or mysql_db
        'site_db': 'ini_db', # ini_db or mysql_db
        'pkey_id': 'sshproxy@penguin.fr', # public key id for generated keys
        'ipc_address': '127.0.0.1:2244', # IPC address
        }
    types = {
        'port': int,
        'max_connections': int,
        'log_dir': path,
        'plugin_dir': path,
        'logger_conf': path,
        }

SSHproxyConfigSection.register()

inipath = os.environ.get('SSHPROXY_CONFIG', '')
if not inipath:
    inipath = os.path.join(os.environ['HOME'], '.sshproxy')
inipath = os.path.join(os.getcwd(), inipath)
inifile = '%s/sshproxy.ini' % inipath
if not os.environ.has_key('SSHPROXY_WIZARD'):
    get_config = Config(inifile)

    # make sure we catch errors early
    cfg = get_config('sshproxy')

    if not cfg.has_key('version'):
        if cfg.has_key('pwdb_backend'):
            print ("This configuration file is not compatible with sshproxy-%s"
                                                        % __version__)
            print "Please move it away, and run sshproxy-setup"
            sys.exit(0)
        else:
            cfg['version'] = '.'.join([ str(v) for v in __version_info__[0:3] ])


    cfg_version = tuple([ int(v) for v in cfg['version'].split('.') ])

    if  cfg_version < minimum_version:
        print "Version mismatch for configuration file"
        print "Please run sshproxy-setup"
        sys.exit(0)




