-- MySQL/MariaDB Database Setup for Video MCQ Generator (Safe Version)
-- This version handles existing indexes gracefully
-- Run this in MySQL Workbench or via mysql command line
-- Requires MySQL 5.7+ or MariaDB 10.2+ (for JSON support)

-- Create database (if it doesn't exist)
CREATE DATABASE IF NOT EXISTS mcq_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Use the database
USE mcq_db;

-- Create table
CREATE TABLE IF NOT EXISTS video_mcqs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  video_id VARCHAR(32) UNIQUE NOT NULL,
  url TEXT NOT NULL,
  mcq_count INT NOT NULL DEFAULT 20,
  questions JSON NOT NULL,
  generator JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create indexes safely (only if they don't exist)
-- This uses a stored procedure approach to check first

DELIMITER $$

DROP PROCEDURE IF EXISTS create_index_if_not_exists$$
CREATE PROCEDURE create_index_if_not_exists(
    IN p_table_name VARCHAR(64),
    IN p_index_name VARCHAR(64),
    IN p_index_definition TEXT
)
BEGIN
    DECLARE index_exists INT DEFAULT 0;
    
    SELECT COUNT(*) INTO index_exists
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = p_table_name
      AND index_name = p_index_name;
    
    IF index_exists = 0 THEN
        SET @sql = CONCAT('CREATE INDEX ', p_index_name, ' ON ', p_table_name, ' ', p_index_definition);
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$

DELIMITER ;

-- Create indexes using the procedure
CALL create_index_if_not_exists('video_mcqs', 'idx_video_mcqs_url', '(url(255))');
CALL create_index_if_not_exists('video_mcqs', 'idx_video_mcqs_video_id', '(video_id)');

-- Clean up procedure
DROP PROCEDURE IF EXISTS create_index_if_not_exists;

-- Verify table creation
SHOW TABLES;
DESCRIBE video_mcqs;
SHOW INDEXES FROM video_mcqs;

