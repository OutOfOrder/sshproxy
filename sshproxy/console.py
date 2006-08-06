#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Aug 07, 01:01:37 by david
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

    def __reginit__(self, msg, stdin=None, stdout=None):
        self.msg = msg
        self.populate()
        cmd.Cmd.__init__(self, stdin=stdin, stdout=stdout)
        self.prompt = 'sshproxy> '

    def populate(self):
        methods = self.msg.request('public_methods').split('\n')
        self.methods = {}
        for line in methods:
            method, help = line.split(' ', 1)
            self.methods[method] = help.replace('\\n','\n')

    def completenames(self, text, *ignored):
        return [ a for a in self.methods.keys() if a.startswith(text) ]

    def do_help(self, arg):
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
        print self.msg.request(line)

    def emptyline(self):
        return

Console.register()


