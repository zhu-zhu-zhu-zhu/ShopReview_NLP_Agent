CREATE DATABASE IF NOT EXISTS shopreview_serving
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE shopreview_serving;

CREATE TABLE IF NOT EXISTS dws_sentiment_overview (
  load_batch_id VARCHAR(64) NOT NULL,
  model_version VARCHAR(128) NOT NULL,
  review_count BIGINT NOT NULL,
  product_count BIGINT NOT NULL,
  positive_count BIGINT NOT NULL,
  neutral_count BIGINT NOT NULL,
  negative_count BIGINT NOT NULL,
  positive_rate DOUBLE NOT NULL,
  neutral_rate DOUBLE NOT NULL,
  negative_rate DOUBLE NOT NULL,
  average_rating DOUBLE NULL,
  average_prediction_score DOUBLE NULL,
  generated_at DATETIME NULL,
  synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (load_batch_id, model_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dws_sentiment_daily (
  dt DATE NOT NULL,
  load_batch_id VARCHAR(64) NOT NULL,
  model_version VARCHAR(128) NOT NULL,
  review_count BIGINT NOT NULL,
  positive_count BIGINT NOT NULL,
  neutral_count BIGINT NOT NULL,
  negative_count BIGINT NOT NULL,
  positive_rate DOUBLE NOT NULL,
  neutral_rate DOUBLE NOT NULL,
  negative_rate DOUBLE NOT NULL,
  average_rating DOUBLE NULL,
  generated_at DATETIME NULL,
  synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (dt, load_batch_id, model_version),
  KEY idx_daily_batch_model_dt (load_batch_id, model_version, dt)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dws_product_sentiment (
  parent_asin VARCHAR(64) NOT NULL,
  product_title TEXT NULL,
  store_name VARCHAR(512) NULL,
  main_category VARCHAR(255) NULL,
  load_batch_id VARCHAR(64) NOT NULL,
  model_version VARCHAR(128) NOT NULL,
  review_count BIGINT NOT NULL,
  average_rating DOUBLE NULL,
  positive_count BIGINT NOT NULL,
  neutral_count BIGINT NOT NULL,
  negative_count BIGINT NOT NULL,
  positive_rate DOUBLE NOT NULL,
  neutral_rate DOUBLE NOT NULL,
  negative_rate DOUBLE NOT NULL,
  verified_purchase_rate DOUBLE NULL,
  average_helpful_vote DOUBLE NULL,
  average_prediction_score DOUBLE NULL,
  generated_at DATETIME NULL,
  synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (parent_asin, load_batch_id, model_version),
  KEY idx_product_batch_model (load_batch_id, model_version),
  KEY idx_product_review_count (load_batch_id, model_version, review_count),
  KEY idx_product_negative_rate (load_batch_id, model_version, negative_rate),
  KEY idx_product_main_category (main_category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
