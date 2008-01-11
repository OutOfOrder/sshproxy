#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
#
# Last modified: 2008 Jan 11, 17:09:14 by david
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

import os, shlex

from registry import Registry
from backend import Backend
import ipc
from ptywrap import PTYWrapper
from console import Console
from acl import ACLDB
import cipher
import log

###########################################################################
class DispatcherCommandError(Exception):
    pass

class Dispatcher(Registry, ipc.IPCInterface):
    _class_id = 'Dispatcher'
    _singleton = True

    default_acl = True

    def __reginit__(self, daemon_ipc, namespace):
        self.d_ipc = daemon_ipc
        self.namespace = namespace
        self.daemon_methods = {}
        for line in self.d_ipc.call('public_methods'):
            method, help = line
            self.daemon_methods[method] = help #.replace('\n', '\\n')

    def __init__(self, *args, **kw):
        pass

    def default_call_handler(self, _name, _chan, *args, **kw):
        import shlex
        import re
        func = getattr(self, 'cmd_' + _name, None)
        if not func:
            if _name in self.daemon_methods:
                return self.d_ipc.call(_name, *args, **kw)
            else:
                # TODO: raise and catch in ipc
                try:
                    raise AttributeError(_(u'Dispatcher.cmd_%s does not exist'
                                                                    % _name))
                except AttributeError:
                    log.exception('in Dispatcher.default_call_handler')
                return _(u'%s does not exist') % _name

        if len(args):
            self.cmdline = args[0]
            arguments = shlex.split(args[0])
            rx = re.compile('([a-zA-Z_][a-zA-Z0-9_]*)=(.*)')
            args = []
            kw = {}
            for arg in arguments:
                m = rx.match(arg)
                if m:
                    kw[m.group(1)] = m.group(2)
                else:
                    args.append(arg)
        else:
            self.cmdline = ''
        
        try:
            return func(*args, **kw)
        except DispatcherCommandError, msg:
            return str(msg)
        except:
            log.exception("An exception occured in " +
                                            "Dispatcher.default_call_handler")
            return _(u"Something wrong happened. "
                        "Please contact the administrator.")


    def is_admin(self):
        return ACLDB().check('admin', **self.namespace)

    def public_methods(self):
        u"""
        Return a list of allowed commands.
        """
        if self.is_admin():
            methods = self.daemon_methods.items()
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
            methods.append((method[4:], _(doc)))

        return methods

    def cmd_public_methods(self, *args, **kw):
        return self.public_methods()

    def check_acl(self, *args):
        u"""
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
            log.exception("Parse error in Dispatcher.dispatch()")
            return _(u'parse error')

        if not len(args):
            return ''

        if args[0] == 'public_methods':
            return self.public_methods()

        if args[0] == 'help':
            pm = self.public_methods()
            pm.sort()
            return '\n'.join([ u'%s:\t%s' % (cmd, help) for cmd, help in pm])

        command = 'cmd_' + args[0]

        if not hasattr(self, command):
            if args[0] in self.daemon_methods.keys() and self.is_admin():
                return self.d_ipc.call(*args)

            else:
                return _(u'Unknown command %s') % args[0]

        if not self.check_acl(*args):
            return _(u'You have not enough rights to do this')

        func = getattr(self, command)

        try:
            return func(*args[1:])
        except DispatcherCommandError, msg:
            return msg

    def init_console(self, cmd=None):
        from server import Server

        address = 'sshproxy-control-%d' % os.getpid()

        def PtyConsole(*args, **kwargs):
            if cmd:
                Console(*args, **kwargs).onecmd(cmd)
            else:
                Console(*args, **kwargs).cmdloop()

        self._console = PTYWrapper(Server().chan, PtyConsole, address=address,
                                                              handler=self)

    def __call__(self, chan):
        self.c_ipc = chan
        return self


    def console(self, cmd=None):
        from server import Server
        self.init_console(cmd)

        self._console.loop()


    def check_args(self, num, args, strict=False):
        u"""
        Check number of arguments.
        """
        if strict:
            if len(args) != num:
                if num == 0:
                    num = 'no'
                raise DispatcherCommandError(
                        _(u"This command accepts %s arguments") % num)
        else:
            if len(args) < num:
                raise DispatcherCommandError(
                        _(u"This command accepts at least %d arguments") % num)

##########################################################################

    def cmd_list_aclrules(self, *args, **kw):
        u"""
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
    def cmd_set_aclrule(self, *args, **kw):
        u"""
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
        args = self.cmdline.split()
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
            return _(u"Need numeric id, got %s") % id

        if args[1][0] == ':':
            try:
                newid = int(args[1][1:])
            except ValueError:
                return _(u"Need numeric id, got %s") % newid
            action = 'reorder'
        else:
            rule = ' '.join(args[1:])


        if action == 'add':
            Backend().add_aclrule(name, rule.replace('\\n', '\n'))
        elif action == 'update':
            Backend().set_aclrule(name, rule.replace('\\n', '\n'), id)
        elif action == 'reorder':
            return _(u"Reordering rules is not yet available")

        Backend().acldb.save_rules()

    acl_del_aclrule = "acl(admin)"
    def cmd_del_aclrule(self, *args, **kw):
        u"""
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
                    return _(u"Rule id must be numeric")

            Backend().del_aclrule(arg, id)

        Backend().acldb.save_rules()



##########################################################################

    def cmd_list_clients(self, *args, **kw):
        u"""
        list_clients

        List clients.
        """
        self.check_args(0, args, strict=False)

        resp = Backend().list_clients(**kw)
        resp.append(_(u'\nTotal: %d') % len(resp))
        return '\n'.join(resp)

    acl_add_client = "acl(admin)"
    def cmd_add_client(self, *args, **kw):
        u"""
        add_client username [tag=value ...]

        Add a new client to the client database.
        """
        self.check_args(1, args)

        if Backend().client_exists(args[0]):
            return _(u"Client %s does already exist.") % args[0]

        if 'password' in kw:
            import sha
            kw['password'] = sha.new(kw['password']).hexdigest()
        resp = Backend().add_client(args[0], **kw)
        return resp

    acl_del_client = "acl(admin)"
    def cmd_del_client(self, *args, **kw):
        u"""
        del_client username

        Delete a client from the client database.
        """
        self.check_args(1, args, strict=True)


        if self.d_ipc.call('get_ns_tag', 'client', 'username') == args[0]:
            return _(u"Don't delete yourself!")

        b = Backend()

        if not b.client_exists(args[0]):
            return _(u"Client %s does not exist.") % args[0]

        resp = b.del_client(args[0], **kw)
        return resp

    acl_tag_client = "acl(admin)"
    def cmd_tag_client(self, *args, **kw):
        u"""
        tag_client username [tag=value ...]

        Add or update a client's tags.
        If no tag is provided, show the client tags.
        If a tag has no value, it is deleted.
        """
        self.check_args(1, args)

        if not Backend().client_exists(args[0]):
            return _(u"Client %s does not exist.") % args[0]

        if 'password' in kw:
            import sha
            kw['password'] = sha.new(kw['password']).hexdigest()
        tags = Backend().tag_client(args[0], **kw)
        resp = []
        for tag, value in tags.items():
            value = self.show_tag_filter('client', tag, value)
            resp.append('%s = "%s"' % (tag, value.replace('"', '\\"')))
        return '\n'.join(resp)

    acl_set_client_password = "acl(admin)"
    def cmd_set_client_password(self, *args, **kw):
        u"""
        set_client_password username

        Set or change a client password.
        """
        self.check_args(1, args, strict=True)

        if not Backend().client_exists(args[0]):
            return _(u"Client %s does not exist.") % args[0]

        if 'password' not in kw:
            return _(u"Missing password in argument list")

        import sha
        kw['password'] = sha.new(kw['password']).hexdigest()
        tags = Backend().tag_client(args[0], **kw)
        return _(u"Password updated")


##########################################################################

    def cmd_list_sites(self, *args, **kw):
        u"""
        list_sites

        List all sites.
        """
        self.check_args(0, args, strict=False)

        sites = []
        for site in Backend().list_site_users(**kw):
            sites.append([site.login or _(u'ORPHAN'), site.name,
                                        site.get_tags().get('priority', '0')])

        resp = []
        if len(sites):
            name_width = max([ len(e[0]) + len(e[1]) for e in sites ])
            for uid, name, priority in sites:
                priority = priority or '0'
                sid = '%s@%s' % (uid, name)
                resp.append('%s %s %s' % (sid, ' '*(name_width + 1 - len(sid)),
                                                            '[%s]' % priority))
        resp.append(_(u'\nTotal: %d') % len(resp))
        return '\n'.join(resp)

    acl_add_site = "acl(admin)"
    def cmd_add_site(self, *args, **kw):
        u"""
        add_site [user@]site [tag=value ...]

        Add a new site to the site database.
        """
        self.check_args(1, args)

        if Backend().site_exists(args[0]):
            return _(u"Site %s does already exist.") % args[0]

        for token in kw.keys():
            if token in ('password', 'pubkey'):
                value = kw[token]
                while len(value):
                    if value[0] == '$':
                        parts = value.split('$')
                        if (len(parts) >= 3
                                        and parts[1] in cipher.list_engines()):
                            # this is already ciphered
                            break

                    kw[token] = cipher.cipher(value)
                    break

        resp = Backend().add_site(args[0], **kw)
        return resp

    acl_del_site = "acl(admin)"
    def cmd_del_site(self, *args, **kw):
        u"""
        del_site [user@]site

        Delete a site from the site database.
        """
        self.check_args(1, args, strict=True)

        if not Backend().site_exists(args[0]):
            return _(u"Site %s does not exist.") % args[0]

        resp = Backend().del_site(args[0], **kw)
        return resp

    acl_tag_site = "acl(admin)"
    def cmd_tag_site(self, *args, **kw):
        u"""
        tag_site [user@]site [tag=value ...]

        Add or update a site's tags.
        If no tag is provided, show the site tags.
        If a tag has no value, it is deleted.
        """
        self.check_args(1, args)

        if not Backend().site_exists(args[0]):
            return _(u"Site %s does not exist.") % args[0]

        for token in kw.keys():
            if token in ('password', 'pubkey'):
                value = kw[token]
                while len(value):
                    if value[0] == '$':
                        parts = value.split('$')
                        if (len(parts) >= 3
                                        and parts[1] in cipher.list_engines()):
                            # this is already ciphered
                            break

                    kw[token] = cipher.cipher(value)
                    break

        tags = Backend().tag_site(args[0], **kw)

        if not hasattr(tags, 'items'):
            # this is an error message
            return tags

        resp = []
        for tag, value in tags.items():
            value = self.show_tag_filter('site', tag, value)
            resp.append('%s = "%s"' % (tag, value))
        return '\n'.join(resp)

    acl_set_site_password = "acl(admin)"
    def cmd_set_site_password(self, *args, **kw):
        u"""
        set_site_password user@site

        Set or change a site password.
        """
        self.check_args(1, args, strict=True)

        if len(args[0].replace('@', '')) != len(args[0]) - 1:
            return _(u"%s is not a valid user@site") % args[0]

        if not Backend().site_exists(args[0]):
            return _(u"Site %s does not exist.") % args[0]

        if 'password' not in kw:
            return _(u"Missing password in argument list")

        kw['password'] = self.cipher_token(kw['password'])
        tags = Backend().tag_site(args[0], **kw)
        return _(u"Password updated")

    acl_set_site_privkey = "acl(admin)"
    def cmd_set_site_privkey(self, *args, **kw):
        u"""
        set_site_privkey [user@]site

        Set or change a site private key.
        """
        self.check_args(1, args, strict=True)

        if not Backend().site_exists(args[0]):
            return _(u"Site %s does not exist.") % args[0]

        if 'privkey' not in kw:
            return _(u"Missing privkey in argument list")

        kw['privkey'] = self.cipher_token(kw['privkey']).replace('\\n', '\n')
        tags = Backend().tag_site(args[0], **kw)
        return _(u"Private key updated")


    def cipher_token(self, value):
        if len(value):
            if value[0] == '$':
                parts = value.split('$')
                if (len(parts) >= 3
                                and parts[1] in cipher.list_engines()):
                    # this is already ciphered
                    return value

            return cipher.cipher(value)

        return value

    def show_tag_filter(self, object, tag, value):
        value = value or ''
        if not self.is_admin() and object == 'site':
            # mangle sensible data
            if tag in ('password', '_pkey') and value:
                return ('*'*len(value))[:30]

        return value


Dispatcher.register()


