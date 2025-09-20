-- MySQL dump 10.13
-- Host: localhost    Database: bankdb
-- Table structure for table `users`

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `account_number` varchar(20) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `balance` double DEFAULT NULL,
  `card_last4` varchar(4) DEFAULT NULL,                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             
  PRIMARY KEY (`id`)
) ENGINE=InnoDB;

INSERT INTO `users` VALUES (1,'Vennela','v@gmail.com','ACC123','12345',50000,'9876');
INSERT INTO `users` VALUES (2,'Vasudev Shri Krishn','krishn@example.com','ACC1001','password123',5000,'1234');
