CREATE DATABASE
IF NOT EXISTS `tracker`
USE `tracker`;

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
  `expense` int DEFAULT '0',
  `role` varchar
(100) DEFAULT 'user',
  PRIMARY KEY
(`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

USE tracker;
DROP TABLE IF EXISTS `transactions`;
CREATE TABLE `transactions`
(
	 id int AUTO_INCREMENT,
     user_id INT,
    amount int NOT NULL DEFAULT '0',
    description varchar (255) DEFAULT NULL,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE
);