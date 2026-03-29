-- novelDownloader database initialization
-- MySQL 8

CREATE DATABASE IF NOT EXISTS novel_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE novel_db;

-- -------------------------------------------------------
-- books
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS books (
  id                BIGINT          NOT NULL AUTO_INCREMENT,
  source_site       VARCHAR(50)     NOT NULL COMMENT '站点标识, e.g. txt520',
  source_id         VARCHAR(50)     NOT NULL COMMENT '站点内书籍 ID',
  source_url        VARCHAR(500)    DEFAULT NULL COMMENT '详情页 URL',
  title             VARCHAR(255)    NOT NULL,
  author            VARCHAR(100)    DEFAULT NULL,
  category          VARCHAR(50)     DEFAULT NULL,
  summary           TEXT            DEFAULT NULL,
  chapter_count     INT             DEFAULT NULL COMMENT '章节数（来自文件名括号）',
  file_size_bytes   BIGINT          DEFAULT NULL,
  detected_encoding VARCHAR(20)     DEFAULT NULL,
  parse_status      ENUM('pending','processing','success','failed') NOT NULL DEFAULT 'pending',
  total_words       INT             DEFAULT NULL,
  first_seen_at     TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  downloaded_at     TIMESTAMP       NULL DEFAULT NULL,
  parsed_at         TIMESTAMP       NULL DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_source (source_site, source_id),
  KEY idx_parse_status (parse_status),
  KEY idx_first_seen_at (first_seen_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------
-- chapters
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS chapters (
  id            BIGINT          NOT NULL AUTO_INCREMENT,
  book_id       BIGINT          NOT NULL,
  chapter_num   INT             NOT NULL COMMENT '章节序号（1开始）',
  chapter_title VARCHAR(255)    DEFAULT NULL,
  content       LONGTEXT        DEFAULT NULL,
  content_hash  CHAR(64)        DEFAULT NULL COMMENT 'SHA-256(content)',
  word_count    INT             DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_chapter (book_id, chapter_num),
  KEY idx_book_id (book_id),
  CONSTRAINT fk_chapter_book FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------
-- parse_logs
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS parse_logs (
  id                  BIGINT          NOT NULL AUTO_INCREMENT,
  book_id             BIGINT          DEFAULT NULL,
  log_type            ENUM('info','warning','error') NOT NULL DEFAULT 'info',
  message             VARCHAR(500)    DEFAULT NULL,
  detected_encoding   VARCHAR(20)     DEFAULT NULL,
  parse_duration_ms   INT             DEFAULT NULL,
  created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_book_id (book_id),
  KEY idx_log_type (log_type),
  KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
