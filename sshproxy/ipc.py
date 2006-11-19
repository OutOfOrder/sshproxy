#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Nov 18, 12:53:06 by david
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
import marshal, socket

class IPChannel(object):
    def __init__(self, sock):
        self.sock = sock
        self.timeout = 0.0
        self.reset()

    def close(self):
        self.sock.close()

    def _read_size(self):
        S = self.sock.recv(4)
        if not S:
            return 0 # connection closed
        return unpack('I', S)[0]

    def _read_nonblocking(self):
        sz = self._read_size()
        S = self.sock.recv(sz)
        s = unpack('%ss' % sz, S)[0]
        return s

    def _read_blocking(self):
        while True:
            r, w, e = select.select([self.sock], [], [], 5)
            if self.sock in r:
                sz = self._read_size()
                break
        while True:
            r, w, e = select.select([self.sock], [], [], 5)
            if self.sock in r:
                S = self.sock.recv(sz)
                break
        s = unpack('%ss' % sz, S)[0]
        return s

    def _read_timeout(self):
        r, w, e = select.select([self.sock], [], [], self.timeout)
        if self.sock not in r:
            return None
        sz = self._read_size()
        r, w, e = select.select([self.sock], [], [], self.timeout)
        if self.sock not in r:
            return None
        S = self.sock.recv(sz)
        s = unpack('%ss' % sz, S)[0]
        return s

    def recv_message(self):
        sz = self._read_size()
        if not sz:
            return (0, None)
        s = self.sock.recv(sz)
        #if not s:
        #    return (0, )
        return marshal.loads(s)

    def send_message(self, s):
        #s = str(s)
        s = marshal.dumps(s)
        S = pack('I%ss' % len(s), len(s), s)
        return self.sock.send(S)

    def respond(self, s):
        if self._responded:
            raise Exception('Already responded, not reset')
        
        ret = self.send_message((0, s))
        self._responded = True
        return ret

    def request(self, request):
        self.send_message((1, request))
        w, s = self.recv_message()
        return s

    def info(self, info):
        self.send_message((0, info))

    def reset(self):
        self._responded = False

    def fileno(self):
        # fileno is useful for select
        # which is mainly for a read operation
        return self.sock.fileno()

    def setblocking(self):
        self.settimeout(None)

    def setnonblocking(self):
        self.settimeout(0.0)

    def settimeout(self, timeout):
        self.timeout = timeout

    def flush(self):
        return
        #os.fdatasync(self.wfd)



class IPC(object):
    count = 0
    def __init__(self):
        self.name = '\x00sshproxy-%d-%d\x00\xff' % (os.getpid(), self.count)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(self.name)
        IPC.count = (IPC.count + 1) & 0xFFFFFFFF
        self.sock.listen(1)
        self.child = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        return

    def get_parent_fd(self):
        # call this method after a fork when pid != 0
        self.child.close()
        self.parent, address = self.sock.accept()
        ipc = IPChannel(self.parent)
        self.sock.close()
        return ipc

    def get_child_fd(self):
        # call this method after a fork when pid == 0
        self.child.connect(self.name)
        self.sock.close()
        return IPChannel(self.child)
