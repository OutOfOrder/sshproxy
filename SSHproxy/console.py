#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 mai 30, 13:21:18 by david
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





class Console(cmd.Cmd):
    def __init__(self, ctrlfd, is_admin, stdin=None, stdout=None):
        self.ctrlfd = ctrlfd
        self.is_admin = is_admin
        cmd.Cmd.__init__(self, stdin=stdin, stdout=stdout)
        self.prompt = '\nsshproxy> '

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
    def _sites(self, group=None):
        from pwdb.manage import pwdb
        sites=[]
        user = self._whoami().strip()
        for site in pwdb.list_allowed_sites(user=user, group=group):
            sites.append((site['name'], site['uid'],
                          site['ip'], site['location']))
        sites.sort(lambda x, y: x[1] < y[1])
        sites.sort()
        return sites


    #############################################################
    # PUBLIC METHODS - COMMANDS
    #############################################################
    def do_db(self, arg):
        """access to the sshproxy database management console"""
        if not self.need_admin(): return
        from pwdb.manage import DBConsole
        DBConsole().cmdloop()
        
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
        from pwdb.manage import CommandLine
        arg = CommandLine(arg)
        group = None
        if len(arg) and arg[0] != '#':
            group = arg[0]
        sites = self._sites(group=group)
        if len(sites):
            name_width = max([ len(e[0]) for e in sites ])
            for name, uid, ip, location in sites:
                print '%s@%s [%s]' % (uid, name, location)
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


