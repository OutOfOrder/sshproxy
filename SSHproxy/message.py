#!/usr/bin/python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005 David Guerizec <david@guerizec.net>
#
# Last modified:
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
import os, select

class Pipe(object):
    def __init__(self, r, w):
        self.rfd = r
        self.wfd = w
        self.timeout = 0.0

    def close(self):
        os.close(self.rfd)
        os.close(self.wfd)

    def read(self, sz=1024):
        if self.timeout == 0.0:
            return os.read(self.rfd, sz)
        elif self.timeout is None:
            while 1:
                r, w, e = select.select([self.rfd], [], [], 5)
                if self.rfd in r:
                    return os.read(self.rfd, sz)
        else:
            r, w, e = select.select([self.rfd], [], [], self.timeout)
            return os.read(self.rfd, sz)

    def write(self, str):
        return os.write(self.wfd, str)

    def fileno(self):
        # fileno is useful for select
        # which is mainly for a read operation
        return self.rfd

    def setblocking(self):
        self.settimeout(None)

    def setnonblocking(self):
        self.settimeout(0.0)

    def settimeout(self, timeout):
        self.timeout = timeout

class Message(object):
    def __init__(self):
        r1, w2 = os.pipe()
        r2, w1 = os.pipe()
        self.parent = Pipe(r1, w1)
        self.child = Pipe(r2, w2)

    def get_parent_fd(self):
        # call this method after a fork when pid != 0
        #self.child.close()
        return self.parent

    def get_child_fd(self):
        # call this method after a fork when pid == 0
        #self.parent.close()
        return self.child
    

