#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Nov 09, 10:47:14 by david
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

    def _set_password(self, line, prompt1=None, prompt2=None):
        prompt1 = prompt1 or "Enter the password: "
        prompt2 = prompt2 or "Confirm the password: "
        item = line.strip()
        if not item:
            print "This command accept at least 1 argument"
            return

        from getpass import getpass
        pass1, pass2 = "1", "2"
        while not pass1.strip() or pass1 != pass2:
            try:
                pass1 = getpass(prompt1)
            except EOFError:
                print
                pass
            try:
                pass2 = getpass(prompt2)
            except EOFError:
                print
                pass
        return item, pass1

    def do_set_client_password(self, line):
        try:
            client, password = self._set_password(line)
        except TypeError:
            return
        except KeyboardInterrupt:
            print "Aborted."
            return

        response = self.ipc.call("set_client_password", "%s password=%s" %
                                                (client, repr(password)))
        print response

    def do_set_site_password(self, line):
        try:
            site, password = self._set_password(line)
        except TypeError:
            return
        except KeyboardInterrupt:
            print "Aborted."
            return

        response = self.ipc.call("set_site_password", "%s password=%s" %
                                                (site, repr(password)))
        print response

    def emptyline(self):
        return

    def do_exit(self, arg):
        return True

    def do_EOF(self, arg):
        print 'EOF'
        return True

Console.register()


