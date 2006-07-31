#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 31, 02:41:06 by david
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

import sys, os, os.path
import getpass

from menu import Menu, MenuInput, MenuSep, MenuDyn, MenuSwitch, MenuSub, MenuChoice, MenuPassword


class Wizard(object):
    def __init__(self):
        import config
        self.cfg  = config.get_config('sshproxy')
        self.menu = self.make_menu()
        while True:
            try:
                self.menu()
                break
            except KeyboardInterrupt:
                print
                try:
                    ans = raw_input("Do you want to abort without"
                                    " saving ? [y/n]")
                except KeyboardInterrupt:
                    print 'Aborted.'
                    sys.exit(0)
                if ans and ans.lower()[0] == 'y':
                    print 'Aborted.'
                    sys.exit(0)
        self.cfg.write()
        print 'Configuration saved.'

    def get_current_backends(self):
        return (self.cfg['acl_db'],
                self.cfg['client_db'],
                self.cfg['site_db'])

    def set_listen_on(self, value):
        self.cfg['listen_on'] = value

    def set_port(self, value):
        try:
            value = int(value)
        except ValueError:
            print "Port must be numeric"
            return False
        if not (0 < value < 65536):
            print "Port must be a number comprised between 1 and 65535"
            return False
        self.cfg['port'] = value

    def set_auto_add_key(self, value):
        value = value.lower()
        if value not in ('yes', 'no'):
            try:
                if int(value) < 0:
                    raise ValueError
            except ValueError:
                print "Unknown value %s" % value
                return False
        self.cfg['auto_add_key'] = value

    def set_pkey_id(self, value):
        self.cfg['pkey_id'] = value

    def set_cipher(self, value):
        import cipher
        if value not in cipher.list_engines():
            return False
        self.cfg['cipher_type'] = value

    def set_blowfish_secret(self, value):
        import cipher
        import config
        if value:
            if len(value) < 10:
                print "You must enter at least 10 characters."
                return False
            config.get_config['blowfish']['secret'] = value
        else:
            raw_input("Secret passphrase untouched.\nPress enter")

    def set_backend(self, value, backend):
        if self.cfg[backend] == value:
            return
        old = self.cfg[backend]
        self.cfg[backend] = value
        # add the new backend to the plugin list
        self.enable_plugin(value, True)
        if old not in self.get_current_backends():
            # remove the old unused backend from the plugin list
            self.enable_plugin(old, False)

    def enable_plugin(self, value, state):
        enp = self.cfg['plugin_list'].split()
        if state:
            enp.append(value)
        else:
            enp.remove(value)
        # make unique
        enp = dict(map(lambda x: (x, x), enp)).keys()
        enp.sort()
        self.cfg['plugin_list'] = ' '.join(enp)
        self.plugins[value].enabled = state
        return True

    def load_plugins_info(self):
        import plugins
        from util import SortedDict
        self.plugins = SortedDict()
        self.enabled_plugins = SortedDict()
        for plugin in plugins.plugin_list:
            self.plugins[plugin.name] = plugin
            if plugin.enabled:
                self.enabled_plugins[plugin.name] = plugin

    def make_plugins_menu(self):
        plugin_list = []
        for name, plugin in self.plugins.items():
            if plugin.backend:
                continue
            plugin_list.append(MenuSwitch(plugin.plugin_name,
                                          plugin.name,
                                          plugin.enabled,
                                          cb=self.enable_plugin))

        select_plugins = Menu('Select plugins',
                      'Add or remove plugins from the list',
                      *plugin_list)

        plugmenu = MenuDyn(self.make_plugin_list, "Plugins settings")

        return [
                MenuSep('Plugin options'),
                select_plugins,
                MenuSep(),
                plugmenu
                ]

    def make_plugin_list(self):
        plugins = []
        for name, plugin in self.plugins.items():
            if not plugin.enabled or plugin.backend:
                continue
            plugins.append(Menu(plugin.plugin_name,
                                plugin.description,
                                *(plugin.setup() or [])))

        return plugins

    def make_backends_menu(self):
        backends = self.get_current_backends()
        backend_items = []
        backend_plugins = []
        for name, plugin in self.plugins.items():
            if not plugin.backend:
                continue
            backend_items.append((plugin.plugin_name,
                                 name))
            if name in backends:
                backend_plugins.append(Menu(plugin.plugin_name,
                                            plugin.description,
                                            *(plugin.setup() or [])))

        acl_menu = MenuChoice('ACL database backend type',
                        "Choose a backend",
                        self.cfg['acl_db'],
                        self.set_backend,
                        backend='acl_db',
                        *backend_items
                        )
        client_menu = MenuChoice('Client database backend type',
                        "Choose a backend",
                        self.cfg['client_db'],
                        self.set_backend,
                        backend='client_db',
                        *backend_items)
        site_menu = MenuChoice('Site backend type',
                        "Choose a backend",
                        self.cfg['site_db'],
                        self.set_backend,
                        backend='site_db',
                        *backend_items)
        backend_menu = MenuSub("Backends", "", *backend_plugins)

        return [
                MenuSep('Choose backends'),
                acl_menu,
                client_menu,
                site_menu,
                MenuSep(),
                MenuSep('Configure backends'),
                backend_menu
                ]

    def make_cipher_menu(self):
        import config
        cipher = self.cipher_module
        cipher_list = [ (o.capitalize(), o) for o in cipher.list_engines() ]
        menu = []
        menu.append(MenuChoice('Cipher engine',
                            ("Please choose a cipher engine to crypt passwords "
                             "in the database."),
                            self.cfg['cipher_type'],
                            self.set_cipher,
                            *cipher_list))
        if self.cfg['cipher_type'] == 'blowfish':
            menu.append(MenuPassword(
                    'Blowfish secret passphrase',
                    "Enter at least 10 characters.",
                    config.get_config['blowfish']['secret'],
                    self.set_blowfish_secret))
        return menu

    def make_menu(self):
        import cipher
        self.cipher_module = cipher
        self.load_plugins_info()
        menu = Menu('Configure sshproxy', None,

            MenuSep('Global options'),
            MenuInput('IP address or interface',
                      ("Enter the IP address or the interface name on wich "
                       "the server will listen for incomming connections."),
                      self.cfg['listen_on'] or 'any',
                      self.set_listen_on),
            MenuInput('Port',
                      ("Enter the port on which the server will listen for "
                       "incomming connections."),
                      self.cfg['port'],
                      self.set_port),
            MenuInput('Auto-add public key',
                      ("If you want the auto-add-key feature, enter here the "
                       "number of keys auto-added in the client keyring, or "
                       "'yes' for no limit. Saying 'no' disable this feature."
                       "\nAttention: this feature, if enabled, can be "
                       "dangerous."),
                      self.cfg['auto_add_key'],
                      self.set_auto_add_key),
            MenuInput('Public key id string',
                      ("Enter the public key id string used to identify the "
                       "proxy public key that can be put in a remote "
                       ".ssh/authorized_keys file. This is typically in the "
                       "form of an email address."),
                      self.cfg['pkey_id'],
                      self.set_pkey_id),
            )

        menu.add(MenuDyn(self.make_cipher_menu, "Cipher"))

        menu.add(MenuSep())

        menu.add(MenuDyn(self.make_backends_menu, "Backends"))

        menu.add(MenuSep())

        menu.add(self.make_plugins_menu())

        menu.add(MenuSep())

        menu.back_text = "Quit"
        return menu




def setup():
    os.environ['SSHPROXY_WIZARD'] = 'running'
    import config
    configdir = config.inipath

    if not os.path.isdir(configdir):
        print 'Creating config dir %s' % configdir
        os.makedirs(os.path.join(configdir, 'log'))

    config.get_config = config.Config(config.inifile)
    cfg = config.get_config('sshproxy')

    Wizard()
    print 'Setup done.'
    print 'You can now run the following command:'
    print os.environ.get('INITD_STARTUP',
                            'sshproxyd -c %s' % (configdir))


