#!/usr/bin/python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Mar 06, 17:25:55 by david
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
import os, select, pty, traceback

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
                log.exception('error executing function %s', code.__name__)
                pass
            cout.write('EOF')
            cout.close()
            os.abort() # squash me! (don't let me close paramiko channels)

    def loop(self):
        chan = self.chan
        master_fd = self.master_fd
        cin = self.cin
        while master_fd and chan.active:
            rfds, wfds, xfds = select.select(
                    [master_fd, chan, cin], [], [],5)
            if master_fd in rfds:
                try:
                    data = pty._read(master_fd)
                except OSError:
                    break
                chan.send(data)
            if chan in rfds:
                data = chan.recv(1024)
                if chan.closed or chan.eof_received:
                    break 
                if data == '':
                    break
                pty._writen(master_fd, data)
            if cin in rfds:
                data = cin.read(1024)
                # since this is a pipe, it seems to always return EOF ('')
                if not len(data):
                    continue
                if data == 'EOF':
                    cin.close() # stop the loop
                    return None
                return data


