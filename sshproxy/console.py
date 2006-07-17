#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 17, 01:55:50 by david
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


# XXX: Remove the following obsolete dead code after recycling

class ObsoleteConsole(cmd.Cmd):

    def need_admin(self):
        if not self.is_admin:
            print "ERROR: unsufficient rights!"
            return False
        return True

    def _whoami(self):
        self.ctrlfd.write('whoami')
        self.ctrlfd.setblocking()
        out = self.ctrlfd.read(4096)
        return out

    def emptyline(self):
        return

    #needed for do_show_sites
    # TODO: put this in daemon.py when the ctrlfd protocol is more robust
    def _sites(self):
        from backend import get_backend
        pwdb = get_backend()
        sites=[]
        login = self._whoami().strip()
        for site in pwdb.list_allowed_sites():
            sites.append([site.login, site.name, site.get_tags().priority])
        return sites


    #############################################################
    # PUBLIC METHODS - COMMANDS
    #############################################################
    def do_EOF(self, arg):
        """exit the console if there are no open connections left"""
        return self.do_exit(arg)

    def do_exit(self, arg):
        """exit the console if there are no open connections left"""
        self.ctrlfd.write('exit_verify')
        self.ctrlfd.setblocking()
        err = self.ctrlfd.read(4096)
        if err:
            print err
        else:
            return True

    def do_list_connections(self, arg):
        """list_connections"""
        self.ctrlfd.write('list_conn')
        self.ctrlfd.setblocking()
        err = self.ctrlfd.read(4096)
        print err

    def do_sites(self, arg):
        """sites"""
        from util import CommandLine
        arg = CommandLine(arg)
        sites = self._sites()
        if len(sites):
            name_width = max([ len(e[0]) + len(e[1]) for e in sites ])
            for uid, name, priority in sites:
                priority = priority or '0'
                sid = '%s@%s' % (uid, name)
                print sid, ' '*(name_width + 1 - len(sid)), '[%s]' % priority
        print '\nTOTAL: %d ' % len(sites)

    def do_open(self, arg):
        """open [site]"""
        self.ctrlfd.write('open '+arg)
        self.ctrlfd.setblocking()
        err = self.ctrlfd.read()
        if err != 'OK':
            print err
        return

    def do_switch(self, arg):
        """switch [id]"""
        self.ctrlfd.write('switch '+arg)
        self.ctrlfd.setblocking()
        err = self.ctrlfd.read()
        if err != 'OK':
            print err
        
    def do_close(self, arg):
        """close [id]"""
        self.ctrlfd.write('close '+arg)
        self.ctrlfd.setblocking()
        err = self.ctrlfd.read()
        if err != 'OK':
            print err

    def do_whoami(self, arg):
        """identify me"""
        print self._whoami()

############################################################################
    def do_admin(self, arg):
        print self.ctrlfd.request('admin %s' % arg)

    def set_password(self, user):
        import termios, getpass
        pass1 = ""
        pass2 = " "
        print 'Setting password for user %s' % user
        try:
            while (pass1 != pass2):
                pass1 = getpass.getpass("Enter new password: ")
                pass2 = getpass.getpass("Confirm password: ")
            if pass1 == '':
                raise termios.error
        except EOFError:
            print 'Abort'
            return
        except termios.error:
            print 'Warning: Could not set password, setting random password:'
            import string, random
            pass1 = [ random.choice(string.ascii_letters + string.digits)
                                                        for x in range(8) ]
            pass1 = ''.join(pass1)
            print pass1
        return pass1

    def do_list_clients(self, arg):
        print self.ctrlfd.request('list_clients %s' % arg)

    def do_add_client(self, arg):
        if not arg:
            print "Missing username argument"
            return
        password = self.set_password(arg)
        print self.ctrlfd.request('add_client %s password="%s"' %
                                        (arg, password.replace('"', '\\"')))

    def do_del_client(self, arg):
        if not arg:
            print "Missing username argument"
            return
        print self.ctrlfd.request('del_client %s' % arg)

    def do_tag_client(self, arg):
        if not arg:
            print "Missing username argument"
            return
        print self.ctrlfd.request('tag_client %s' % arg)

    def do_tag_site(self, arg):
        if not arg:
            print "Missing sitename argument"
            return
        print self.ctrlfd.request('tag_site %s' % arg)

    def do_list_sites(self, arg):
        result = self.ctrlfd.request('list_sites %s' % arg)
        print result


    def _sites(self):
        from backend import get_backend
        pwdb = get_backend()
        sites=[]
        login = self._whoami().strip()
        for site in pwdb.list_allowed_sites():
            sites.append([site.login, site.name, site.get_tags().priority])
        return sites

    def do_sites(self, arg):
        """sites"""
        from util import CommandLine
        arg = CommandLine(arg)
        sites = self._sites()
        if len(sites):
            name_width = max([ len(e[0]) + len(e[1]) for e in sites ])
            for uid, name, priority in sites:
                priority = priority or '0'
                sid = '%s@%s' % (uid, name)
                print sid, ' '*(name_width + 1 - len(sid)), '[%s]' % priority
        print '\nTOTAL: %d ' % len(sites)

