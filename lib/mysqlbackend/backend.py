#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 01, 18:44:54 by david
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

import os
import MySQLdb

from sshproxy import backend
from sshproxy.config import get_config, Config, ConfigSection
from sshproxy.util import SSHProxyAuthError

import console

class MySQLConfigSection(ConfigSection):
    section_defaults = {
        'host': 'localhost',
        'user': 'sshproxy',
        'password': 'sshproxypw',
        'db': 'sshproxy',
        'port': 3306,
        }
    types = {
        'port': int,
        }


def Q(str):
    """Safe quote mysql values"""
    if str is None:
        return ''
    return str.replace("'", "\\'")

class MySQLBackend(backend.PasswordDatabase):
    """MySQL Password DataBase connector class"""
    backend_id = 'mysql'

    def __init__(self):
        self.login = None
        Config.register_handler('mysql', MySQLConfigSection)
        cfg = get_config('mysql')
        try:
            self.db = MySQLdb.connect(
                    host=cfg['host'],
                    port=cfg['port'],
                    db=cfg['db'],
                    user=cfg['user'],
                    passwd=cfg['password'])
        except:
            if not os.environ.has_key('SSHPROXY_WIZARD'):
                raise

    def get_console(self):
        return console.DBConsole(self)

    def get_wizard(self):
        from wizard import Wizard
        return Wizard(self)

################## miscellaneous functions ##############################

    def set_login_key(self, key, login=None, force=0):
        if not login:
            login = self.login
        if not login:
            raise SSHProxyAuthError("Missing login and not authenticated")
        if not force and len(self.get_login(login)['key']):
            # Don't overwrite an existing key
            return True
        q_setkey = """
            update login set `key` = '%s' where uid = '%s'
        """
        setkey = self.db.cursor()
        ret = setkey.execute(q_setkey % (Q(key), Q(login)))
        setkey.close()
        return ret

    def is_admin(self, login=None):
        if login is None:
            login = self.login

        q_admin = """
            select 1 from login, login_profile, profile
            where login.uid = '%s'
              and login.id = login_profile.login_id 
              and login_profile.profile_id = profile.id
              and (profile.id = 0 or profile.admin = 1)
        """

        admin = self.db.cursor()
        admin.execute(q_admin % Q(login))
        admin = admin.fetchone()
        if not admin or not len(admin):
            return False
        return True

################## functions for script/add_profile #####################

    def list_profiles(self):
        q_getprofile = """
            select id, name, admin from profile
        """
        profile = self.db.cursor()
        profile.execute(q_getprofile)
        p = []
        for id, name, admin in profile.fetchall():
            p.append({ 'id': id, 'name': name, 'admin': admin })
        profile.close()
        return p

    def get_profile(self, name):
        q_getprofile = """
            select id, name from profile where name = '%s'
        """
        profile = self.db.cursor()
        profile.execute(q_getprofile % Q(name))
        p = profile.fetchone()
        if not p or not len(p):
            return None
        profile.close()
        return { 'id': p[0], 'name': p[1] }

    def add_profile(self, name):
        q_addprofile = """
            insert into profile (name) values ('%s')
        """
        if self.get_profile(name):
            return None
        profile = self.db.cursor()
        profile.execute(q_addprofile % Q(name))
        profile.close()
        return 1

    def _add_profile_id(self, name, id):
        q_addprofile = """
            insert into profile values (%d, '%s', 0)
        """
        if self.get_profile(name):
            return None
        profile = self.db.cursor()
        profile.execute(q_addprofile % (id, Q(name)))
        if id == 0:
            profile.execute("update profile set id=0 where name='%s'"
                                                            % Q(name))
        profile.close()
        return 1

    def remove_profile(self, name):
        q = """
            delete from profile where name = '%s'
        """
        profile_id = self.get_id('profile', name)
        if not profile_id:
            return False
        self.unlink_login_profile(None, profile_id)
        self.unlink_profile_domain(profile_id, None)
        profile = self.db.cursor()
        profile.execute(q % Q(name))
        profile.close()
        return True

################ functions for scripts/add_domain ########################

    def list_domains(self, site=None):
        q_domain = """
            select domain.id,
                   domain.name
                from domain
        """
        if site:
            q_domain = q_domain.strip() + """,
                     domain_site,
                     site
                where site.name = '%s' and
                      site.id = domain_site.site_id and
                      domain_site.domain_id = domain.id""" % Q(site)
        domain = self.db.cursor()
        domain.execute(q_domain)
        p = []
        for id, name in domain.fetchall():
            p.append({ 'id': id, 'name': name })
        domain.close()
        return p

    def get_domain(self, name):
        q_domain = """
            select id, name from domain where name = '%s'
        """
        domain = self.db.cursor()
        domain.execute(q_domain % Q(name))
        p = domain.fetchone()
        if not p or not len(p):
            return None
        domain.close()
        return { 'id': p[0], 'name': p[1] }

    def add_domain(self, name):
        q_domain = """
            insert into domain (name) values ('%s')
        """
        if self.get_domain(name):
            return None
        domain = self.db.cursor()
        domain.execute(q_domain % Q(name))
        domain.close()
        return 1

    def remove_domain(self, name):
        q = """
            delete from domain where name = '%s'
        """
        domain_id = self.get_id('domain', name)
        if not domain_id:
            return False
        self.unlink_profile_domain(None, domain_id)
        self.unlink_domain_site(domain_id, None)
        domain = self.db.cursor()
        domain.execute(q % Q(name))
        domain.close()
        return True

################ functions for scripts/add_site #######################

    def list_sites(self, domain=None):
        q_listsite = """
            select site.id,
                   site.name,
                   site.ip_address,
                   site.port,
                   site.location
                from site
        """
        if domain:
            q_listsite = q_listsite.strip() + """,
                     domain_site,
                     domain
                where domain.name = '%s' and
                      domain_site.domain_id = domain.id and
                      domain_site.site_id = site.id""" % Q(domain)
        site = self.db.cursor()
        site.execute(q_listsite)
        p = []
        for id, name, ip_address, port, location in site.fetchall():
            p.append({ 'id': id,
                       'name': name,
                       'ip': ip_address,
                       'port': port,
                       'location': location })
        site.close()
        return p

    # XXX: rename this method
    def get_site(self, name):
        q_getsite = """
            select id,
                   name,
                   ip_address,
                   port,
                   location
                from site 
                where name = '%s'
        """
        site = self.db.cursor()
        site.execute(q_getsite % Q(name))
        p = site.fetchone()
        if not p or not len(p):
            return None
        site.close()
        return { 'id': p[0],
                 'name': p[1],
                 'ip': p[2],
                 'port': p[3],
                 'location': p[4] }

    def add_site(self, name, ip_address, port, location):
        q_addsite = """
            insert into site (
                    name,
                    ip_address,
                    port,
                    location)
                values ('%s','%s',%d,'%s')
        """
        if self.get_site(name):
            return None
        site = self.db.cursor()
        site.execute(q_addsite % (Q(name), Q(ip_address), port, Q(location)))
        site.close()
        return 1

    def remove_site(self, name):
        q = "delete from site where name = '%s'"
        site_id = self.get_id('site', name)
        if not site_id:
            return False
        for u in self.list_rlogins(site_id):
            self.remove_rlogin(u['uid'], site_id)
        self.unlink_domain_site(None, site_id)
        site = self.db.cursor()
        site.execute(q % Q(name))
        site.close()
        return True

################## functions for scripts/add_rlogin #####################

    def list_rlogins(self, site_id=None):
        q_listrlogin = """
            select site_id, uid, password, priority from rlogin
        """
        if site_id:
            q_listrlogin = q_listrlogin + " where site_id = %d" % site_id
        site = self.db.cursor()
        site.execute(q_listrlogin)
        p = []
        for site_id, uid, password, priority in site.fetchall():
            p.append({ 'uid': uid,
                       'site_id': site_id,
                       'password': password,
                       'priority': priority })
        site.close()
        return p

    def get_rlogins(self, uid, site_id):
        q_getrlogin = """
            select site_id,
                   uid,
                   password,
                   priority
                from rlogin where uid = '%s' and site_id = %d
        """
        if type(site_id) == type(""):
            site_id = self.get_id("site", site_id)
        rlogin = self.db.cursor()
        rlogin.execute(q_getrlogin % (Q(uid), site_id))
        p = rlogin.fetchone()
        if not p or not len(p):
            return None
        rlogin.close()
        return { 'site_id': p[0],
                 'uid': p[1],
                 'password': p[2],
                 'priority': p[3] }

    def add_rlogin_to_site(self, uid, site, password, pkey, priority):
        site_id = self.get_id('site', site)
        if not site_id:
            return False
        return self.add_rlogin(uid, site_id, password, pkey, priority)

    def add_rlogin(self, uid, site_id, password, pkey, priority):
        q_addrlogin = """
            insert into rlogin (
                    uid,
                    site_id,
                    password,
                    pkey,
                    priority)
                values ('%s', %d, '%s', '%s', %d)
        """
        if self.get_rlogins(uid, site_id):
            return None
        rlogin = self.db.cursor()
        rlogin.execute(q_addrlogin % (Q(uid), site_id, Q(password),
                                                       Q(pkey), priority))
        rlogin.close()
        return True

    def set_rlogin_password(self, uid, site, password):
        q_setpassword = """
            update rlogin set `password` = '%s'
                where uid = '%s' and site_id = %d
        """
        site_id = self.get_id('site', site)
        if not site_id:
            return False
        update = self.db.cursor()
        update.execute(q_setpassword % (Q(password), Q(uid), site_id))
        return True

    def get_rlogin_pkey(self, uid, site):
        q_getpkey = """
            select pkey from rlogin
                where uid = '%s' and site_id = %d
        """
        site_id = self.get_id('site', site)
        if not site_id:
            return None
        getpkey = self.db.cursor()
        getpkey.execute(q_getpkey % (Q(uid), site_id))
        pkey = getpkey.fetchone()
        if not pkey or not len(pkey):
            return ''
        return pkey[0]

    def set_rlogin_pkey(self, uid, site, pkey):
        q_setpkey = """
            update rlogin set pkey = '%s'
                where uid = '%s' and site_id = %d
        """
        site_id = self.get_id('site', site)
        if not site_id:
            return False
        update = self.db.cursor()
        update.execute(q_setpkey % (Q(pkey), Q(uid), site_id))
        return True

    def remove_rlogin_from_site(self, uid, site):
        site_id = self.get_id('site', site)
        if not site_id:
            return False
        return self.remove_rlogin(uid, site_id)

    def remove_rlogin(self, uid, site_id):
        q = """
            delete from rlogin where uid = '%s' and site_id = %d
        """
        if type(site_id) == type(""):
            site_id = self.get_id("site", site_id)
        if not self.get_rlogins(uid, site_id):
            return False
        rlogin = self.db.cursor()
        rlogin.execute(q % (Q(uid), site_id))
        rlogin.close()
        return True

################### functions for scripts/add_login   #############

    def list_logins(self):
        q_listlogin = """
            select uid, password, `key` from login
        """
        site = self.db.cursor()
        site.execute(q_listlogin)
        p = []
        for login, password, key in site.fetchall():
            p.append({ 'login': login, 'password': password, 'key': key })
        site.close()
        return p

    def get_login(self, uid):
        q_getlogin = """
            select uid, password, `key` from login where uid = '%s'
        """
        login = self.db.cursor()
        login.execute(q_getlogin % Q(uid))
        p = login.fetchone()
        if not p or not len(p):
            return None
        login.close()
        return { 'login': p[0], 'password': p[1], 'key': p[2] }

    def add_login(self, login, password, key=None):
        q_addlogin = """
            insert into login (uid, `password`, `key`)
                        values ('%s',sha1('%s'),'%s')
        """
        if self.get_login(login):
            return None
        addlogin = self.db.cursor()
        addlogin.execute(q_addlogin % (Q(login), Q(password), Q(key)))
        addlogin.close()
        return True

    def set_login_password(self, uid, password):
        q_setpassword = """
            update login set `password` = sha1('%s') where uid = '%s'
        """
        update = self.db.cursor()
        update.execute(q_setpassword % (Q(password), Q(uid)))
        return True

    def remove_login(self, login):
        q = """
            delete from login where uid = '%s'
        """
        login_id = self.get_id('login', login)
        if not login_id:
            return False
        self.unlink_login_profile(login_id, None)
        removelogin = self.db.cursor()
        removelogin.execute(q % Q(login))
        removelogin.close()
        return True

######### functions for link scripts/add_login_profile ###############

    def list_login_profile(self):
        q_list = """
             select login_id, profile_id from login_profile
        """
        lists = self.db.cursor()
        lists.execute(q_list)
        p = []
        for login_id,profile_id in lists.fetchall():
            profile = self.get_name('profile', profile_id)
            login = self.get_name('login', login_id, name='uid')
            p.append({ 'login': login, 'profile': profile })
        lists.close()
        return p

    def add_login_profile(self, login_id, profile_id):
        q_addlogin = """
            replace into login_profile (login_id, profile_id) values (%d, %d)
        """
        login = self.db.cursor()
        login.execute(q_addlogin % (login_id, profile_id))
        login.close()
        return 1

    def unlink_login_profile(self, login_id, profile_id):
        q = """
            delete from login_profile where 
        """
        q_where = []
        if login_id is not None:
            q_where.append("login_id = %d" % login_id)
        if profile_id is not None:
            q_where.append("profile_id = %d" % profile_id)
        if not len(q_where):
            return False

        login = self.db.cursor()
        login.execute(q + ' and '.join(q_where))
        login.close()
        return True


######### functions for link scripts/add_profile_domain ###############

    def list_profile_domain(self):
        q_list = """
             select profile_id, domain_id from profile_domain
        """
        lists = self.db.cursor()
        lists.execute(q_list)
        p = []
        for profile_id, domain_id in lists.fetchall():
            profile = self.get_name('profile', profile_id)
            domain = self.get_name('domain', domain_id)
            p.append({'profile': profile, 'domain': domain})
        lists.close()
        return p

    def add_profile_domain(self, profile_id, domain_id):
        q_addlogin = """
            replace into profile_domain (profile_id, domain_id) values (%d, %d)
        """
        login = self.db.cursor()
        login.execute(q_addlogin % (profile_id, domain_id))
        login.close()
        return 1

    def unlink_profile_domain(self, profile_id, domain_id):
        q = """
            delete from profile_domain where 
        """
        q_where = []
        if profile_id is not None:
            q_where.append("profile_id = %d" % profile_id)
        if domain_id is not None:
            q_where.append("domain_id = %d" % domain_id)
        if not len(q_where):
            return False
        login = self.db.cursor()
        login.execute(q + ' and '.join(q_where))
        login.close()
        return True


######### functions for link scripts/add_domain_site ###############

    def list_domain_site(self):
        q_list = """
             select domain_id, site_id from domain_site
        """
        lists = self.db.cursor()
        lists.execute(q_list)
        p = []
        for domain_id, site_id in lists.fetchall():
            domain = self.get_name('domain', domain_id)
            site = self.get_name('site', site_id)
            p.append({'domain': domain, 'site': site})
        lists.close()
        return p

    def add_domain_site(self, domain_id, site_id):
        q_addlogin = """
            replace into domain_site (domain_id, site_id) values (%d, %d)
        """
        login = self.db.cursor()
        login.execute(q_addlogin % (domain_id, site_id))
        login.close()
        return 1

    def unlink_domain_site(self, domain_id, site_id):
        q = """
            delete from domain_site where 
        """
        q_where = []
        if domain_id is not None:
            q_where.append("domain_id = %d" % domain_id)
        if site_id is not None:
            q_where.append("site_id = %d" % site_id)
        if not len(q_where):
            return False

        login = self.db.cursor()
        login.execute(q + ' and '.join(q_where))
        login.close()
        return True

######################################################################

    def get_name(self, table, id, name='name'):
        query = """
        select %s from `%s` where id = '%d'
        """
        c= self.db.cursor()
        c.execute(query % (name, Q(table), int(id)))
        name = c.fetchone()
        c.close()
        if name:
            return name[0]
        else:
            return None


    def get_id(self, table, name):
        id = None
        if table == 'login':
            query = """
            select id from `%s` where uid = '%s' 
            """
        else:
            query = """
            select id from `%s` where name = '%s' 
            """
        c = self.db.cursor()
        c.execute(query % (Q(table), Q(name)))
        id = c.fetchone()
        c.close()
        if id and len(id):
            return id[0]
        else:
            return 0

    def is_allowed(self, username, password=None, key=None):
        """Check is a user is allowed to connect to the proxy."""
        if password is None and key is None:
            return None
        if key is None:
            q_access = """
                select 1 from login
                    where uid = '%s' and `password` = sha1('%s')
            """ % (Q(username), Q(password))
        else:
            q_access = """
                select 1 from login where uid = '%s' and `key` = '%s'
            """ % (Q(username), Q(key))
        logins = self.db.cursor()
        logins.execute(q_access)
        try:
            login = logins.fetchone()[0]
        except TypeError:
            return None
        logins.close()
        if login:
            self.login = username
        return login

    def get_rlogin_site(self, site_id):
        rlogin = None
        if site_id.find('@') >= 0:
            rlogin, sid = site_id.split('@')
        else:
            sid = site_id
        rlogins = self.db.cursor()
        if not rlogin:
            q_rlogin = """
            select uid
                from site, rlogin
                where site.id = rlogin.site_id and site.name = '%s'
                order by priority desc            
            """
            rlogins.execute(q_rlogin % Q(sid))
        else:
            q_rlogin = """
            select uid
                from site, rlogin
                where site.id = rlogin.site_id and site.name = '%s'
                  and rlogin.uid = '%s'
                order by priority desc            
            """

            rlogins.execute(q_rlogin % (Q(sid), rlogin))
        rlogin = rlogins.fetchone()
        if not rlogin or not len(rlogin):
            raise SSHProxyAuthError("No such rlogin: %s" % site_id)
        while rlogin:
            # try all rlogins until we find one that we can connect to
            rlogin = rlogin[0]
            if self.can_connect(rlogin, sid):
                break
            rlogin = rlogins.fetchone()
            if self.login and not rlogin:
                raise SSHProxyAuthError("User %s is not allowed to connect "
                                        "to %s@%s" % (self.login, rlogin, sid))

        rlogins.close()
        q_sites = """
            select id, name, ip_address, port, location
                from site
                where site.name = '%s'
                order by name limit 1
            """
        q_rlogins = """
            select id, site_id, uid, password, pkey, priority
                from rlogin where site_id = %d
            """
        sites = self.db.cursor()
        sites.execute(q_sites % Q(sid))
        id, name, ip_address, port, location = sites.fetchone()
        rlogin_list = []
        rlogins = self.db.cursor()
        rlogins.execute(q_rlogins % id)
        for id, site_id, uid, password, pkey, priority in rlogins.fetchall():
            rlogin_list.append(backend.UserEntry(
                                        uid=uid,
                                        password=password,
                                        pkey=pkey,
                                        priority=priority))
        site = backend.SiteEntry(sid=name,
                                ip_address=ip_address,
                                port=port,
                                location=location,
                                rlogin_list=rlogin_list)

        return rlogin, site

    def can_connect(self, rlogin, site):
        q_domain = """
        select count(*) 
        from
            login,
            login_profile,
            profile,
            profile_domain,
            domain,
            domain_site,
            domain_rlogin,
            site,
            rlogin 
        where login.uid = '%s' 
          and login.id = login_profile.login_id 
          and login_profile.profile_id = profile.id 
          and profile.id = profile_domain.profile_id 
          and profile_domain.domain_id = domain.id
          and ((domain.id = domain_site.domain_id
                and domain_site.site_id = site.id)
           or (domain.id = domain_rlogin.domain_id
                and domain_rlogin.rlogin_id = rlogin.id))
          and site.name = '%s'
          and rlogin.site_id = site.id
          and rlogin.uid = '%s'  
        """
        link = self.db.cursor()
        link.execute(q_domain % (Q(self.login), Q(site), Q(rlogin)))
        gr = link.fetchone()[0]
        link.close()
        return gr

    def list_allowed_sites(self, domain=None, login=None):
        q_domain = """
        select site.id,
               site.name,
               site.ip_address,
               site.port,
               site.location,
               rlogin.uid
        from
            login,
            login_profile,
            profile,
            profile_domain,
            domain,
            domain_site,
            domain_rlogin,
            site,
            rlogin 
        where login.uid = '%s' 
          and login.id = login_profile.login_id 
          and login_profile.profile_id = profile.id 
          and profile.id = profile_domain.profile_id 
          and profile_domain.domain_id = domain.id
          and ((domain.id = domain_site.domain_id
                and domain_site.site_id = site.id)
           or (domain.id = domain_rlogin.domain_id
                and domain_rlogin.rlogin_id = rlogin.id))
          and rlogin.site_id = site.id
        """
        if domain:
            q_domain += """ and domain.name = '%s'""" % Q(domain)
        q_domain += """ group by rlogin.uid, site.name"""
        if not login:
            login = self.login
        sites = self.db.cursor()
        sites.execute(q_domain % (Q(login)))
        p = []
        for id, name, ip_address, port, location, uid in sites.fetchall():
            p.append({ 'id': id,
                       'name': name,
                       'ip': ip_address,
                       'port': port,
                       'location': location,
                       'uid': uid })
        sites.close()
        return p

#if get_config('sshproxy')['pwdb_backend'] == 'mysql':
#    MySQLBackend.register_backend()
MySQLBackend.register_backend()
