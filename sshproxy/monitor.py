#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Mar 20, 18:42:13 by david
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


import os, signal, time
import marshal

from registry import Registry
from config import get_config
import log 
import ipc
from acl import ACLDB, ProxyNamespace
from backend import Backend

class Monitor(Registry, ipc.IPCInterface):
    _class_id = "Monitor"
    _singleton = True

    def __reginit__(self, input_message_queue):
        self.children = {}
        self.fds = {}
        self.imq = input_message_queue
        self.ipc = ipc.IPCServer(get_config('sshproxy').get('ipc_address',
                                    ('127.0.0.1', 2244)), handler=self)
        self.imq.append(self.ipc)
        self.chans = []
        self.namespaces = {}

    
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, chan):
        ipc.IPCInterface.__init__(self, chan)
        return self

    def clean_at_fork(self):
        for chan in self.chans:
            if chan and chan.channel:
                chan.channel.close()

    def add_child(self, pid, chan, ip_addr):
        self.children[pid] = {'ipc': chan, 'ip_addr': ip_addr}
        self.fds[ipc] = pid
    #    self.imq.append(ipc)

    def default_call_handler(self, _name, _chan, *args, **kw):
        func = getattr(self, 'rq_' + _name, None)
        if not func:
            return 'monitor.%s does not exist' % _name
        return func(_chan, *args, **kw)

    def children_count(self):
        return len(self.children)

    def find_child_pid(self, fd):
        return self.fds.get(fd, None)

    def kill_children(self, sig=signal.SIGHUP):
        for pid in self.children.keys():
            self.kill_child(pid, sig)

    def kill_child(self, pid, sig=signal.SIGHUP):
        try:
            os.kill(pid, sig)
            return True
        except OSError:
            log.warning('ERROR: child pid %s does not exist', pid)
        return False

    def kill_zombies(self, signum=None, frame=None):
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
            if pid and pid in self.children:
                ipc = self.children[pid]['ipc']
                imqfd = self.imq.index(ipc)
                self.imq[imqfd].close()
                del self.imq[imqfd]
                del self.children[pid]
                del self.fds[ipc]
                log.info("A child process has been killed and cleaned.")
        except OSError:
            pass

    def connect(self, chan):
        pass

    def disconnect(self, chan):
        chan = self.chans.pop(self.chans.index(chan))

    def handle_incomming_connection(self, fd):
        chan = self.ipc.accept()
        self.chans.append(chan)

    def func_update_client(self, _chan, value):
        #self.children[pid].update(value)
        self.namespaces.get('proxy', {}).update(value)
        pass

    def func_public_methods(self, _chan, *args, **kw): # public_methods
        methods = []
        for method in dir(self):
            if method[:3] != 'rq_':
                continue
            doc = getattr(getattr(self, method), '__doc__', None)
            if not doc:
                continue
            methods.append((method[3:], doc))

        return methods

    def func_check_acl(self, _chan, *args, **kw):
        print "monitor.py:Monitor.func_check_acl(_chan=%s, *args=%s, **kw=%s):: ATTENTION!!!!!!" % (repr(_chan), repr(args), repr(kw))
        return True

    def func_authenticate(self, _chan, *args, **kw):
        if not Backend().authenticate(username=kw['username'],
                                        auth_tokens=kw,
                                        ip_addr=kw['ip_addr']):
            return False
        else:
            if not self.namespaces.has_key(_chan):
                self.namespaces[_chan] = {}
            self.namespaces[_chan]['client'] = Backend().get_client_tags()
            return True

    def func_authorize(self, _chan, *args, **kw):
        if not Backend().authorize(user_site=kw['user_site'],
                                   need_login=kw.get('need_login')):
            return False
        else:
            self.namespaces[_chan]['site'] = Backend().get_site_tags()
            return True

    def func_get_namespace(self, _chan, *args, **kw):
        ns = self.namespaces.get(_chan, {})
        ns.update({'proxy':ProxyNamespace()})
        return ns
    




    #######################################################################
    ###  Public methods
    #######################################################################

    #def rq_shutdown(self, id, *args):
    #    """Shutdown all active connections"""
    #    msg = ("The administrator has requested a shutdown.\n"
    #            "Your session will be closed.")
    #    for pid, child in self.children.items():
    #        if pid == id:
    #            continue
    #        self.send_message(pid, 'kill', msg)
    #    time.sleep(2)
    #    for pid, child in self.children.items():
    #        if pid == id:
    #            continue
    #        self.kill_child(pid)

    def rq_nb_con(self, id, *args):
        """
        Get number of currently active client connections.
        """
        return '%d %d' % (len(self.children.keys()), len(self.chans))


    def rq_watch(self, id, *args):
        """
        Display connected users.
        """
        r = []
        for chan in self.chans:
            r.append(repr(chan.channel.getpeername()))
        return '\n'.join(r)
    #    s = []
    #    for pid, child in self.children.items():
    #        # don't show ourself
    #        if pid == id:
    #            continue
    #        if 'name' in child:
    #            s.append('% 6d %s@%s ---(%s)--> %s@%s' %
    #                        (pid, child['username'], str(child['ip_addr'][0]),
    #                        child['type'],
    #                        child['login'], child['name']))
    #        else:
    #            s.append('%s@%s -->(%s)' %
    #                            (child['username'], str(child['ip_addr'][0]),
    #                            child['type']))
    #    return '\n'.join(s)

    #def rq_message(self, id, *args):
    #    """
    #    message user@site <message contents>

    #    Send a message to user@site.
    #    """
    #    if len(args) < 3:
    #        return 'Need a message'
    #    for pid, child in self.children.items():
    #        cid = '%s@%s' % (child['username'], child['ip_addr'][0])

    #        if args[1] == '*' or args[1] == cid:
    #            msg = ("\007On administrative request, "
    #                   "your session will be closed.")
    #            if len(args) > 2:
    #                msg = ' '.join(args[2:])
    #            self.send_message(pid, 'announce', msg)
    #            #return '%s found and signaled' % cid
    #        #return "%s couldn't be signaled" % cid
    #    return '%s not found' % (args[1])

    def rq_kill(self, id, *args):
        """
        kill user@site

        Kill all connections to user@site.
        """
        count = 0
        for pid, child in self.children.items():
            # don't kill ourself
            if pid == id:
                continue
            if 'username' in child:
                username = child['username']
            else:
                username = '_'
            cid = '%s@%s' % (username, child['ip_addr'][0])
            if 'name' in child:
                sid = '%s@%s' % (child['login'], child['name'])
            else:
                sid = None
            if args[1] in ('*', cid, sid):
                msg = ("\007On administrative request, "
                       "your session will be closed.")
                if len(args) > 2:
                    msg = ' '.join(args[2:])
                self.send_message(pid, 'kill', msg)
                count += 1
        if count:
            return '%d killed connections' % count
        else:
            return '%s not found' % (args[1])


Monitor.register()
