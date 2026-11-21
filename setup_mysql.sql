-- SQL Script to create AcxiomCRM Database in MySQL
-- Execute in MySQL Workbench, phpMyAdmin, or MySQL CLI:
-- mysql -u root -p < setup_mysql.sql

CREATE DATABASE IF NOT EXISTS acxiom_crm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE acxiom_crm;

-- Grant permissions if necessary:
-- GRANT ALL PRIVILEGES ON acxiom_crm.* TO 'crm_user'@'localhost' IDENTIFIED BY 'password123';
-- FLUSH PRIVILEGES;
