#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 22, 10:07:55 by david
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

import sys, getpass

import MySQLdb
from MySQLdb import MySQLError
from MySQLdb.constants import CLIENT

from sshproxy.config import get_config
from backend import Q

class Wizard(object):
    db_schema = {}
    db_schema['domain'] = """
        CREATE TABLE domain (
            id int(10) unsigned NOT NULL auto_increment,
            name varchar(255) NOT NULL default '',
            PRIMARY KEY (id)
        ) ENGINE=MyISAM;
    """

    db_schema['domain_rlogin'] = """
        CREATE TABLE domain_rlogin (
            domain_id int(10) unsigned NOT NULL default '0',
            rlogin_id int(10) unsigned NOT NULL default '0',
            PRIMARY KEY (domain_id,rlogin_id)
        ) ENGINE=MyISAM;
    """

    db_schema['domain_site'] = """
        CREATE TABLE domain_site (
            domain_id int(10) unsigned NOT NULL default '0',
            site_id int(10) unsigned NOT NULL default '0',
            PRIMARY KEY (domain_id,site_id)
        ) ENGINE=MyISAM;
    """

    db_schema['login'] = """
        CREATE TABLE login (
            id mediumint(10) unsigned NOT NULL auto_increment,
            uid varchar(255) NOT NULL default '',
            password varchar(255) NOT NULL default '',
            `key` text NOT NULL,
            PRIMARY KEY (id)
        ) ENGINE=MyISAM;
    """

    db_schema['login_profile'] = """
        CREATE TABLE login_profile (
            login_id int(10) unsigned NOT NULL default '0',
            profile_id int(10) unsigned NOT NULL default '0',
            PRIMARY KEY (login_id,profile_id)
        ) ENGINE=MyISAM;
    """

    db_schema['profile'] = """
        CREATE TABLE profile (
            id int(10) unsigned NOT NULL auto_increment,
            name varchar(255) NOT NULL default '',
            admin int(10) unsigned NOT NULL default '0',
            PRIMARY KEY (id)
        ) ENGINE=MyISAM;
    """

    db_schema['profile_domain'] = """
        CREATE TABLE profile_domain (
            profile_id int(10) unsigned NOT NULL default '0',
            domain_id int(10) unsigned NOT NULL default '0',
            PRIMARY KEY (profile_id,domain_id)
        ) ENGINE=MyISAM;
    """

    db_schema['rlogin'] = """
        CREATE TABLE rlogin (
            id int(10) unsigned NOT NULL auto_increment,
            site_id int(10) unsigned NOT NULL default '0',
            uid varchar(255) NOT NULL default '',
            password varchar(255) NOT NULL default '',
            priority tinyint(1) unsigned NOT NULL default '0',
            PRIMARY KEY (id)
        ) ENGINE=MyISAM;
    """

    db_schema['site'] = """
        CREATE TABLE site (
            id int(10) unsigned NOT NULL auto_increment,
            name varchar(255) NOT NULL default '',
            ip_address varchar(255) NOT NULL default '',
            port int(5) unsigned NOT NULL default '22',
            location text NOT NULL,
            PRIMARY KEY (id)
        ) ENGINE=MyISAM;
    """

    def __init__(self, mysql):
        self.mysql = mysql
        
    def run(self):
        self.adminid="root"
        adminpw=""
        self.cfg = cfg = get_config('mysql')
        cfg['host'] = (raw_input("SSHproxy database hostname [%s]: "
                        % cfg['host']) or cfg['host'])
        cfg['port'] = (raw_input("SSHproxy database port [%s]: "
                        % cfg['port']) or cfg['port'])
        cfg['db'] = (raw_input("SSHproxy database name [%s]: "
                        % cfg['db']) or cfg['db'])
        cfg['user'] = (raw_input("SSHproxy database user [%s]: "
                        % cfg['user']) or cfg['user'])
        cfg['password'] = (raw_input("SSHproxy database password [%s]: "
                        % cfg['password']) or cfg['password'])


        cfg.write()

        db = None
        while not db:
            self.adminid = raw_input("MySQL administration user [%s]: "
                            % self.adminid) or self.adminid
            adminpw = getpass.getpass("MySQL administration password: ")
        
            db = self.connect_to_db(cfg['host'], cfg['port'], "",
                                    self.adminid, adminpw)

        self.dbc = db.cursor()

        self.create_database()

        self.create_dbuser()

        self.dbc.close()
        db.close()

        # reconnect as sshproxy user
        db = self.connect_to_db(cfg['host'], cfg['port'], cfg['db'],
                                cfg['user'], cfg['password'])

        if not db:
            print "There was an unexpected error."
            print "Please contact the maintainer on sshproxy-dev@penguin.fr"
            sys.exit(1)

        self.mysql.db = db
        self.dbc = db.cursor()


        self.add_admin()

        self.add_first_site()

        self.dbc.close()
        db.close()



    def create_database(self):
        print 'create database'
        cfg = self.cfg
        c = self.dbc
        while True:
            try:
                c.execute("create database %s" % Q(cfg['db']))
                break
            except MySQLError, e:
                self.handle_mysql_error(e, can_cont=True)
                try:
                    c.execute("drop database %s" % Q(cfg['db']))
                except MySQLError, e:
                    self.handle_mysql_error(e)
                    break

        try:
            c.execute("use %s" % Q(cfg['db']))
        except MySQLError, e:
            self.handle_mysql_error(e)
        
        for table, statmt in self.db_schema.items():
            try:
                # create table
                c.execute(statmt)
            except MySQLError, e:
                self.handle_mysql_error(e, table_name=table)


    def create_dbuser(self):
        cfg = self.cfg
        c = self.dbc
        selfip = 'localhost'
        selfip = raw_input("Enter the IP of the host connecting to the "
                            "database (* for any) [%s] " % selfip) or selfip
        try:
            # create the sshproxy user
            if cfg['user'] != self.adminid:
                c.execute("GRANT USAGE ON * . * TO '%s'@'%s' "
                        "IDENTIFIED BY '%s' WITH "
                        "MAX_QUERIES_PER_HOUR 0 MAX_CONNECTIONS_PER_HOUR 0 "
                        "MAX_UPDATES_PER_HOUR 0" % (Q(cfg['user']), Q(selfip),
                                                    Q(cfg['password'])))
            c.execute("GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, "
                    "INDEX, ALTER, CREATE TEMPORARY TABLES ON `%s` . * TO "
                    "'%s'@'%s'" % (Q(cfg['db']), Q(cfg['user']), Q(selfip)))
        except MySQLError, e:
            raise
            self.handle_mysql_error(e)

    def add_admin(self):
        cfg = self.cfg
        c = self.dbc
        adminid = 'admin'
        adminpw = ''
        
        adminid = raw_input("Enter the admin uid [%s] " % adminid) or adminid
        
        while not adminpw:
            adminpw1 = getpass.getpass("Enter the admin password ")
            adminpw2 = getpass.getpass("Confirm the admin password ")
            if adminpw1 == adminpw2:
                adminpw = adminpw1
                if not adminpw:
                    print "Empty passwords are not allowed"
            else:
                print "Passwords don't match"

        admingrp = 'Administrators'
        admingrp = raw_input("Enter the admin profile name [%s] "
                                        % admingrp) or admingrp

        self.mysql._add_profile_id(admingrp, id=0)
        self.mysql.add_login(adminid, adminpw, 'no key')
        self.mysql.add_login_profile(self.mysql.get_id('login', adminid), 0)


    def add_first_site(self):
        pass

    def connect_to_db(self, host, port, db, user, password):
        try:
            return MySQLdb.connect(
                host=host,
                port=port,
                db=db,
                user=user,
                passwd=password,
                client_flag=CLIENT.MULTI_STATEMENTS
                )
        except MySQLError, e:
            self.handle_mysql_error(e, can_cont=True)
            return None


    def handle_mysql_error(self, e, can_cont=False, table_name=None):
        code, msg = e
        if table_name:
            msg = '%s (table: %s)' % (msg, table_name)
        cont = False
        if 0:
            pass
        elif code == 1007: # database already exists
            print msg
            while can_cont:
                a = raw_input("Do you want to delete the old database ? "
                                                                "(yes/no)")
                if a == 'yes':
                    cont = True
                    break
                elif a == 'no':
                    break
        elif code == 1044: # access denied or unknown user
            print msg
        elif code == 1045: # incorrect password
            print msg
        elif code == 1049: # unknown database
            print msg
        elif code == 2003: # can't connect (long timeout)
            print msg
        elif code == 2005: # unknown host
            print msg
        else:
            print code, msg
        if not cont:
            if can_cont:
                while True:
                    a = raw_input("Do you want to continue nevertheless ? "
                                                                    "(yes/no)")
                    if a == 'yes':
                        cont = True
                        break
                    elif a == 'no':
                        break
            if not cont:
                print "Exiting..."
                sys.exit(1)

        print "Continuing..."
    
