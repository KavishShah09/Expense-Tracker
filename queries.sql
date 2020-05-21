CREATE DATABASE
IF NOT EXISTS `tracker`;
USE `tracker`;


CREATE TABLE `transactions`
(
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `amount` int NOT NULL DEFAULT '0',
  `description` varchar
(255) DEFAULT NULL,
  `category` varchar (255) DEFAULT NULL,
  `date` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY
(`id`),
  KEY `user_id`
(`user_id`),
  CONSTRAINT `transactions_ibfk_1` FOREIGN KEY
(`user_id`) REFERENCES `users`
(`id`) ON
DELETE CASCADE ON
UPDATE CASCADE
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users`
(
  `id` int NOT NULL AUTO_INCREMENT,
  `first_name` varchar
(100) DEFAULT NULL,
  `last_name` varchar
(100) DEFAULT NULL,
  `email` varchar
(100) DEFAULT NULL,
  `username` varchar
(100) DEFAULT NULL,
  `password` varchar
(100) DEFAULT NULL,
  `role` varchar
(100) DEFAULT 'user',
  PRIMARY KEY
(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;