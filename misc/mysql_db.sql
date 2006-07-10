DROP TABLE IF EXISTS `aclrules`;
CREATE TABLE IF NOT EXISTS `aclrules` (
  `name` varchar(255) NOT NULL default '',
  `weight` tinyint(4) NOT NULL default '0',
  `rule` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;


DROP TABLE IF EXISTS `acltags`;
CREATE TABLE IF NOT EXISTS `acltags` (
  `object` varchar(15) NOT NULL default '',
  `id` int(10) NOT NULL default '0',
  `tag` varchar(255) NOT NULL default '',
  `value` text NOT NULL,
  PRIMARY KEY  (`object`,`id`,`tag`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;


DROP TABLE IF EXISTS `client`;
CREATE TABLE IF NOT EXISTS `client` (
  `id` int(10) unsigned NOT NULL auto_increment,
  `uid` varchar(255) NOT NULL default '',
  `password` varchar(255) NOT NULL default '',
  PRIMARY KEY  (`id`),
  UNIQUE KEY `uid` (`uid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;


DROP TABLE IF EXISTS `login`;
CREATE TABLE IF NOT EXISTS `login` (
  `id` int(10) unsigned NOT NULL auto_increment,
  `site_id` int(10) unsigned NOT NULL default '0',
  `login` varchar(255) NOT NULL default '',
  `password` varchar(255) NOT NULL default '',
  `pkey` text NOT NULL,
  `priority` tinyint(1) unsigned NOT NULL default '0',
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;


DROP TABLE IF EXISTS `site`;
CREATE TABLE IF NOT EXISTS `site` (
  `id` int(10) unsigned NOT NULL auto_increment,
  `name` varchar(255) NOT NULL default '',
  `ip_address` varchar(255) NOT NULL default '',
  `port` int(5) unsigned NOT NULL default '22',
  `location` text NOT NULL,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
