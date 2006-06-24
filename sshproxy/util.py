#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jun 24, 23:51:22 by david
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

import pwd

import log


class SSHProxyError(Exception):
    def __init__(self, msg):
        log.error("PROXY: "+msg)
        Exception.__init__(self, msg)

class SSHProxyAuthError(SSHProxyError):
    def __init__(self, msg):
        log.error("AUTH: "+msg)
        Exception.__init__(self, "Authentication error: "+msg)

class SSHProxyPluginError(SSHProxyError):
    def __init__(self, msg):
        log.error("PLUG: "+msg)
        Exception.__init__(self, "Plugin error: "+msg)

def istrue(s):
    return s.lower().strip() in ('yes', 'true', 'on', '1')
        
class CommandLine(object):
    def __init__(self, args):
        if type(args) == type(''):
            self.args = self.decode(args)
        else:
            self.args = args

    def __len__(self):
        return len(self.args)

    def __getitem__(self, item):
        return self.args[item]

    def decode(self, args):
        l = [ e.strip() for e in args.split() ]
        l = [ e for e in l if e ]
        return l

    def encode(self, args=None):
        if not args:
            args = self.args
        return ' '.join(args)

SUSPEND, SWITCH, CLOSE = range(-4, -1)


def getgid(username): # Credits: TMDA
    """Return username's numerical group ID."""
    return pwd.getpwnam(username)[3]

def getgrouplist(username): # Credits: TMDA
    """Read through the group file and calculate the group access
    list for the specified user.  Return a list of group ids."""
    import grp
    # calculate the group access list
    gids = [ i[2] for i in grp.getgrall() if username in i[-1] ]
    # include the base gid
    gids.insert(0, getgid(username))
    return gids

def getuid(username): # Credits: TMDA
    """Return username's numerical user ID."""
    return pwd.getpwnam(username)[2]

def gethomedir(username): # Credits: TMDA
    """Return the home directory of username."""
    return pwd.getpwnam(username)[5]

