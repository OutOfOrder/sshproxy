#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 mai 30, 17:55:59 by david
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


import os, select, pty

import log

class PTYWrapper(object):
    def __init__(self, chan, code, msg, *args, **kwargs):
        self.chan = chan
        self.cin = msg.get_parent_fd()
        pid, self.master_fd = pty.fork()
        if not pid: # child process
            cout = msg.get_child_fd()
            try:
                code(cout, *args, **kwargs)
            except Exception, e:
                log.exception('ERROR: cannot execute function %s' %
                                                            code.__name__)
                pass
            cout.write('EOF')
            cout.close()
            chan.transport.atfork() # close only the socket
            # Here the child process exits

    def loop(self):
        chan = self.chan
        master_fd = self.master_fd
        cin = self.cin
        while master_fd and chan.active:
            # FIXME: What exception do we catch here ?
            # """try prevents rfds to return -1 and an error""" ????
            try:
                rfds, wfds, xfds = select.select(
                        [master_fd, chan, cin], [], [], 5)
            except:
                break
            
            if master_fd in rfds:
                try:
                    data = pty._read(master_fd)
                except OSError:
                    break
                chan.send(data)
            if chan in rfds:
                # read a large buffer until the protocol is more robust
                data = chan.recv(10240)
                if chan.closed or chan.eof_received:
                    break 
                if data == '':
                    break
                pty._writen(master_fd, data)
            if cin in rfds:
                # read a large buffer until the protocol is more robust
                data = cin.read(10240)
                # since this is a pipe, it seems to always return EOF ('')
                if not len(data):
                    continue
                if data == 'EOF':
                    cin.close() # stop the loop
                    return None
                return data


