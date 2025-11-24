CREATE DATABASE  IF NOT EXISTS `mydb` /*!40100 DEFAULT CHARACTER SET utf8mb3 */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `mydb`;
-- MySQL dump 10.13  Distrib 8.0.44, for Win64 (x86_64)
--
-- Host: localhost    Database: mydb
-- ------------------------------------------------------
-- Server version	9.4.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `клієнти_3фн`
--

DROP TABLE IF EXISTS `клієнти_3фн`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `клієнти_3фн` (
  `id_клієнта` int unsigned NOT NULL AUTO_INCREMENT,
  `Клієнт` varchar(45) NOT NULL,
  `Адреса_клієнта` varchar(45) NOT NULL,
  PRIMARY KEY (`id_клієнта`),
  UNIQUE KEY `id_клієнта_UNIQUE` (`id_клієнта`),
  UNIQUE KEY `Клієнт_UNIQUE` (`Клієнт`)
) ENGINE=InnoDB AUTO_INCREMENT=1003 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `клієнти_3фн`
--

LOCK TABLES `клієнти_3фн` WRITE;
/*!40000 ALTER TABLE `клієнти_3фн` DISABLE KEYS */;
INSERT INTO `клієнти_3фн` VALUES (1000,'Мельник','Хрещатик 1'),(1001,'Шевченко','Басейна 2'),(1002,'Коваленко','Комп\'ютерна 3');
/*!40000 ALTER TABLE `клієнти_3фн` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `не_нормована`
--

DROP TABLE IF EXISTS `не_нормована`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `не_нормована` (
  `номер_замовлення` int NOT NULL AUTO_INCREMENT,
  `Назва_товару_кількість` varchar(45) NOT NULL,
  `Адреса_клієнта` varchar(45) NOT NULL,
  `Дата_замовлення` date NOT NULL,
  `Клієнт` varchar(45) NOT NULL,
  PRIMARY KEY (`номер_замовлення`)
) ENGINE=InnoDB AUTO_INCREMENT=104 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `не_нормована`
--

LOCK TABLES `не_нормована` WRITE;
/*!40000 ALTER TABLE `не_нормована` DISABLE KEYS */;
INSERT INTO `не_нормована` VALUES (101,'Лептоп: 3, Мишка: 2','Хрещатик 1','2023-03-15','Мельник'),(102,'Принтер: 1','Басейна 2','2023-03-16','Шевченко'),(103,'Мишка: 4','Комп\'ютерна 3','2023-03-17','Коваленко');
/*!40000 ALTER TABLE `не_нормована` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `перша_форма_нормалізації`
--

DROP TABLE IF EXISTS `перша_форма_нормалізації`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `перша_форма_нормалізації` (
  `Нопер_замовлення` int NOT NULL AUTO_INCREMENT,
  `Назва_товару` varchar(45) NOT NULL,
  `Кількість_товару` int unsigned NOT NULL,
  `Адреса_клієнта` varchar(45) NOT NULL,
  `Дата_замовлення` date NOT NULL,
  `Клієнт` varchar(45) NOT NULL,
  PRIMARY KEY (`Нопер_замовлення`,`Назва_товару`)
) ENGINE=InnoDB AUTO_INCREMENT=104 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `перша_форма_нормалізації`
--

LOCK TABLES `перша_форма_нормалізації` WRITE;
/*!40000 ALTER TABLE `перша_форма_нормалізації` DISABLE KEYS */;
INSERT INTO `перша_форма_нормалізації` VALUES (101,'Лептоп',3,'Хрещатик 1','2023-03-15','Мельник'),(101,'Мишка',2,'Хрещатик 1','2023-03-15','Мельник'),(102,'Принтер',1,'Басейна 2','2023-03-16','Шевченко'),(103,'Мишка',4,'Комп\'ютена 3','2023-03-17','Коваленко');
/*!40000 ALTER TABLE `перша_форма_нормалізації` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `таблиця_замовлення_2нф`
--

DROP TABLE IF EXISTS `таблиця_замовлення_2нф`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `таблиця_замовлення_2нф` (
  `номер_замовлення` int NOT NULL AUTO_INCREMENT,
  `клієнт` varchar(45) NOT NULL,
  `Адреса_клієнта` varchar(45) NOT NULL,
  `Дата_замовлення` varchar(45) NOT NULL,
  PRIMARY KEY (`номер_замовлення`)
) ENGINE=InnoDB AUTO_INCREMENT=104 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `таблиця_замовлення_2нф`
--

LOCK TABLES `таблиця_замовлення_2нф` WRITE;
/*!40000 ALTER TABLE `таблиця_замовлення_2нф` DISABLE KEYS */;
INSERT INTO `таблиця_замовлення_2нф` VALUES (101,'Мельник','Хрещатик 1','2023-03-15'),(102,'Шевченко','Басейна 2','2023-03-16'),(103,'Коваленко','Комп\'ютерна 3','2023-03-17');
/*!40000 ALTER TABLE `таблиця_замовлення_2нф` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `таблиця_замовлення_3нф`
--

DROP TABLE IF EXISTS `таблиця_замовлення_3нф`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `таблиця_замовлення_3нф` (
  `номер_замовлення` int unsigned NOT NULL AUTO_INCREMENT,
  `Дата_замовлення` date NOT NULL,
  `id_клієнта` int unsigned NOT NULL,
  PRIMARY KEY (`номер_замовлення`),
  UNIQUE KEY `номер_замовлення_UNIQUE` (`номер_замовлення`),
  UNIQUE KEY `id_клієнта_UNIQUE` (`id_клієнта`),
  KEY `Кліяєнт_замовлення_idx` (`id_клієнта`),
  CONSTRAINT `Кліяєнт_замовлення` FOREIGN KEY (`id_клієнта`) REFERENCES `клієнти_3фн` (`id_клієнта`)
) ENGINE=InnoDB AUTO_INCREMENT=104 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `таблиця_замовлення_3нф`
--

LOCK TABLES `таблиця_замовлення_3нф` WRITE;
/*!40000 ALTER TABLE `таблиця_замовлення_3нф` DISABLE KEYS */;
INSERT INTO `таблиця_замовлення_3нф` VALUES (101,'2023-03-15',1000),(102,'2023-03-16',1001),(103,'2023-03-17',1002);
/*!40000 ALTER TABLE `таблиця_замовлення_3нф` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `товари_замовлення_2нф`
--

DROP TABLE IF EXISTS `товари_замовлення_2нф`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `товари_замовлення_2нф` (
  `id_товару` int unsigned NOT NULL AUTO_INCREMENT,
  `Номер_Замовлення` int NOT NULL,
  `Назва_товару` varchar(45) NOT NULL,
  `Кількість` int unsigned NOT NULL,
  PRIMARY KEY (`id_товару`),
  UNIQUE KEY `id_товару_UNIQUE` (`id_товару`),
  KEY `замовлення_товари_idx` (`Номер_Замовлення`),
  CONSTRAINT `замовлення_товари_2ФН` FOREIGN KEY (`Номер_Замовлення`) REFERENCES `таблиця_замовлення_2нф` (`номер_замовлення`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `товари_замовлення_2нф`
--

LOCK TABLES `товари_замовлення_2нф` WRITE;
/*!40000 ALTER TABLE `товари_замовлення_2нф` DISABLE KEYS */;
INSERT INTO `товари_замовлення_2нф` VALUES (1,101,'Лептоп',3),(2,101,'Мишка',2),(3,102,'Принтер',1),(4,103,'Мишка',4);
/*!40000 ALTER TABLE `товари_замовлення_2нф` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `товари_замовлення_3нф`
--

DROP TABLE IF EXISTS `товари_замовлення_3нф`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `товари_замовлення_3нф` (
  `id_позиції` int unsigned NOT NULL AUTO_INCREMENT,
  `Назва_товару` varchar(45) NOT NULL,
  `Кількість` int unsigned NOT NULL,
  `Номер_замовлення` int unsigned NOT NULL,
  PRIMARY KEY (`id_позиції`),
  KEY `Замовлення_товари_idx` (`Номер_замовлення`),
  CONSTRAINT `Замовлення_товари` FOREIGN KEY (`Номер_замовлення`) REFERENCES `таблиця_замовлення_3нф` (`номер_замовлення`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `товари_замовлення_3нф`
--

LOCK TABLES `товари_замовлення_3нф` WRITE;
/*!40000 ALTER TABLE `товари_замовлення_3нф` DISABLE KEYS */;
INSERT INTO `товари_замовлення_3нф` VALUES (1,'Лептоп',3,101),(2,'Мишка',2,101),(3,'Принтер',1,102),(4,'Мишка',4,103);
/*!40000 ALTER TABLE `товари_замовлення_3нф` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-11-24 22:02:49
