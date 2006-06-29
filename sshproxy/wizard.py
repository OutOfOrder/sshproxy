#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jun 30, 00:26:45 by david
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
    from sshproxy import config
    configdir = config.inipath

    if not os.path.isdir(configdir):
        print 'Creating config dir %s' % configdir
        os.makedirs(os.path.join(configdir, 'log'))

    config.get_config = config.Config(config.inifile)
    cfg = config.get_config('sshproxy')

    cfg['bindip'] = raw_input("Enter the IP address to listen on [%s]: " % (
                                    cfg['bindip'] or 'any')) or cfg['bindip']
    if cfg['bindip'] == 'any':
        cfg['bindip'] = ''
    
    cfg['port'] = raw_input("Enter the port to listen on [%s]: " % 
                                            cfg['port']) or cfg['port']
    
    cfg['cipher_type'] = raw_input("Enter the cipher method to crypt passwords"
                            " in the database (plain/base64/blowfish) [%s]: " % 
                                    cfg['cipher_type']) or cfg['cipher_type']
    
    
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
    
    
    import plugins
    plugins.init_plugins()
    from backend import get_backend

    cfg = maincfg
    while True:
        cfg['pwdb_backend'] = raw_input("Enter the password database backend "
                            "you prefer to use (file/mysql) [%s]: " % 
                                    cfg['pwdb_backend']) or cfg['pwdb_backend']
        if cfg['pwdb_backend'] == 'file':
                    "WARNING: The file backend is insecure for now, "
                            "because it will let any user to connect to the "
                            "proxy, and thus to any remote site you "
                            "configured. This will change in the future, but "
                            " this backend is for testing purpose until then. "
            ans = raw_input("Do you really want to continue ? (yes I have "
                                                        "read the warning)")
            if ans.lower() == "yes i have read the warning":
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

    print 'Setup done.'
    print 'You can now run the following command:'
    print os.environ.get('INITD_STARTUP', '%s -c %s' % (sys.argv[0], configdir)


