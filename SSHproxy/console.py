#!/usr/bin/python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 jan 18, 15:59:15 by david
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
import cmd, os

def rwinput(prompt):
    while 1:
        try:
            return raw_input(prompt)
        except KeyboardInterrupt:
            print
            continue
        break

cmd.raw_input = rwinput

class Console(cmd.Cmd):
    def __init__(self, ctrlfd, stdin=None, stdout=None):
        self.ctrlfd = ctrlfd
        cmd.Cmd.__init__(self, stdin=stdin, stdout=stdout)
        self.prompt = '[ssh proxy] '

    def do_manage_pwdb(self, arg):
        from pwdb.manage import DBConsole
        DBConsole().cmdloop()
        
    def do_EOF(self, arg):
        return True

    def emptyline(self):
        return

    def do_connect(self, arg):
        self.ctrlfd.write('connect '+arg)
        self.ctrlfd.setblocking()
        err = self.ctrlfd.read()
        if err != 'OK':
            print err
        return

    def do_list_connections(self, arg):
        self.ctrlfd.write('list')
        self.ctrlfd.setblocking()
        err = self.ctrlfd.read(4096)
        print err

    def do_switch(self, arg):
        self.ctrlfd.write('switch '+arg)
        self.ctrlfd.setblocking()
        err = self.ctrlfd.read()
        if err != 'OK':
            print err
        
    def do_back(self, arg):
        self.ctrlfd.write('back')
        self.ctrlfd.setblocking()
        err = self.ctrlfd.read()
        if err != 'OK':
            print err

    def do_shell(self, arg):
        os.system('/bin/bash')

