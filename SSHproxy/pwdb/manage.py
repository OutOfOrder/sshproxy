#!/usr/bin/python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005 David Guerizec <david@guerizec.net>
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
from pprint import pprint as pp
import readline
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
        self.prompt = '[pwdb manager] '

    def emptyline(self):
        return

    def do_select_site(self, arg):
        """select_site [sitename]"""
        arg = CommandLine(arg)
        if not len(arg):
            self.onecmd('help select_site')
            return
        self.current_site = arg[0]
        self.set_prompt()

    def set_prompt(self):
        self.prompt = 'site: %s\n> ' % self.current_site

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

    def _complete_groups(self, text, line, begidx, endidx):
        groups = self._groups()
        w = len(text)
        l = []
        for id, name in groups:
            if w > len(name):
                continue
            if text == name[:w]:
                l.append(name+' ')
        return l

    def complete_list_users(self, text, line, begidx, endidx):
        return self._complete_sites(text, line, begidx, endidx)

    def complete_select_site(self, text, line, begidx, endidx):
        return self._complete_sites(text, line, begidx, endidx)

    def complete_list_groups(self, text, line, begidx, endidx):
        return self._complete_sites(text, line, begidx, endidx)

    def complete_list_sites(self, text, line, begidx, endidx):
        return self._complete_groups(text, line, begidx, endidx)


############################### sites ##################################

    def do_add_site(self, arg):
        """add_site [name] [IP address] [port] [location]"""
        arg = CommandLine(arg)
        if len(arg) != 4:
            self.onecmd('help add_site')
            return
        else:
            pwdb.add_site(arg[0], arg[1], int(arg[2]), arg[3])

    def _sites(self, group=None):
        sites=[]
        for site in pwdb.list_sites(group=group):
            sites.append((site['name'], site['ip'], site['location']))
        sites.sort(lambda x,y: x[0] < y[0])
        return sites

    def do_list_sites(self, arg):
        """list_sites"""
        arg = CommandLine(arg)
        group = None
        if len(arg):
            group = arg[0]
        sites = self._sites(group=group)
        if len(sites):
            name_width = max([ len(e[0]) for e in sites ])
            ip_width = max([ len(e[1]) for e in sites ])
            #loc_width = max([ len(e[2]) for e in sites ])
            for name, ip, loc in sites:
                print name + ' '*(name_width - len(name)), \
                        ip + ' '*(ip_width - len(ip)), loc
        print len(sites), 'sites in the database'


################################ users ##################################

    def set_password(self, user):
        pass1 = ""
        pass2 = " "
        print 'Setting password for user %s' % user
        try:
            while (pass1 != pass2):
                pass1 = getpass.getpass("Enter new password: ")
                pass2 = getpass.getpass("Confirm password: ")
        except EOFError:
            print 'Abort'
            return
        print 'Password set for user %s' % user
        return pass1

    def do_add_user(self, arg):
        """add_user [uid] [site] [primary]"""
        arg = CommandLine (arg)
        if (len(arg) != 3):
            self.onecmd('help add_user')
            return
        else:
            try:
                pass1 = self.set_password(arg[0])
                pwdb.add_user_to_site(arg[0], arg[1], pass1, int(arg[2]))
            except KeyboardInterrupt:
                return


    def do_list_users(self, arg):
        """list_users [sitename]"""
        arg = CommandLine(arg)
        if not len(arg):
            if not self.current_site:
                self.onecmd('help list_users')
                return
            site = self.current_site
        else:
            site = arg[0]

        res = pwdb.get_site_for_script(site)
        if res:
            site_id = res['id']
        else:
            self.onecmd('help list_users')
            return
 
        users=[]
        for user in pwdb.list_users(site_id=site_id):
            users.append((user['uid'], user['password']))
        users.sort(lambda x,y: x[0]<y[0])
        if len(users):
            uid_width = max([ len(e[0]) for e in users ])
        else:
            print 'No users for site %s' % site
            return
        for uid, passwd in users:
            print uid + ' '*(uid_width - len(uid)), passwd


############################### login ##################################

    def do_add_login(self, arg):
        """add_login [uid] [key]"""
        arg = CommandLine (arg)
        if len (arg) != 2:
            self.onecmd('help add_login')
            return
        else:
            pass1 = self.set_password(arg[0])
            pwdb.add_login (arg[0], arg[1], pass1)

    def do_list_logins(self,arg):
        """list_logins"""
        lg_list = pwdb.list_logins()
        for lg in lg_list :
            print 'uid: %s passwd: %s key: %s' % (lg['login'], lg['password'], lg['key'])


############################## login_profile ###########################

    def do_add_login_to_profile(self, arg):
        """add_login_to_profile [login] [profile]"""
        arg = CommandLine(arg)
        if len (arg) != 2:
            self.onecmd('help add_login_to_profile')
            return
        else:
            login_id = pwdb.get_id('login', arg[0])
            profile_id = pwdb.get_id('profile', arg[1])
            pwdb.add_login_profile(login_id, profile_id)

    def do_list_login_profile(self, arg):
        """list_login_profile [profile]"""
        arg = CommandLine(arg)
        if len(arg) != 1:
            self.onecmd('help list_login_profile')
            return
        else:
            lp_list = pwdb.list_login_profile()
            for lp in lp_list:
                if lp['profile'] == arg[0]:
                    print '%s' % (lp['login'])


############################## profile #################################

    def do_add_profile(self, arg):
        """add_profile [profile] [profile] ..."""
        arg = CommandLine (arg)
        if len(arg) < 1:
            self.onecmd('help add_profile')
            return
        else:
            for name in arg:
                pwdb.add_profile(name)

    # FIXME: sort profile list
    def do_list_profiles(self,args):
        """list existing profiles"""
        p_list = pwdb.list_profiles()
        def sort_list(x,y):
            print x , y
            return x['id'] < y['id']
        #p_list.sort(sort_list)
        for pl in p_list:
            print 'id = %d, name = %s' % (pl['id'], pl['name'])

############################### profile_sgroup #########################

    def do_add_profile_to_group(self, arg):
        """add_profile_to_group [profile] [group]"""
        arg = CommandLine(arg)
        if len (arg) != 2:
            self.onecmd('help add_profile_to_group')
            return
        else:
            profile_id = pwdb.get_id('profile', arg[0])
            sgroup_id = pwdb.get_id('sgroup', arg[1])
            pwdb.add_profile_group(profile_id, sgroup_id)

    def do_list_profile_group(self, arg):
        """list existing links between profile and group tables"""
        pg_list = pwdb.list_profile_group()
        for pg in pg_list:
            print 'profile = %s, group = %s' % (pg['prof'], pg['sgroup'])

############################### groups #################################

    def do_add_group(self, arg):
        """add_group [group1] [group2] ..."""
        arg = CommandLine (arg)
        if len (arg) < 1:
            self.onecmd('help add_group')
            return
        else:
            for name in arg[:]:
                pwdb.add_group(name)

    def _groups(self, site=None):
        groups = pwdb.list_groups(site=site)
        group = []
        for g in groups:
            group.append((g['id'], g['name']))
        group.sort(lambda x,y: x[1] < y[1])
        return group

    def do_list_groups(self, arg):
        """list_groups [site]"""
        arg = CommandLine(arg)
        if len(arg) != 1:
            site = self.current_site
        else:
            site = arg[0]
        groups = self._groups(site=site)
        for id, name in groups:
            print name


############################# site_group ###############################

    def do_add_site_to_group(self, arg):
        """add_site_to_group [site] [group]"""
        arg = CommandLine(arg)
        if len(arg) != 2:
            self.onecmd('help add_site_to_group')
            return
        else:
            site_id = pwdb.get_id('site', arg[0])
            group_id = pwdb.get_id('sgroup', arg[1])
            pwdb.add_group_site(group_id, site_id)

    def do_list_sites_from_group(self, arg):
        """list_sites_from_group [group]"""
        arg = CommandLine(arg)
        if len(arg) != 1:
            self.onecmd('help list_sites_from_group')
            return
        else:
            sg_list = pwdb.list_group_site()
            for sg in sg_list:
                if sg['sgroup'] == arg[0]:
                    print '%s' % (sg['site'])

############################## misc #####################################

    
    def do_EOF(self, arg):
        print
        return True

    def do_exit(self, arg):
        return True

    def completenames(self, text, *ignored):
        dotext = 'do_'+text
        return [a[3:]+' ' for a in self.get_names() if a.startswith(dotext)]



# allow identifiers to contain -
readline.set_completer_delims('''\n\r\t `~!@#$%^&*()=+[{]}\|;:'",<>/?''')

if __name__ == '__main__':
    import sys
    dbc = DBConsole()
    if len(sys.argv) > 1:
        dbc.onecmd(CommandLine(sys.argv[1:]).encode())
    else:
        dbc.cmdloop()
