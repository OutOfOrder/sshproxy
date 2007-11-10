#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Nov 10, 01:54:44 by david
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
from util import istrue
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
        self.imq[self.ipc] = self
        self.chans = []
        self.namespaces = {}
        self.backend = {}

    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, chan):
        ipc.IPCInterface.__init__(self, chan)
        return self

    def clean_at_fork(self):
        for chan in self.chans:
            if chan and chan.channel:
                chan.channel.close()
        self.ipc.sock.close()

    def add_child(self, pid, chan, ip_addr):
        self.children[pid] = {'ipc': chan, 'ip_addr': ip_addr}
        self.fds[chan] = pid

    def default_call_handler(self, _name, _chan, *args, **kw):
        func = getattr(self, 'rq_' + _name, None)
        if not func:
            try:
                raise AttributeError('Monitor.rq_%s does not exist' % _name)
            except AttributeError:
                log.exception('in Monitor.default_call_handler')
            return _(u'%s does not exist') % _name
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
            if pid and pid in self.children and pid != os.getpid():
                ipc = self.children[pid]['ipc']
                try:
                    del self.children[pid]
                    del self.fds[ipc]
                except KeyError:
                    log.exception("Monitor.kill_zombies():")
                    pass
                log.info("A child process has been killed and cleaned.")
        except OSError:
            pass

    def connect(self, chan):
        pass

    def disconnect(self, chan):
        chan = self.chans.pop(self.chans.index(chan))

    def handle_incoming_connection(self, fd):
        chan = self.ipc.accept()
        self.chans.append(chan)

    def func_update_ns(self, _chan, name, value):
        if _chan not in self.namespaces:
            self.namespaces[_chan] = {}
        if name not in self.namespaces[_chan]:
            self.namespaces[_chan][name] = {}
        self.namespaces[_chan][name].update(value)

    def func_get_ns_tag(self, _chan, namespace, tag, default=None):
        if _chan not in self.namespaces:
            return default
        if namespace not in self.namespaces[_chan]:
            return default
        if tag not in self.namespaces[_chan][namespace]:
            return default
        return self.namespaces[_chan][namespace][tag]

    def func_public_methods(self, _chan, *args, **kw): # public_methods
        methods = []
        for method in dir(self):
            if method[:3] != 'rq_':
                continue
            doc = getattr(getattr(self, method), '__doc__', None)
            if not doc:
                continue
            methods.append((method[3:], _(doc)))

        return methods

    def func_check_acl(self, _chan, *args, **kw):
        if not len(args):
            return False

        namespaces = self.namespaces[_chan]
        return ACLDB().check(acl=args[0], **namespaces)

    def func_authenticate(self, _chan, *args, **kw):
        backend = Backend()
        if not backend.authenticate(username=kw['username'],
                                        auth_tokens=kw,
                                        ip_addr=kw['ip_addr']):
            return False
        else:
            if not self.namespaces.has_key(_chan):
                self.namespaces[_chan] = {}
            if not self.backend.has_key(_chan):
                self.backend[_chan] = backend
            self.namespaces[_chan]['client'] = backend.get_client_tags()
            return True

    def func_authorize(self, _chan, *args, **kw):
        if not self.backend[_chan].authorize(user_site=kw['user_site'],
                                   need_login=kw.get('need_login')):
            return False
        else:
            self.namespaces[_chan]['site'] = self.backend[_chan].get_site_tags()
            return True

    def func_get_namespace(self, _chan, *args, **kw):
        ns = self.namespaces.get(_chan, {})
        ns.update({'proxy':ProxyNamespace()})
        return ns
    
    def func_reload_acl_rules(self, *args):
        ACLDB().reload_rules()
        
        return True
            
    def func_add_client_pubkey(self, _chan, pubkey):
        auto_add_key = get_config('sshproxy')['auto_add_key']

        if istrue(auto_add_key):
            return self.backend[_chan].add_client_pubkey(None,
                                                         pubkey, auto_add_key)

        return False




    #######################################################################
    ###  Public methods
    #######################################################################

    #def rq_shutdown(self, id, *args):
    #    u"""Shutdown all active connections"""
    #    msg = _(u"The administrator has requested a shutdown.\n"
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
        u"""
        Get number of currently active client connections.
        """
        return '%d %d' % (len(self.children.keys()), len(self.chans))

    def rq_reload_acl_rules(self, id, *args):
        u"""
        Reloads system ACLs database to cache
        """
        ACLDB().reload_rules()
        
        return _(u"ACL Rules reloaded.")

    def rq_watch(self, id, *args):
        u"""
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
    #    u"""
    #    message user@site <message contents>

    #    Send a message to user@site.
    #    """
    #    if len(args) < 3:
    #        return _(u'Need a message')
    #    for pid, child in self.children.items():
    #        cid = '%s@%s' % (child['username'], child['ip_addr'][0])

    #        if args[1] == '*' or args[1] == cid:
    #            msg = _(u"\007On administrative request, "
    #                   "your session will be closed.")
    #            if len(args) > 2:
    #                msg = ' '.join(args[2:])
    #            self.send_message(pid, 'announce', msg)
    #            #return '%s found and signaled' % cid
    #        #return "%s couldn't be signaled" % cid
    #    return _(u'%s not found') % (args[1])

    def rq_kill(self, id, *args):
        u"""
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
                msg = _(u"\007On administrative request, "
                       "your session will be closed.")
                if len(args) > 2:
                    msg = ' '.join(args[2:])
                self.send_message(pid, 'kill', msg)
                count += 1
        if count:
            return _(u'%d killed connections') % count
        else:
            return _(u'%s not found') % (args[1])


Monitor.register()
