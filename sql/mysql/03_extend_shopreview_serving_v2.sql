CREATE DATABASE IF NOT EXISTS shopreview_serving CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE shopreview_serving;

CREATE TABLE IF NOT EXISTS dws_category_sentiment (
 category_key CHAR(64) NOT NULL, main_category VARCHAR(255) NOT NULL, review_count BIGINT NOT NULL, product_count BIGINT NOT NULL,
 average_rating DOUBLE NULL, positive_count BIGINT NOT NULL, neutral_count BIGINT NOT NULL, negative_count BIGINT NOT NULL,
 positive_rate DOUBLE NOT NULL, neutral_rate DOUBLE NOT NULL, negative_rate DOUBLE NOT NULL, average_prediction_score DOUBLE NULL,
 generated_at DATETIME NULL, load_batch_id VARCHAR(64) NOT NULL, model_version VARCHAR(128) NOT NULL, synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(category_key,load_batch_id,model_version), KEY idx_category_batch_model(load_batch_id,model_version),
 KEY idx_category_negative(load_batch_id,model_version,negative_rate), KEY idx_category_reviews(load_batch_id,model_version,review_count), KEY idx_category_name(main_category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dws_store_sentiment (
 store_key CHAR(64) NOT NULL, store_name VARCHAR(512) NOT NULL, review_count BIGINT NOT NULL, product_count BIGINT NOT NULL,
 average_rating DOUBLE NULL, positive_count BIGINT NOT NULL, neutral_count BIGINT NOT NULL, negative_count BIGINT NOT NULL,
 positive_rate DOUBLE NOT NULL, neutral_rate DOUBLE NOT NULL, negative_rate DOUBLE NOT NULL, average_prediction_score DOUBLE NULL,
 generated_at DATETIME NULL, load_batch_id VARCHAR(64) NOT NULL, model_version VARCHAR(128) NOT NULL, synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(store_key,load_batch_id,model_version), KEY idx_store_batch_model(load_batch_id,model_version),
 KEY idx_store_negative(load_batch_id,model_version,negative_rate), KEY idx_store_reviews(load_batch_id,model_version,review_count), KEY idx_store_name(store_name(191))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dws_verified_purchase_sentiment (
 purchase_status VARCHAR(16) NOT NULL, review_count BIGINT NOT NULL, positive_count BIGINT NOT NULL, neutral_count BIGINT NOT NULL, negative_count BIGINT NOT NULL,
 positive_rate DOUBLE NOT NULL, neutral_rate DOUBLE NOT NULL, negative_rate DOUBLE NOT NULL, average_rating DOUBLE NULL,
 average_helpful_vote DOUBLE NULL, average_prediction_score DOUBLE NULL, generated_at DATETIME NULL,
 load_batch_id VARCHAR(64) NOT NULL, model_version VARCHAR(128) NOT NULL, synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(purchase_status,load_batch_id,model_version), KEY idx_verified_batch_model(load_batch_id,model_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dws_rating_prediction_matrix (
 rating_value INT NOT NULL, pred_label VARCHAR(16) NOT NULL, review_count BIGINT NOT NULL, rate_within_rating DOUBLE NOT NULL,
 generated_at DATETIME NULL, load_batch_id VARCHAR(64) NOT NULL, model_version VARCHAR(128) NOT NULL, synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(rating_value,pred_label,load_batch_id,model_version), KEY idx_rating_batch_model(load_batch_id,model_version), KEY idx_rating_label(pred_label)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dws_prediction_confidence (
 bucket_code VARCHAR(16) NOT NULL, bucket_order INT NOT NULL, minimum_score DOUBLE NOT NULL, maximum_score DOUBLE NOT NULL,
 review_count BIGINT NOT NULL, positive_count BIGINT NOT NULL, neutral_count BIGINT NOT NULL, negative_count BIGINT NOT NULL,
 average_prediction_score DOUBLE NULL, generated_at DATETIME NULL, load_batch_id VARCHAR(64) NOT NULL, model_version VARCHAR(128) NOT NULL,
 synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(bucket_code,load_batch_id,model_version),
 KEY idx_confidence_batch_model(load_batch_id,model_version), KEY idx_confidence_reviews(load_batch_id,model_version,review_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dws_monthly_sentiment (
 month_id CHAR(7) NOT NULL, review_count BIGINT NOT NULL, product_count BIGINT NOT NULL, positive_count BIGINT NOT NULL,
 neutral_count BIGINT NOT NULL, negative_count BIGINT NOT NULL, positive_rate DOUBLE NOT NULL, neutral_rate DOUBLE NOT NULL,
 negative_rate DOUBLE NOT NULL, average_rating DOUBLE NULL, average_prediction_score DOUBLE NULL, generated_at DATETIME NULL,
 load_batch_id VARCHAR(64) NOT NULL, model_version VARCHAR(128) NOT NULL, synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(month_id,load_batch_id,model_version), KEY idx_monthly_batch_model(load_batch_id,model_version), KEY idx_monthly_month(month_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dws_sentiment_alerts (
 alert_id CHAR(64) NOT NULL, alert_type VARCHAR(64) NOT NULL, alert_level VARCHAR(16) NOT NULL, entity_type VARCHAR(32) NOT NULL,
 entity_id VARCHAR(128) NOT NULL, entity_name TEXT NULL, metric_name VARCHAR(64) NOT NULL, metric_value DOUBLE NOT NULL,
 threshold_value DOUBLE NOT NULL, review_count BIGINT NOT NULL, alert_message TEXT NOT NULL, generated_at DATETIME NULL,
 load_batch_id VARCHAR(64) NOT NULL, model_version VARCHAR(128) NOT NULL, synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(alert_id), KEY idx_alert_batch_model(load_batch_id,model_version), KEY idx_alert_level_type(load_batch_id,model_version,alert_level,alert_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dws_review_samples (
 sample_id CHAR(64) NOT NULL, parent_asin VARCHAR(64) NULL, product_title TEXT NULL, main_category VARCHAR(255) NULL,
 rating DOUBLE NOT NULL, pred_label VARCHAR(16) NOT NULL, pred_score DOUBLE NOT NULL, review_text_preview VARCHAR(720) NULL,
 text_length BIGINT NOT NULL, review_time DATETIME NULL, sample_rank INT NOT NULL, generated_at DATETIME NULL,
 load_batch_id VARCHAR(64) NOT NULL, model_version VARCHAR(128) NOT NULL, synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(sample_id,load_batch_id,model_version), KEY idx_samples_batch_model(load_batch_id,model_version), KEY idx_samples_label(load_batch_id,model_version,pred_label)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dws_aspect_summary (
 aspect_code VARCHAR(64) NOT NULL, aspect_name VARCHAR(128) NOT NULL, mention_count BIGINT NOT NULL, product_count BIGINT NOT NULL,
 positive_count BIGINT NOT NULL, neutral_count BIGINT NOT NULL, negative_count BIGINT NOT NULL, positive_rate DOUBLE NOT NULL,
 neutral_rate DOUBLE NOT NULL, negative_rate DOUBLE NOT NULL, average_prediction_score DOUBLE NULL, extraction_method VARCHAR(64) NOT NULL,
 rule_version VARCHAR(64) NOT NULL, generated_at DATETIME NULL, load_batch_id VARCHAR(64) NOT NULL, model_version VARCHAR(128) NOT NULL,
 synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(aspect_code,load_batch_id,model_version),
 KEY idx_aspect_batch_model(load_batch_id,model_version), KEY idx_aspect_negative(load_batch_id,model_version,negative_rate), KEY idx_aspect_reviews(load_batch_id,model_version,mention_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dws_negative_reasons (
 reason_code VARCHAR(64) NOT NULL, reason_name VARCHAR(128) NOT NULL, mention_count BIGINT NOT NULL, product_count BIGINT NOT NULL,
 share_of_negative_reviews DOUBLE NOT NULL, average_prediction_score DOUBLE NULL, extraction_method VARCHAR(64) NOT NULL,
 rule_version VARCHAR(64) NOT NULL, generated_at DATETIME NULL, load_batch_id VARCHAR(64) NOT NULL, model_version VARCHAR(128) NOT NULL,
 synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(reason_code,load_batch_id,model_version),
 KEY idx_reason_batch_model(load_batch_id,model_version), KEY idx_reason_share(load_batch_id,model_version,share_of_negative_reviews), KEY idx_reason_mentions(load_batch_id,model_version,mention_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
