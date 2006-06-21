#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jun 22, 01:08:31 by david
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
    db_schema = """
-- MySQL dump 10.9
--
-- Host: localhost    Database: spy
-- ------------------------------------------------------
-- Server version	4.1.14-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `domain`
--

DROP TABLE IF EXISTS `domain`;
CREATE TABLE `domain` (
  `id` int(10) unsigned NOT NULL auto_increment,
  `name` varchar(255) NOT NULL default '',
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

--
-- Table structure for table `domain_rlogin`
--

DROP TABLE IF EXISTS `domain_rlogin`;
CREATE TABLE `domain_rlogin` (
  `domain_id` int(10) unsigned NOT NULL default '0',
  `rlogin_id` int(10) unsigned NOT NULL default '0',
  PRIMARY KEY  (`domain_id`,`rlogin_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

--
-- Table structure for table `domain_site`
--

DROP TABLE IF EXISTS `domain_site`;
CREATE TABLE `domain_site` (
  `domain_id` int(10) unsigned NOT NULL default '0',
  `site_id` int(10) unsigned NOT NULL default '0',
  PRIMARY KEY  (`domain_id`,`site_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

--
-- Table structure for table `login`
--

DROP TABLE IF EXISTS `login`;
CREATE TABLE `login` (
  `id` mediumint(10) unsigned NOT NULL auto_increment,
  `uid` varchar(255) NOT NULL default '',
  `password` varchar(255) NOT NULL default '',
  `key` text NOT NULL,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

--
-- Table structure for table `login_profile`
--

DROP TABLE IF EXISTS `login_profile`;
CREATE TABLE `login_profile` (
  `login_id` int(10) unsigned NOT NULL default '0',
  `profile_id` int(10) unsigned NOT NULL default '0',
  PRIMARY KEY  (`login_id`,`profile_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

--
-- Table structure for table `profile`
--

DROP TABLE IF EXISTS `profile`;
CREATE TABLE `profile` (
  `id` int(10) unsigned NOT NULL auto_increment,
  `name` varchar(255) NOT NULL default '',
  `admin` int(10) unsigned NOT NULL default '0',
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

--
-- Table structure for table `profile_domain`
--

DROP TABLE IF EXISTS `profile_domain`;
CREATE TABLE `profile_domain` (
  `profile_id` int(10) unsigned NOT NULL default '0',
  `domain_id` int(10) unsigned NOT NULL default '0',
  PRIMARY KEY  (`profile_id`,`domain_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

--
-- Table structure for table `rlogin`
--

DROP TABLE IF EXISTS `rlogin`;
CREATE TABLE `rlogin` (
  `id` int(10) unsigned NOT NULL auto_increment,
  `site_id` int(10) unsigned NOT NULL default '0',
  `uid` varchar(255) NOT NULL default '',
  `password` varchar(255) NOT NULL default '',
  `priority` tinyint(1) unsigned NOT NULL default '0',
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

--
-- Table structure for table `site`
--

DROP TABLE IF EXISTS `site`;
CREATE TABLE `site` (
  `id` int(10) unsigned NOT NULL auto_increment,
  `name` varchar(255) NOT NULL default '',
  `ip_address` varchar(255) NOT NULL default '',
  `port` int(5) unsigned NOT NULL default '22',
  `location` text NOT NULL,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

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
        
        try:
            # create tables
            c.execute(self.db_schema)
        except MySQLError, e:
            handle_mysql_error(e)


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


    def handle_mysql_error(self, e, can_cont=False):
        code, msg = e
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
    
