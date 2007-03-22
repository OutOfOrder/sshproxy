#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Mar 22, 13:58:18 by david
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


import os, sys, select, pty

import ipc
import log

class PTYWrapper(object):
    def __init__(self, chan, code, address, handler, *args, **kwargs):
        self.chan = chan
        try:
            self.ipc = ipc.IPCServer(address, handler=handler)
        except:
            log.exception('Exception:')
            raise
        pid, self.master_fd = pty.fork()
        if not pid: # child process
            cipc = ipc.IPCClient(address)
            try:
                code(cipc, *args, **kwargs)
            except Exception, e:
                log.exception('ERROR: cannot execute function %s' %
                                                            code.__name__)
                pass
            cipc.terminate()
            cipc.close()
            sys.stdout.close()
            chan.transport.atfork() # close only the socket
            # Here the child process exits

        # Let's wait for the client to connect
        r, w, e = select.select([self.ipc], [], [], 5)
        if not r:
            self.ipc.terminate()
            self.ipc.close()
        else:
            self.ipc.accept()

    def loop(self):
        chan = self.chan
        master_fd = self.master_fd
        while master_fd and chan.active:
            # FIXME: What exception do we catch here ?
            # """try prevents rfds to return -1 and an error""" ????
            try:
                rfds, wfds, xfds = select.select(
                        [master_fd, chan], [], [], 5)
            except:
                break
            
            if master_fd in rfds:
                try:
                    data = pty._read(master_fd)
                except OSError:
                    break
                if data == '':
                    break
                #print 'from console:', repr(data)
                chan.send(data)
            if chan in rfds:
                data = chan.recv(10240)
                if data == '':
                    break
                pty._writen(master_fd, data)
                if chan.closed or chan.eof_received:
                    break 

