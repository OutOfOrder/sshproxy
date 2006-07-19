#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 19, 02:48:05 by david
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

import shlex

from registry import Registry
import util, log, proxy, pool
from backend import Backend
from config import get_config
from message import Message
from ptywrap import PTYWrapper
from console import Console



###########################################################################

class Dispatcher(Registry):
    _class_id = 'Dispatcher'
    _singleton = True

    def __reginit__(self, daemon_msg):
        self.d_msg = daemon_msg
        self.d_msg.reset()
        self.daemon_methods = self.d_msg.request('public_methods').split()
        self.daemon_methods = {}
        for line in self.d_msg.request('public_methods').split('\n'):
            method, help = line.split(' ', 1)
            self.daemon_methods[method] = help.replace('\n', '\\n')

    def public_methods(self):
        methods = [ '%s %s' % (m, h) for m, h in self.daemon_methods.items() ]
        for method in dir(self):
            if method[:4] != 'cmd_':
                continue
            methods.append(' '.join(
                    [ method[4:],
                      getattr(getattr(self, method), '__doc__') or ''
                    ]))

        return '\n'.join([ m.replace('\n', '\\n') for m in methods ])

    def dispatch(self, cmdline):
        try:
            args = shlex.split(cmdline)
        except:
            return 'parse error'

        if args[0] == 'public_methods':
            return self.public_methods()

        command = 'cmd_' + args[0]

        if not hasattr(self, command):
            if args[0] in self.daemon_methods.keys():
                return self.d_msg.request(cmdline)
            else:
                return 'Unknown command %s' % args[0]

        func = getattr(self, command)

        return func(*args[1:])

    def init_console(self, conn=None):
        from server import Server
        c_msg = Message()

        def PtyConsole(*args, **kwargs):
            Console(*args, **kwargs).cmdloop()

        self._console = PTYWrapper(Server().chan, PtyConsole, msg=c_msg)

        self.c_msg = c_msg.get_parent_fd()

    def console(self, conn=None):
        #console = ConsoleBackend(conn)
        self.init_console(conn)

        while True:
            self.c_msg.reset()
        
            data = self._console.loop()
            if data is None:
                break

            response = self.dispatch(data)
            self.c_msg.response(response)


    def cmd_admin(self, *args):
        """
        admin command [args]

        Execute administrative commands on the main daemon.
        """
        return self.d_msg.request(' '.join(args))

    def cmd_list_clients(self, *args):
        tokens = {}
        for arg in args:
            t = arg.split('=', 1)
            if len(t) > 1:
                value = t[1]
                if value and value[0] == value[-1] == '"':
                    value = value[1:-1]

            tokens[t[0]] = value

        resp = Backend().list_clients(**tokens)
        resp.append('\nTotal: %d' % len(resp))
        return '\n'.join(resp)

    def cmd_add_client(self, *args):
        if Backend().client_exists(args[0]):
            return "Client %s does already exist." % args[0]

        tokens = {}
        for arg in args[1:]:
            t = arg.split('=', 1)
            if len(t) > 1:
                value = t[1]
                if value and value[0] == value[-1] == '"':
                    value = value[1:-1]
            else:
                return 'Parse error around <%s>' % arg

            if t[0] == 'password' and str(value).strip():
                import sha
                value = sha.new(value).hexdigest()
            tokens[t[0]] = value

        resp = Backend().add_client(args[0], **tokens)
        return resp

    def cmd_del_client(self, *args):
        if not Backend().client_exists(args[0]):
            return "Client %s does not exist." % args[0]

        tokens = {}
        for arg in args[1:]:
            t = arg.split('=', 1)
            if len(t) > 1:
                value = t[1]
                if value and value[0] == value[-1] == '"':
                    value = value[1:-1]
            else:
                return 'Parse error around <%s>' % arg

            tokens[t[0]] = value

        resp = Backend().del_client(args[0], **tokens)
        return resp

    def cmd_tag_client(self, *args):
        if not Backend().client_exists(args[0]):
            return "Client %s does not exist." % args[0]

        tokens = {}
        for arg in args[1:]:
            t = arg.split('=', 1)
            if len(t) > 1:
                value = t[1]
                if value and value[0] == value[-1] == '"':
                    value = value[1:-1]
            else:
                return 'Parse error around <%s>' % arg

            if t[0] == 'username':
                return "'username' is a read-only tag"
            else:
                if t[0] == 'password' and str(value).strip():
                    import sha
                    value = sha.new(value).hexdigest()
                tokens[t[0]] = value

            

        tags = Backend().tag_client(args[0], **tokens)
        resp = []
        for tag, value in tags.items():
            value = self.show_tag_filter('client', tag, value)
            resp.append('%s = "%s"' % (tag, value))
        return '\n'.join(resp)

##########################################################################

    def cmd_list_sites(self, *args):
        tokens = {}
        for arg in args:
            t = arg.split('=', 1)
            value = len(t) > 1 and t[1] or ''
            if value:
                if (value[0] == value[-1] == '"' or
                    value[0] == value[-1] == "'"):
                    value = value[1:-1]

            tokens[t[0]] = value

        sites = []
        for site in Backend().list_site_users(**tokens):
            sites.append([site.login or '', site.name,
                                            site.get_tags().priority])

        resp = []
        if len(sites):
            name_width = max([ len(e[0]) + len(e[1]) for e in sites ])
            for uid, name, priority in sites:
                priority = priority or '0'
                sid = '%s@%s' % (uid, name)
                resp.append('%s %s %s' % (sid, ' '*(name_width + 1 - len(sid)),
                                                            '[%s]' % priority))
        resp.append('\nTotal: %d' % len(resp))
        return '\n'.join(resp)

    def cmd_add_site(self, *args):
        if Backend().site_exists(args[0]):
            return "Site %s does already exist." % args[0]

        tokens = {}
        for arg in args[1:]:
            t = arg.split('=', 1)
            if len(t) > 1:
                value = t[1]
                if value and value[0] == value[-1] == '"':
                    value = value[1:-1]
            else:
                return 'Parse error around <%s>' % arg

            tokens[t[0]] = value

        resp = Backend().add_site(args[0], **tokens)
        return resp

    def cmd_del_site(self, *args):
        if not Backend().site_exists(args[0]):
            return "Site %s does not exist." % args[0]

        tokens = {}
        for arg in args[1:]:
            t = arg.split('=', 1)
            if len(t) > 1:
                value = t[1]
                if value and value[0] == value[-1] == '"':
                    value = value[1:-1]
            else:
                return 'Parse error around <%s>' % arg

            tokens[t[0]] = value

        resp = Backend().del_site(args[0], **tokens)
        return resp

    def cmd_tag_site(self, *args):
        if not Backend().site_exists(args[0]):
            return "Site %s does not exist." % args[0]

        tokens = {}
        for arg in args[1:]:
            t = arg.split('=', 1)
            if len(t) > 1:
                value = t[1]
                if value and value[0] == value[-1] == '"':
                    value = value[1:-1]
            else:
                return 'Parse error around <%s>' % arg

            if t[0] in ('name', 'login'):
                return "'%s' is a read-only tag" % t[0]
            else:
                tokens[t[0]] = value

            

        tags = Backend().tag_site(args[0], **tokens)
        if not hasattr(tags, 'items'):
            # this is an error message
            return tags
        resp = []
        for tag, value in tags.items():
            value = self.show_tag_filter('site', tag, value)
            resp.append('%s = "%s"' % (tag, value))
        return '\n'.join(resp)

    def show_tag_filter(self, object, tag, value):
        value = value or ''
        # XXX: test if the values are already crypted or mangled (crypto module)
        return value
        if object == 'client':
            if tag == 'password' and value:
                return '*'*len(value)
        elif object == 'site':
            if tag in ('password', '_pkey') and value:
                return ('*'*len(value))[:30]

        return value


Dispatcher.register()


# XXX: Remove the following obsolete dead code after recycling


class ObsoleteConsoleBackend(Registry):
    _class_id = "ConsoleBackend"
    def __reginit__(self, conn=None):
        conf = get_config('sshproxy')
        self.maxcon = conf['max_connections']

        from server import Server
        self.client = Server()
        self.chan = self.client.chan

        self.msg = Message()

        self.main_console = PTYWrapper(self.chan, self.PtyConsole, msg=self.msg)
        self.status = self.msg.get_parent_fd()

        self.cpool = pool.get_connection_pool()
        self.cid = None
        if conn is not None:
            self.cid = self.cpool.add_connection(conn)

    @staticmethod
    def PtyConsole(*args, **kwargs):
        Console(*args, **kwargs).cmdloop()


    def loop(self):
        while True:

            self.status.reset()
        
            data = self.main_console.loop()
            if data is None:
                break
            try:
                action, data = data.split(' ', 1)
            except ValueError:
                action = data.strip()
                data = ''

            method = 'cmd_'+action
            if hasattr(self, method):
                method = getattr(self, method)
                if callable(method):
                    response = method(data)
                    if response is None:
                        break
            # status.response() absolutely NEEDS to be called once an action
            # has been processed, otherwise you may experience hang ups.
                    self.status.response(response)
                    continue
            # if inexistant or no callable
            self.status.response('ERROR: Unknown action %s' % action)
            log.error('ERROR: Unknown action %s' % action)

        self.close()

    def cmd_open(self, args):
        if self.maxcon and len(self.cpool) >= self.maxcon:
            return 'ERROR: Max connection count reached'
        sitename = args.strip()
        if sitename == "":
            return 'ERROR: where to?'
        #try:
        #    sitename = self.client.set_remote(sitename)
        #except util.SSHProxyAuthError, msg:
        if not self.client.pwdb.authorize(sitename):
            log.error("ERROR(open): %s", msg)
            return ("ERROR: site does not exist or you don't "
                            "have sufficient rights")

        conn = proxy.ProxyShell(self.client)

        cid = self.cpool.add_connection(conn)
        while True:
            if not conn:
                ret = 'ERROR: no connection id %s' % cid
                break
            try:
                ret = conn.loop()
            except:
                self.chan.send("\r\n ERROR0: It seems you found a bug."
                               "\r\n Please report this error "
                               "to your administrator.\r\n\r\n")
                self.chan.close()
                raise
            if ret == util.CLOSE:
                self.cpool.del_connection(cid)
            elif ret >= 0:
                self.cid = cid = ret
                conn = self.cpool.get_connection(cid)
                continue
            ret = 'OK'
            break
        if not ret:
            ret = 'OK'
        return ret

    def cmd_switch(self, args):
        # switch between one connection to the other
        if not self.cpool:
            return 'ERROR: no opened connection.'
        args = args.strip()
        if args:
            cid = int(args)
        else:
            if self.cid is not None:
                cid = self.cid
            else:
                cid = 0
        while True:
            conn = self.cpool.get_connection(cid)
            if not conn:
                ret = 'ERROR: no id %d found' % cid
                break
            ret = conn.loop()
            if ret == util.CLOSE:
                self.cpool.del_connection(cid)
            elif ret >= 0:
                self.cid = cid = ret
                continue
            ret = 'OK'
            break
        return ret

    def cmd_close(self, args):
        # close connections
        args = args.strip()

        # there must exist open connections
        if self.cpool:
            # close all connections
            if args == 'all':
                l = len(self.cpool)
                while len(self.cpool):
                    self.cpool.del_connection(0)
                return '%d connections closed' % l
            # argument must be a digit
            elif args != "":
                if args.isdigit():
                    try:
                        cid = int(args)
                        self.cpool.del_connection(cid)
                        msg="connection %d closed" % cid
                    except UnboundLocalError:
                        msg = 'ERROR: unknown connection %s' % args
                    return msg
                else:
                    return 'ERROR: argument must be a digit'
            else:
                return 'ERROR: give an argument'
        else:
            return 'ERROR: no open connection'

    def cmd_list_conn(self, args):
        # show opened connections
        l = []
        i = 0
        # list the open connections
        for c in self.cpool.list_connections():
            l.append('%d %s\n' % (i, c.name))
            i = i + 1
        if not len(l):
            return 'ERROR: no opened connections'
        else:
            # send the connection list
            return ''.join(l)

    def cmd_whoami(self, args):
        # whoami command
        return '%s' % (self.client.username)

    def cmd_exit_verify(self, args):
        # check open connections for exit
        if self.cpool:
            return 'ERROR: close all connections first!'
        else:
            return None

    def cmd_sites(self, args):
        # dump the listing of all sites we're allowed to connect to
        # TODO: see console.py : Console._sites()
        return 'OK'

    def close(self):
        self.chan.close()
        log.info('Client exits now!')

#ConsoleBackend.register()
