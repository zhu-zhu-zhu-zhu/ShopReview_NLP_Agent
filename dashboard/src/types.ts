export type ResponseMeta = {
  data_mode: string;
  schema_version: string;
  data_scope: string;
  production_business_metrics: boolean;
  source: string;
  message?: string;
  load_batch_id?: string;
  model_version?: string;
  extraction_method?: string;
  generated_at?: string;
};

export type HealthPayload = {
  ok: boolean;
  data_mode: string;
  schema_version: string;
  production_business_metrics: boolean;
  export_name: string;
  data_scope_summary: string;
  sentiment_data?: string;
  aspect_data?: string;
  serving_release?: string;
  load_batch_id?: string;
  model_version?: string;
  record_counts?: Record<string, number>;
  source: string;
};

export type KpiRecord = {
  review_count: number;
  user_count: number | null;
  product_count: number;
  positive_count: number;
  neutral_count: number;
  negative_count: number;
  positive_rate: number;
  neutral_rate: number;
  negative_rate: number;
  average_rating: number;
  average_prediction_score?: number;
  generated_at?: string;
  data_scope: string;
};

export type ProductRow = {
  parent_asin: string;
  product_title: string;
  store_name?: string | null;
  main_category?: string | null;
  review_count: number;
  average_rating: number;
  positive_count: number;
  neutral_count: number;
  negative_count: number;
  positive_rate: number;
  neutral_rate: number;
  negative_rate: number;
  average_prediction_score?: number;
  generated_at?: string;
  load_batch_id?: string;
  model_version?: string;
  data_scope: string;
};

export type AspectRow = {
  aspect: string;
  reason_code: string;
  reason_name: string;
  mention_count: number;
  negative_count: number;
  neutral_count: number;
  positive_count: number;
  product_count?: number;
  positive_rate?: number;
  neutral_rate?: number;
  negative_rate: number;
  average_confidence: number;
  extractor_version: string;
  extraction_method?: string;
  rule_version?: string;
  generated_at?: string;
  load_batch_id?: string;
  model_version?: string;
  data_scope: string;
};

export type ReasonRow = {
  parent_asin: string;
  product_title: string;
  aspect: string;
  reason_code: string;
  reason_name: string;
  reason_count: number;
  reason_share: number;
  extractor_version: string;
  extraction_method?: string;
  rule_version?: string;
  generated_at?: string;
  load_batch_id?: string;
  model_version?: string;
  data_scope: string;
};

export type TrendPoint = {
  dt?: string;
  month_id?: string;
  review_count: number;
  positive_rate: number;
  neutral_rate: number;
  negative_rate: number;
  average_rating?: number;
};

export type AlertRow = {
  alert_id: string;
  alert_type: string;
  alert_level: string;
  entity_type: string;
  entity_id: string;
  entity_name?: string | null;
  metric_name: string;
  metric_value: number;
  threshold_value: number;
  review_count: number;
  alert_message: string;
  generated_at?: string;
  load_batch_id?: string;
  model_version?: string;
};

export type SampleRow = {
  sample_id: string;
  parent_asin?: string | null;
  product_title?: string | null;
  rating: number;
  pred_label: string;
  pred_score: number;
  review_text_preview?: string | null;
  generated_at?: string;
  load_batch_id?: string;
  model_version?: string;
};

export type CategoryRow = {
  main_category: string;
  review_count: number;
  product_count: number;
  positive_rate: number;
  neutral_rate: number;
  negative_rate: number;
  average_rating?: number;
};

export type StoreRow = {
  store_key: string;
  store_name: string;
  review_count: number;
  product_count: number;
  positive_count: number;
  positive_rate: number;
  neutral_rate: number;
  negative_rate: number;
  average_rating?: number;
  average_prediction_score?: number;
};

export type VerifiedRow = {
  purchase_status: string;
  review_count: number;
  positive_rate: number;
  neutral_rate: number;
  negative_rate: number;
  average_rating?: number;
};

export type MatrixCell = {
  rating_value: number;
  pred_label: string;
  review_count: number;
  rate_within_rating: number;
};

export type ConfidenceRow = {
  bucket_code: string;
  bucket_order: number;
  review_count: number;
  average_prediction_score?: number;
  positive_count: number;
  neutral_count: number;
  negative_count: number;
  generated_at?: string;
  load_batch_id?: string;
  model_version?: string;
};

export type Wrapped<T> = {
  ok: boolean;
  data: T;
  meta: ResponseMeta;
};
