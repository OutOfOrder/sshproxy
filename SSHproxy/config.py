#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 mai 30, 13:12:42 by david
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


# TODO: parse config file located at $HOME/.sshproxy/server/config

import os, os.path, sys
import imp


class Config(object):
    def __init__(self, service):
        self._dirname = os.path.join(os.environ['HOME'], '.sshproxy')
        self._filename = os.path.join(self._dirname, service+'.conf')
        if os.path.isfile(self._filename):
            fp = open(self._filename)
            # Ugly hack to make imp.load_source silent
            class Sssshh(object):
                def write(self, msg):
                    pass
            oldstdout = sys.stdout
            sys.stdout = Sssshh()
            # Why does imp.load_source bark out the filename ???
            module = imp.load_source(service,
                        'THIS/IS/TO/AVOID/CREATION/OF/A/C/FILE!!!', fp)
            sys.stdout = oldstdout
            # END Ugly hack to make imp.load_source silent
            fp.close()
            for var in dir(module):
                if var[0] == '_':
                    continue
                setattr(self, var, getattr(module, var))
        else:
            if not os.path.isdir(self._dirname):
                os.mkdir(self._dirname, 0700)
            self._write()

    def _write(self):
        fp = open(self._filename, "w")
        fp.write(repr(self))
        fp.close()
        
    def __repr__(self):
        # regenerate the config file
        return '\n'.join([ '%s = %s' % (o, repr(getattr(self, o))) \
                            for o in dir(self) if o[0] != '_' ])+'\n'
        

class SSHproxyConfig(Config):
    def __init__(self):
        # set default values
        self.port = 2242
        self.bindip = ''
        
        # read file values
        Config.__init__(self, 'sshproxy')
        
        # readjust values
        try:
            self.port = int(self.port)
        except:
            print "Warning: port %s is not numeric. Using default." % self.port
            self.port = 2242

class MySQLConfig(Config):
    def __init__(self):
        # set default values
        self.host = 'localhost'
        self.user = 'sshproxy'
        self.password = 'sshproxypw'
        self.db = 'sshproxy'
        self.port = 3306
        
        # read file values
        Config.__init__(self, 'mysql')
        
        # readjust values
        try:
            self.port = int(self.port)
        except:
            print "Warning: port %s is not numeric. Using default." % self.port
            self.port = 3306
        

