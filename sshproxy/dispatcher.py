#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Sep 21, 02:20:11 by david
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
from acl import ACLDB
import cipher

###########################################################################
class DispatcherCommandError(Exception):
    pass

class Dispatcher(Registry):
    _class_id = 'Dispatcher'
    _singleton = True

    default_acl = True

    def __reginit__(self, daemon_msg, namespace):
        self.d_msg = daemon_msg
        self.d_msg.reset()
        self.namespace = namespace
        self.daemon_methods = {}
        for line in self.d_msg.request('public_methods').split('\n'):
            method, help = line.split(' ', 1)
            self.daemon_methods[method] = help.replace('\n', '\\n')

    def is_admin(self):
        return ACLDB().check('admin', **self.namespace)

    def public_methods(self):
        """
        Return a list of allowed commands.
        """
        if self.is_admin():
            methods = [ '%s %s' % (m, h)
                                for m, h in self.daemon_methods.items() ]
        else:
            methods = []
        for method in dir(self):
            if method[:4] != 'cmd_':
                continue
            if not self.check_acl(method[4:], None):
                continue
            doc = getattr(getattr(self, method), '__doc__', None)
            if not doc:
                continue
            methods.append(' '.join([ method[4:], doc ]))

        return '\n'.join([ m.replace('\n', '\\n') for m in methods ])

    def check_acl(self, *args):
        """
        Check the command's associated ACL rule, if defined.

        argv[0] is the command name, and argv[1:] contains the command's
        arguments.

        If len(args) == 2 and args[1] is None, public_methods is the caller.
        """
        acl = 'acl_' + args[0]
        if hasattr(self, acl):
            acl = getattr(self, acl)
            if isinstance(acl, str):
                acl = ACLDB().eval(acl, **self.namespace)

            return acl
        else:
            return self.default_acl

    def dispatch(self, cmdline):
        self.cmdline = cmdline
        try:
            args = shlex.split(cmdline)
        except:
            return 'parse error'

        if not len(args):
            return ''

        if args[0] == 'public_methods':
            return self.public_methods()

        command = 'cmd_' + args[0]

        if not hasattr(self, command):
            if args[0] in self.daemon_methods.keys() and self.is_admin():
                return self.d_msg.request(cmdline)
            else:
                return 'Unknown command %s' % args[0]

        if not self.check_acl(*args):
            return 'You have not enough rights to do this'

        func = getattr(self, command)

        try:
            return func(*args[1:])
        except DispatcherCommandError, msg:
            return msg

    def init_console(self):
        from server import Server
        c_msg = Message()

        def PtyConsole(*args, **kwargs):
            Console(*args, **kwargs).cmdloop()

        self._console = PTYWrapper(Server().chan, PtyConsole, msg=c_msg)

        self.c_msg = c_msg.get_parent_fd()

    def console(self):
        self.init_console()

        while True:
            self.c_msg.reset()
        
            data = self._console.loop()
            if data is None:
                break

            response = self.dispatch(data)
            self.c_msg.response(response)


    def check_args(self, num, args, strict=False):
        """
        Check number of arguments.
        """
        if strict:
            if len(args) != num:
                if num == 0:
                    num = 'no'
                raise DispatcherCommandError("This command accepts %s arguments" % num)
        else:
            if len(args) < num:
                raise DispatcherCommandError("This command accepts at least %d arguments"
                                                                                 % num)

##########################################################################

    def cmd_list_aclrules(self, *args):
        """
        list_aclrules [acl_name]

        List ACL rules and display their id.
        """
        self.check_args(0, args)

        name = len(args) and args[0] or None
        resp = []
        old = ''
        i = 0
        aclrules = Backend().list_aclrules(name)
        aclrules.sort(lambda x, y: cmp(x.name, y.name))
        for rule in aclrules:
            if old != rule.name:
                i = 0
                resp.append('%s:' % rule.name)
            resp.append('  [%d] %s' % (i, rule.rule))
            old = rule.name
            i += 1

        return '\n'.join(resp)

    acl_set_aclrule = 'acl(admin)'
    def cmd_set_aclrule(self, *args):
        """
        set_aclrule acl_name[:id] acl expression

        Add or update an ACL rule. If id is given, it's an update,
        otherwise the rule is appended to the list.

        # The following is not working yet:
        # set_aclrule acl_name:oldid :newid
        #
        # Reorder an ACL rule. The rule is moved from oldid to newid
        # and other rules are shifted as needed.
        """
        self.check_args(2, args)

        # keep quotes in expression
        args = self.cmdline.split()[1:]
        name = args[0]
        if ':' in args[0]:
            name, id = args[0].split(':', 1)
            action = 'update'
        else:
            name, id = args[0], 0
            action = 'add'

        try:
            id = int(id)
        except ValueError:
            return "Need numeric id, got %s" % id

        if args[1][0] == ':':
            try:
                newid = int(args[1][1:])
            except ValueError:
                return "Need numeric id, got %s" % newid
            action = 'reorder'
        else:
            rule = ' '.join(args[1:])


        if action == 'add':
            Backend().add_aclrule(name, rule.replace('\\n', '\n'))
        elif action == 'update':
            Backend().set_aclrule(name, rule.replace('\\n', '\n'), id)
        elif action == 'reorder':
            return "Reordering rules is not yet available"
        #    Backend().get_aclrule(name, id)

        Backend().acldb.save_rules()

    acl_del_aclrule = "acl(admin)"
    def cmd_del_aclrule(self, *args):
        """
        del_aclrule acl_name[:id] [acl_name[:id] ...]

        Delete ACL rules. If id is omitted, delete all rules
        from acl_name.
        """
        self.check_args(1, args)

        for arg in args:
            id = None
            if ':' in arg:
                try:
                    arg, id = arg.split(':')
                    id = int(id)
                except ValueError:
                    return "Rule id must be numeric"

            Backend().del_aclrule(arg, id)

        Backend().acldb.save_rules()



##########################################################################

    def cmd_list_clients(self, *args):
        """
        list_clients

        List clients.
        """
        self.check_args(0, args, strict=False)

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

    acl_add_client = "acl(admin)"
    def cmd_add_client(self, *args):
        """
        add_client username [tag=value ...]

        Add a new client to the client database.
        """
        self.check_args(1, args)

        if Backend().client_exists(args[0]):
            return "Client %s does already exist." % args[0]

        tokens = {}
        for arg in args[1:]:
            t = arg.split('=', 1)
            if len(t) > 1:
                value = t[1].replace("\\n", "\n")
                if value and value[0] == value[-1] == '"':
                    value = value[1:-1]
            else:
                return 'Parse error around <%s>' % arg

            if t[0] == 'password' and str(value).strip():
                while True:
                    i = 0
                    for c in value:
                        if not ('0' <= c <= '9') and not ('a' <= c <= 'f'):
                            break
                        i += 1
                    if i == 40:
                        # this looks like an sha1 already
                        # so don't convert it
                        # who would have a password like this anyway ?
                        break
                    import sha
                    value = sha.new(value).hexdigest()
                    break
            tokens[t[0]] = value

        resp = Backend().add_client(args[0], **tokens)
        return resp

    acl_del_client = "acl(admin)"
    def cmd_del_client(self, *args):
        """
        del_client username

        Delete a client from the client database.
        """
        self.check_args(1, args, strict=True)

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

    acl_tag_client = "acl(admin)"
    def cmd_tag_client(self, *args):
        """
        tag_client username [tag=value ...]

        Add or update a client's tags.
        If no tag is provided, show the client tags.
        If a tag has no value, it is deleted.
        """
        self.check_args(1, args)

        if not Backend().client_exists(args[0]):
            return "Client %s does not exist." % args[0]

        tokens = {}
        for arg in args[1:]:
            t = arg.split('=', 1)
            if len(t) > 1:
                value = t[1].replace("\\n", "\n")
                if value and value[0] == value[-1] == '"':
                    value = value[1:-1]
            else:
                return 'Parse error around <%s>' % arg

            if t[0] == 'username':
                return "'username' is a read-only tag"
            else:
                if t[0] == 'password' and str(value).strip():
                    while True:
                        i = 0
                        for c in value:
                            if not ('0' <= c <= '9') and not ('a' <= c <= 'f'):
                                break
                            i += 1
                        if i == 40:
                            # this looks like an sha1 already
                            # so don't convert it
                            # who would have a password like this anyway ?
                            break
                        import sha
                        value = sha.new(value).hexdigest()
                        break
                tokens[t[0]] = value

            

        tags = Backend().tag_client(args[0], **tokens)
        resp = []
        for tag, value in tags.items():
            value = self.show_tag_filter('client', tag, value)
            resp.append('%s = "%s"' % (tag, value))
        return '\n'.join(resp)

##########################################################################

    def cmd_list_sites(self, *args):
        """
        list_sites

        List all sites.
        """
        self.check_args(0, args, strict=False)

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
            sites.append([site.login or 'ORPHAN', site.name,
                                        site.get_tags().get('priority', '0')])

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

    acl_add_site = "acl(admin)"
    def cmd_add_site(self, *args):
        """
        add_site [user@]site [tag=value ...]

        Add a new site to the site database.
        """
        self.check_args(1, args)

        if Backend().site_exists(args[0]):
            return "Site %s does already exist." % args[0]

        tokens = {}
        for arg in args[1:]:
            t = arg.split('=', 1)
            if len(t) > 1:
                value = t[1].replace("\\n", "\n")
                if value and value[0] == value[-1] == '"':
                    value = value[1:-1]
            else:
                return 'Parse error around <%s>' % arg

            if t[0] in ('password', 'pkey'):
                while len(value):
                    if value[0] == '$':
                        parts = value.split('$')
                        if len(parts) >= 3 and part[1] in cipher.list_engines():
                            # this is already ciphered
                            break

                    tokens[t[0]] = cipher.cipher(value)
                    break
            else:
                tokens[t[0]] = value

        resp = Backend().add_site(args[0], **tokens)
        return resp

    acl_del_site = "acl(admin)"
    def cmd_del_site(self, *args):
        """
        del_site [user@]site

        Delete a site from the site database.
        """
        self.check_args(1, args, strict=True)

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

    acl_tag_site = "acl(admin)"
    def cmd_tag_site(self, *args):
        """
        tag_site [user@]site [tag=value ...]

        Add or update a site's tags.
        If no tag is provided, show the site tags.
        If a tag has no value, it is deleted.
        """
        self.check_args(1, args)

        if not Backend().site_exists(args[0]):
            return "Site %s does not exist." % args[0]

        tokens = {}
        for arg in args[1:]:
            t = arg.split('=', 1)
            if len(t) > 1:
                value = t[1].replace("\\n", "\n")
                if value and value[0] == value[-1] == '"':
                    value = value[1:-1]
            else:
                return 'Parse error around <%s>' % arg

            if t[0] in ('name', 'login'):
                return "'%s' is a read-only tag" % t[0]
            elif t[0] in ('password', 'pkey'):
                while len(value):
                    if value[0] == '$':
                        parts = value.split('$')
                        if (len(parts) >= 3 and 
                                parts[1] in cipher.list_engines():
                            # this is already ciphered
                            break

                    tokens[t[0]] = cipher.cipher(value)
                    break
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
        if not self.is_admin() and object == 'site':
            # mangle sensible data
            if tag in ('password', '_pkey') and value:
                return ('*'*len(value))[:30]

        return value


Dispatcher.register()


