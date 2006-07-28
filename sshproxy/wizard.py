#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 28, 04:02:31 by david
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


def setup():
    os.environ['SSHPROXY_WIZARD'] = 'running'
    import config
    configdir = config.inipath

    if not os.path.isdir(configdir):
        print 'Creating config dir %s' % configdir
        os.makedirs(os.path.join(configdir, 'log'))

    config.get_config = config.Config(config.inifile)
    cfg = config.get_config('sshproxy')

    cfg['listen_on'] = raw_input("Enter the IP address to listen on [%s]: " % (
                                cfg['listen_on'] or 'any')) or cfg['listen_on']
    if cfg['listen_on'] == 'any':
        cfg['listen_on'] = ''
    
    cfg['port'] = raw_input("Enter the port to listen on [%s]: " % 
                                            cfg['port']) or cfg['port']
    
    import plugins
    while True:
        i = 0
        plugin_list = []
        for name, mname, module, desc, disabled in plugins.plugin_list:
            if not disabled:
                name = '*' + name
                plugin_list.append(mname)
            print '%d. %s "%s"' % (i, name, desc)
            i += 1
        newplugin = raw_input("Select a plugin to add to the list [%s]: "
                                                    % ' '.join(plugin_list))
        if not newplugin.strip():
            cfg['plugin_list'] = ' '.join(plugin_list)
            break
        try:
            n = int(newplugin)
        except ValueError:
            continue
        plugins.plugin_list[n][4] ^= 1



    import cipher
    cipher_list = cipher.list_engines()

    while True:
        cipher_type = raw_input("Enter the cipher method to crypt passwords"
                            " in the database (%s) [%s]: " % 
                            (','.join(cipher_list), cfg['cipher_type'])
                            ) or cfg['cipher_type']
        if cipher_type in cipher_list:
            cfg['cipher_type'] = cipher_type
            break
    
    
    maincfg = cfg
    
    if cfg['cipher_type'] == 'blowfish':
        cfg = config.get_config('blowfish')
    
        print
        while True:
            secret1 = getpass.getpass("Enter the secret passphrase that will "
                "be used to crypt passwords "
                "(at least 10 characters/leave empty to keep the old one): ")
            if not secret1:
                break
            secret2 = getpass.getpass("Confirm passphrase: ")
            if (len(secret1) + len(secret2)) < 20:
                print "You must enter at least 10 characters"
            elif secret1 == secret2:
                cfg['secret'] = secret1
                break
            else:
                print "Passphrases don't match"

    

    cfg = maincfg
    for db_type in ('client', 'acl', 'site'):
        db_id = db_type + '_db'

        while True:
            choice = cfg[db_id].replace('_db', '')
            choice = raw_input("Enter the password database backend "
                            "you prefer to use for %ss (file/mysql) [%s]: " % 
                                    (db_type, choice)) or choice
            if choice in ('file', 'mysql'):
                cfg[db_id] = choice + '_db'
                break


    cfg.write()

    host_key_file = os.path.join(config.inipath, 'id_dsa')
    sshd_key_file = "/etc/ssh/ssh_host_dsa_key"
    if not os.path.exists(host_key_file) and os.path.exists(sshd_key_file):
        ans = raw_input("Do you want to use the sshd host key with sshproxy ?"
                                                                    " (y/N) ")
        if ans.lower() in ("y", "yes"):
            hkfile = open(host_key_file, "w")
            hkfile.write(open(sshd_key_file).read())
            hkfile.close()
            # change the mode to a reasonable value
            os.chmod(host_key_file, 0400)
            # set the same uid/gid as the config directory
            st = os.stat(config.inipath)
            os.chown(host_key_file, st.st_uid, st.st_gid)

    plugins.init_plugins()
    from backend import get_backend
    be = get_backend()
    wizard = be.get_wizard()
    if wizard:
        a = raw_input("Do you want to run the %s backend "
                        "configuration wizard ? (yes/no)" % be.backend_id)
        if a == "yes":
            try:
                wizard.run()
            except KeyboardInterrupt:
                print " ...Aborted."


        
    print """
Please check the documentation at the following address to add sites and
users to your database:
    """
    if cfg['pwdb_backend'] == 'file':
        print """
http://penguin.fr/sshproxy/documentation.html#file-backend-add-sites-and-users
        """
    elif cfg['pwdb_backend'] == 'mysql':
        print """
http://penguin.fr/sshproxy/documentation.html#mysql-backend-add-sites-and-users
        """

    print 'Setup done.'
    print 'You can now run the following command:'
    print os.environ.get('INITD_STARTUP',
                            '%s -c %s' % (sys.argv[0], configdir))


