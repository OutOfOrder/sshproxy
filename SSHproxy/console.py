#!/usr/bin/python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 jan 16, 18:29:45 by david
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307  USA


# Imports from Python
from cmd import Cmd

class Console(Cmd):
    def __init__(self, sitedata, stdin=None, stdout=None):
        self.sitedata = sitedata
        Cmd.__init__(self, stdin=stdin, stdout=stdout)

    def do_foo(self, arg):
        self.stdout.write("foo(%s)\n" % arg)

    def do_manage_pwdb(self, arg):
        from pwdb.manage import DBConsole
        DBConsole().cmdloop()
        
    def do_EOF(self, arg):
        return True
