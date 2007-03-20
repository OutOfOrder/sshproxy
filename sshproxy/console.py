#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Jan 21, 03:24:18 by david
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


import cmd, os, socket

from sshproxy.registry import Registry

def rwinput(prompt):
    while 1:
        try:
            return raw_input(prompt)
        except KeyboardInterrupt:
            print
            continue
        break

# patch cmd.raw_input to be able to do CTRL-C without exiting
cmd.raw_input = rwinput


class Console(Registry, cmd.Cmd):
    _class_id = 'Console'

    def __reginit__(self, ipc, stdin=None, stdout=None):
        self.ipc = ipc
        self.populate()
        cmd.Cmd.__init__(self, stdin=stdin, stdout=stdout)
        self.prompt = 'sshproxy> '

    def populate(self):
        methods = self.ipc.call('public_methods')
        self.methods = {}
        for method, help in methods:
            self.methods[method] = help #.replace('\\n','\n')

    def completenames(self, text, *ignored):
        return [ a for a in self.methods.keys() if a.startswith(text) ]

    def do_help(self, arg):
        self.populate()
        if arg:
            if arg not in self.methods.keys():
                print 'Unknown command %s' % arg
            else:
                print self.methods.get(arg) or 'No help available'
            return
        
        commands = self.methods.keys()
        commands.sort()
        self.print_topics(self.doc_header, commands, 15, 80)


    def default(self, line):
        try:
            cmd, args = line.split(' ', 1)
        except ValueError:
            cmd, args = line, ''
        response = self.ipc.call(cmd, args)
        if response is not None:
            print response

    def emptyline(self):
        return

    def do_exit(self, arg):
        return True

    def do_EOF(self, arg):
        print 'EOF'
        return True

Console.register()


