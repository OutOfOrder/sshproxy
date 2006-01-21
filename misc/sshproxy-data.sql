--
-- Dumping data for table `login`
--


/*!40000 ALTER TABLE `login` DISABLE KEYS */;
LOCK TABLES `login` WRITE;
INSERT INTO `login` VALUES (1,'admin','foobar','');
UNLOCK TABLES;
/*!40000 ALTER TABLE `login` ENABLE KEYS */;

--
-- Dumping data for table `login_profile`
--


/*!40000 ALTER TABLE `login_profile` DISABLE KEYS */;
LOCK TABLES `login_profile` WRITE;
INSERT INTO `login_profile` VALUES (1,0);
UNLOCK TABLES;
/*!40000 ALTER TABLE `login_profile` ENABLE KEYS */;

--
-- Dumping data for table `profile`
--


/*!40000 ALTER TABLE `profile` DISABLE KEYS */;
LOCK TABLES `profile` WRITE;
INSERT INTO `profile` VALUES (0,'pwdb_admin',1);
UNLOCK TABLES;
/*!40000 ALTER TABLE `profile` ENABLE KEYS */;

--
-- Dumping data for table `profile_sgroup`
--


/*!40000 ALTER TABLE `profile_sgroup` DISABLE KEYS */;
LOCK TABLES `profile_sgroup` WRITE;
INSERT INTO `profile_sgroup` VALUES (0,0);
UNLOCK TABLES;
/*!40000 ALTER TABLE `profile_sgroup` ENABLE KEYS */;

--
-- Dumping data for table `sgroup`
--


/*!40000 ALTER TABLE `sgroup` DISABLE KEYS */;
LOCK TABLES `sgroup` WRITE;
INSERT INTO `sgroup` VALUES (0,'AllSites');
UNLOCK TABLES;
/*!40000 ALTER TABLE `sgroup` ENABLE KEYS */;

