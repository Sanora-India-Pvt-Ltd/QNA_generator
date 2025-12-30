-- MySQL/MariaDB Database Setup for Video MCQ Generator
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

-- Create indexes for better performance
-- If you get "Duplicate key name" error, indexes already exist (safe to ignore)
CREATE INDEX idx_video_mcqs_url ON video_mcqs(url(255));
CREATE INDEX idx_video_mcqs_video_id ON video_mcqs(video_id);

-- Verify table creation
SHOW TABLES;
DESCRIBE video_mcqs;
