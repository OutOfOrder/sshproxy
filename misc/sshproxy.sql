-- MySQL dump 10.10
--
-- Host: localhost    Database: sshproxy
-- ------------------------------------------------------
-- Server version	5.0.16-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

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
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COMMENT='login profil link';

--
-- Table structure for table `profile`
--

DROP TABLE IF EXISTS `profile`;
CREATE TABLE `profile` (
  `id` int(10) unsigned NOT NULL auto_increment,
  `name` varchar(255) NOT NULL default '',
  `admin` tinyint(1) NOT NULL,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COMMENT='User groups';

--
-- Table structure for table `profile_sgroup`
--

DROP TABLE IF EXISTS `profile_sgroup`;
CREATE TABLE `profile_sgroup` (
  `profile_id` int(10) unsigned NOT NULL default '0',
  `sgroup_id` int(10) unsigned NOT NULL default '0',
  PRIMARY KEY  (`profile_id`,`sgroup_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COMMENT='profile sitegroup link';

--
-- Table structure for table `sgroup`
--

DROP TABLE IF EXISTS `sgroup`;
CREATE TABLE `sgroup` (
  `id` int(10) unsigned NOT NULL auto_increment,
  `name` varchar(255) NOT NULL default '',
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COMMENT='Site groups';

--
-- Table structure for table `sgroup_site`
--

DROP TABLE IF EXISTS `sgroup_site`;
CREATE TABLE `sgroup_site` (
  `sgroup_id` int(10) unsigned NOT NULL default '0',
  `site_id` int(10) unsigned NOT NULL default '0',
  PRIMARY KEY  (`sgroup_id`,`site_id`)
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

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` int(10) unsigned NOT NULL auto_increment,
  `site_id` int(10) unsigned NOT NULL default '0',
  `uid` varchar(255) NOT NULL default '',
  `password` varchar(255) NOT NULL default '',
  `primary` tinyint(1) unsigned NOT NULL default '0',
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;


/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

