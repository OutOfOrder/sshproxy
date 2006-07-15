#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 15, 23:10:26 by david
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


import os, select
from struct import pack, unpack

class Pipe(object):
    def __init__(self, r, w):
        self.rfd = r
        self.wfd = w
        self.timeout = 0.0
        self.reset()

    def close(self):
        os.close(self.rfd)
        os.close(self.wfd)

    def _read_size(self):
        S = os.read(self.rfd, 4)
        return unpack('I', S)[0]

    def _read_nonblocking(self):
        sz = self._read_size()
        S = os.read(self.rfd, sz)
        s = unpack('%ss' % sz, S)[0]
        if s == '___EMPTY_MESSAGE___':
            return ''
        return s

    def _read_blocking(self):
        while True:
            r, w, e = select.select([self.rfd], [], [], 5)
            if self.rfd in r:
                sz = self._read_size()
                break
        while True:
            r, w, e = select.select([self.rfd], [], [], 5)
            if self.rfd in r:
                S = os.read(self.rfd, sz)
                break
        s = unpack('%ss' % sz, S)[0]
        if s == '___EMPTY_MESSAGE___':
            return ''
        return s

    def _read_timeout(self):
        r, w, e = select.select([self.rfd], [], [], self.timeout)
        if self.rfd not in r:
            return None
        sz = self._read_size()
        r, w, e = select.select([self.rfd], [], [], self.timeout)
        if self.rfd not in r:
            return None
        S = os.read(self.rfd, sz)
        s = unpack('%ss' % sz, S)[0]
        if s == '___EMPTY_MESSAGE___':
            return ''
        return s

    def read(self, sz=10240):
        if self.timeout == 0.0:
            return self._read_nonblocking()
        elif self.timeout is None:
            return self._read_blocking()
        else:
            return self._read_timeout()

    def write(self, s):
        s = str(s)
        S = pack('I%ss' % len(s), len(s), s)
        return os.write(self.wfd, S)

    def response(self, s):
        if self._responded:
            raise Exception('Already responded, not reset')
        if not s:
            s = '___EMPTY_MESSAGE___'
        
        ret = self.write(s)
        self._responded = True
        return ret

    def request(self, request):
        self.write(request)
        return self._read_blocking()

    def reset(self):
        self._responded = False

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

    def flush(self):
        return
        #os.fdatasync(self.wfd)

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
    

