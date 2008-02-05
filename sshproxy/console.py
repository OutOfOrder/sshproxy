#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
#
# Last modified: 2008 Feb 06, 00:52:57 by david
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
from sshproxy.util import utf8

def rwinput(prompt):
    while 1:
        try:
            return utf8(raw_input(prompt))
        except KeyboardInterrupt:
            print
            continue
        break

# patch cmd.raw_input to be able to do CTRL-C without exiting
# and convert everything to utf8
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
                print _(u'Unknown command %s') % arg
            else:
                print _(self.methods.get(arg)) or _u('No help available')
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
            if prompt2 == -1:
                pass2 = pass1
                continue
            try:
                pass2 = getpass(prompt2)
            except EOFError:
                print
        return item, utf8(pass1)

    def do_set_client_password(self, line):
        try:
            client, password = self._set_password(line)
        except TypeError:
            return
        except KeyboardInterrupt:
            print "Aborted."
            return

        response = self.ipc.call("set_client_password", "%s password=%s" %
                                                (client, password))
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
                                                (site, password))
        print response

    def do_set_site_privkey(self, line):
        prompt1 = "Enter the private key (end with CTRL-D): "
        prompt2 = -1 #"Confirm the private key (end with CTRL-D): "

        import getpass
        _ri = getpass._raw_input

        def _raw_input(prompt="", stream=None):
            import sys, termios
            import log

            prompt = str(prompt)
            # A raw_input() replacement that doesn't save the string in the
            # GNU readline history.
            ifd = sys.stdin.fileno()
            ofd = sys.stdout.fileno()

            old = termios.tcgetattr(ifd)     # a copy to save
            new = old[:]
    
            new[3] = new[3] & ~termios.ICANON # 3 == 'lflags'
            try:
                try:
                    termios.tcsetattr(ifd, termios.TCSANOW, new)
                    if prompt:
                        sys.stdout.write(prompt)
                        sys.stdout.flush()
                    lines = []
                    while True:
                        c = sys.stdin.read(1)
                        if not c or c in ('\000', '\004'): # CTRL-D
                            break
                        lines.append(c)
                        if c not in ' \t\r\n':
                            c = '*'
                        sys.stdout.write(c)
                    return ''.join(lines)

                finally:
                    termios.tcsetattr(ifd, termios.TCSADRAIN, old)
            except KeyboardInterrupt:
                raise
            except:
                log.exception("_raw_input")
                raise

        getpass._raw_input = _raw_input

        try:
            try:
                site, privkey = self._set_password(line, prompt1, prompt2)
            finally:
                getpass._raw_input = _ri
        except TypeError:
            return
        except KeyboardInterrupt:
            print "Aborted."
            return

        privkey = '"%s"' % privkey.replace('\n', r'\\n')

        response = self.ipc.call("set_site_privkey", "%s privkey=%s" %
                                                (site, privkey))
        print response

    def emptyline(self):
        return

    def do_exit(self, arg):
        return True

    def do_EOF(self, arg):
        print 'EOF'
        return True

Console.register()


