#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jun 04, 01:35:07 by david
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


import getpass
import sys
import cmd
import readline

from SSHproxy.cipher import cipher

from mysql import MySQLPwDB



pwdb = MySQLPwDB()

class CommandLine(object):
    def __init__(self, args):
        if type(args) == type(''):
            self.args = self.decode(args)
        else:
            self.args = args

    def __len__(self):
        return len(self.args)

    def __getitem__(self, item):
        return self.args[item]

    def decode(self, args):
        l = [ e.strip() for e in args.split() ]
        l = [ e for e in l if e ]
        return l

    def encode(self, args=None):
        if not args:
            args = self.args
        return ' '.join(args)



class DBConsole(cmd.Cmd):
    def __init__(self):
        self.current_site = None
        cmd.Cmd.__init__(self)
        self.prompt = '\npwdb> '

    def emptyline(self):
        return

    def _complete_sites(self, text, line, begidx, endidx):
        sites = self._sites()
        w = len(text)
        l = []
        for name, ip, loc in sites:
            if w > len(name):
                continue
            if text == name[:w]:
                l.append(name+' ')
        return l

    def _complete_domains(self, text, line, begidx, endidx):
        domains = self._domains()
        w = len(text)
        l = []
        for id, name in domains:
            if w > len(name):
                continue
            if text == name[:w]:
                l.append(name+' ')
        return l

    def complete_list_users(self, text, line, begidx, endidx):
        return self._complete_sites(text, line, begidx, endidx)

    def complete_list_domains(self, text, line, begidx, endidx):
        return self._complete_sites(text, line, begidx, endidx)

    def complete_list_sites(self, text, line, begidx, endidx):
        return self._complete_domains(text, line, begidx, endidx)

    def set_password(self, user):
        import termios
        pass1 = ""
        pass2 = " "
        print 'Setting password for user %s' % user
        try:
            while (pass1 != pass2):
                pass1 = getpass.getpass("Enter new password: ")
                pass2 = getpass.getpass("Confirm password: ")
            if pass1 == '':
                raise termios.error
        except EOFError:
            print 'Abort'
            return
        except termios.error:
            print 'Warning: Could not set password, setting random password:'
            import string, random
            pass1 = [ random.choice(string.ascii_letters + string.digits)
                                                        for x in range(8) ]
            pass1 = ''.join(pass1)
            print pass1
        print 'Password set for user %s' % user
        return pass1

    def _sites(self, domain=None):
        sites=[]
        for site in pwdb.list_sites(domain=domain):
            sites.append((site['name'], site['ip'], site['location']))
        sites.sort(lambda x,y: x[0] < y[0])
        return sites

    def _domains(self, site=None):
        domains = pwdb.list_domains(site=site)
        domain = []
        for g in domains:
            domain.append((g['id'], g['name']))
        domain.sort(lambda x,y: x[1] < y[1])
        return domain

    def completenames(self, text, *ignored):
        dotext = 'do_'+text
        return [a[3:]+' ' for a in self.get_names() if a.startswith(dotext)]


    ############################################################
    # PUBLIC METHODS - COMMANDS
    ############################################################

    def do_add_site(self, arg):
        """
            add_site name IP_address port location

            Add a new site. The name is a symbolic name, not necessary the
            real hostname. The location is only informative (but mandatory).
        """
        arg = CommandLine(arg)
        if len(arg) != 4:
            self.onecmd('help add_site')
            return
        else:
            pwdb.add_site(arg[0], arg[1], int(arg[2]), arg[3])

    def do_del_site(self, arg):
        """
            del_site name

            Remove a site from the database.
            All remote users belonging to that site will be deleted !
        """
        arg = CommandLine(arg)
        if len(arg) != 1:
            self.onecmd('help del_site')
            return
        else:
            if not pwdb.remove_site(arg[0]):
                print "No such site: %s\n" % arg[0]

    def do_list_sites(self, arg):
        """
            list_sites [domain]

            Print the site list in a table.
            If domain is present, list only the sites that belong to
            the domain.
        """
        arg = CommandLine(arg)
        domain = None
        if len(arg):
            domain = arg[0]
        sites = self._sites(domain=domain)
        if len(sites):
            name_width = max([ len(e[0]) for e in sites ])
            ip_width = max([ len(e[1]) for e in sites ])
            #loc_width = max([ len(e[2]) for e in sites ])
            for name, ip, loc in sites:
                print name, ' '*(name_width - len(name)),
                print ip, ' '*(ip_width - len(ip)),
                print loc
        print
        print len(sites), 'sites in the database'

    def do_add_rlogin(self, arg):
        """
            add_rlogin uid site primary
        
            Add a remote user in a site.
            uid is the username or user id.
            primary is a boolean value (0 or 1) to specify the default username
            for that site.
            The password will be prompted.
        """
        arg = CommandLine (arg)
        if (len(arg) != 3):
            self.onecmd('help add_rlogin')
            return
        elif pwdb.get_users(arg[0], arg[1]):
            print "Remote login %s@%s already exists" % (arg[0], arg[1])
        else:
            try:
                password = self.set_password(arg[0])
                pwdb.add_user_to_site(arg[0], arg[1], cipher(password),
                                                                int(arg[2]))
            except KeyboardInterrupt:
                return

    def do_del_rlogin(self, arg):
        """
            del_rlogin uid site
        
            Remove a remote user from the site.
        """
        arg = CommandLine (arg)
        if (len(arg) != 2):
            self.onecmd('help del_rlogin')
            return
        else:
            pwdb.remove_user_from_site(arg[0], arg[1])

    def do_list_rlogins(self, arg):
        """
            list_rlogins sitename
            
            List the remote logins on the given site.
        """
        arg = CommandLine(arg)
        if not len(arg):
            if not self.current_site:
                self.onecmd('help list_rlogins')
                return
            site = self.current_site
        elif len(arg) > 1:
            self.onecmd('help list_rlogins')
            return
        else:
            site = arg[0]

        res = pwdb.get_site(site)
        if res:
            site_id = res['id']
        else:
            self.onecmd('help list_rlogins')
            return
 
        users=[]
        for user in pwdb.list_users(site_id=site_id):
            users.append((user['uid'],
                    ''.join([ '*' for i in user['password'] ])))
        users.sort(lambda x,y: x[0]<y[0])
        if len(users):
            uid_width = max([ len(e[0]) for e in users ])
        else:
            print 'No remote logins for site %s' % site
            return
        for uid, passwd in users:
            print uid + ' '*(uid_width - len(uid)), passwd

    def do_add_login(self, arg):
        """
            add_login uid [key]
            
            Add a local user.
            The password will be prompted.
            If the key is given and is not a valid ssh key, key authentication
            will be disabled for this user (ie. put 'nokey' to disable key
            authentication).
        """
        arg = CommandLine (arg)
        if len(arg) not in (1, 2):
            self.onecmd('help add_login')
            return
        else:
            password = self.set_password(arg[0])
            if len(arg) > 1:
                key = arg[1]
            else:
                key = None
            pwdb.add_login (login=arg[0], password=password, key=key)

    def do_del_login(self, arg):
        """
            del_login uid

            Remove a local user from the database, preventing any further
            connection.
        """
        arg = CommandLine (arg)
        if len (arg) != 1:
            self.onecmd('help del_login')
            return
        else:
            pwdb.remove_login(arg[0])

    def do_list_logins(self,arg):
        """
            list_logins
        
            List all users allowed to connect to the proxy.
        """
        lg_list = pwdb.list_logins()
        for lg in lg_list :
            print 'uid: %s passwd: %s key: %s' % (lg['login'], lg['password'], lg['key'])

    def do_link_login_to_profile(self, arg):
        """
            link_login_to_profile login profile
        
            Associate a local user to a connection profile.
        """
        arg = CommandLine(arg)
        if len (arg) != 2:
            self.onecmd('help link_login_to_profile')
            return
        else:
            login_id = pwdb.get_id('login', arg[0])
            profile_id = pwdb.get_id('profile', arg[1])
            pwdb.add_login_profile(login_id, profile_id)

    def do_unlink_login_from_profile(self, arg):
        """
            unlink_login_from_profile [login] [profile]
        
            Unassociate a local user from a connection profile.
        """
        arg = CommandLine(arg)
        if len (arg) != 2:
            self.onecmd('help unlink_login_from_profile')
            return
        else:
            login_id = pwdb.get_id('login', arg[0])
            profile_id = pwdb.get_id('profile', arg[1])
            pwdb.unlink_login_profile(login_id, profile_id)

    def do_list_logins_in_profile(self, arg):
        """
            list_logins_in_profile profile

            List the local users associated to a given profile.
        """
        arg = CommandLine(arg)
        if len(arg) != 1:
            self.onecmd('help list_logins_in_profile')
            return
        else:
            lp_list = pwdb.list_login_profile()
            for lp in lp_list:
                if lp['profile'] == arg[0]:
                    print '%s' % (lp['login'])

    def do_add_profile(self, arg):
        """
            add_profile profile [profile] ...
        
            Add one or more profiles.
        """
        arg = CommandLine (arg)
        if len(arg) < 1:
            self.onecmd('help add_profile')
            return
        else:
            for name in arg:
                pwdb.add_profile(name)

    def do_del_profile(self, arg):
        """
            del_profile [profile] [profile] ...
        
            Remove one or more profiles.
        """
        arg = CommandLine (arg)
        if len(arg) < 1:
            self.onecmd('help del_profile')
            return
        else:
            for name in arg:
                pwdb.remove_profile(name)

    #FIXME: sort profile list
    def do_list_profiles(self,args):
        """
            list_profiles
            
            List all profiles.
        """
        p_list = pwdb.list_profiles()
        def sort_list(x,y):
            # special profile first
            if x['id'] == 0: return True
            if y['id'] == 0: return False
            # alpha sorting for normal profiles
            return x['name'] < y['name']
        p_list.sort(sort_list)
        for pl in p_list:
            print 'id: %d, name: %s' % (pl['id'], pl['name'])

    def do_link_profile_to_domain(self, arg):
        """
            link_profile_to_domain profile domain
        
            Associate a profile to a site domain.
        """
        arg = CommandLine(arg)
        if len (arg) != 2:
            self.onecmd('help link_profile_to_domain')
            return
        else:
            profile_id = pwdb.get_id('profile', arg[0])
            domain_id = pwdb.get_id('domain', arg[1])
            pwdb.add_profile_domain(profile_id, domain_id)

    def do_unlink_profile_from_domain(self, arg):
        """
            unlink_profile_from_domain profile domain
            
            Unassociate a profile from a domain.
        """
        arg = CommandLine(arg)
        if len (arg) != 2:
            self.onecmd('help unlink_profile_from_domain')
            return
        else:
            profile_id = pwdb.get_id('profile', arg[0])
            domain_id = pwdb.get_id('domain', arg[1])
            pwdb.unlink_profile_domain(profile_id, domain_id)

    def do_list_profile_domain_links(self, arg):
        """
            list_profile_domain_links
        
            List existing links between profiles and domains.
        """
        pg_list = pwdb.list_profile_domain()
        for pg in pg_list:
            print 'profile: %s, domain: %s' % (pg['profile'], pg['domain'])

    def do_add_domain(self, arg):
        """
            add_domain domain1 [domain2] ...

            Add one or more site domains.
        """
        arg = CommandLine (arg)
        if len (arg) < 1:
            self.onecmd('help add_domain')
            return
        else:
            for name in arg[:]:
                pwdb.add_domain(name)

    def do_del_domain(self, arg):
        """
            del_domain domain1 [domain2] ...
        
            Remove one or more domains.
        """
        arg = CommandLine (arg)
        if len (arg) < 1:
            self.onecmd('help del_domain')
            return
        else:
            for name in arg[:]:
                pwdb.remove_domain(name)

    def do_list_domains(self, arg):
        """
            list_domains [site]
            
            List all domains.
            If site is given, only list the domains the site is into.
        """
        arg = CommandLine(arg)
        if len(arg) != 1:
            site = self.current_site
        else:
            site = arg[0]
        domains = self._domains(site=site)
        for id, name in domains:
            print name

    def do_link_site_to_domain(self, arg):
        """
            link_site_to_domain site domain
            
            Associate a site to a domain.
        """
        arg = CommandLine(arg)
        if len(arg) != 2:
            self.onecmd('help link_site_to_domain')
            return
        else:
            site_id = pwdb.get_id('site', arg[0])
            domain_id = pwdb.get_id('domain', arg[1])
            pwdb.add_domain_site(domain_id, site_id)

    def do_unlink_site_from_domain(self, arg):
        """
            unlink_site_from_domain site domain
            
            Unassociate a site from a domain.
        """
        arg = CommandLine(arg)
        if len(arg) != 2:
            self.onecmd('help unlink_site_from_domain')
            return
        else:
            site_id = pwdb.get_id('site', arg[0])
            domain_id = pwdb.get_id('domain', arg[1])
            pwdb.unlink_domain_site(domain_id, site_id)

    def do_list_sites_from_domain(self, arg):
        """
            list_sites_from_domain domain

            List all sites associated to the domain.
        """
        arg = CommandLine(arg)
        if len(arg) != 1:
            self.onecmd('help list_sites_from_domain')
            return
        else:
            sg_list = pwdb.list_domain_site()
            for sg in sg_list:
                if sg['domain'] == arg[0]:
                    print '%s' % (sg['site'])

    def do_EOF(self, arg):
        """
            CTRL-D

            Exit this shell.
        """
        return True

    def do_exit(self, arg):
        """
            exit

            Exit this shell.
        """
        return True

# allow identifiers to contain '-'
readline.set_completer_delims('''\n\r\t `~!@#$%^&*()=+[{]}\|;:'",<>/?''')

if __name__ == '__main__':
    import sys
    dbc = DBConsole()
    if len(sys.argv) > 1:
        dbc.onecmd(CommandLine(sys.argv[1:]).encode())
    else:
        dbc.cmdloop()
