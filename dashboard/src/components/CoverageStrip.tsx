import type { HealthPayload } from "../types";

type Props = { health: HealthPayload };

const LABELS: Record<string, string> = {
  sentiment_overview: "overview",
  sentiment_daily: "daily",
  product_sentiment: "product",
  category_sentiment: "category",
  store_sentiment: "store",
  verified_purchase_sentiment: "verified",
  rating_prediction_matrix: "matrix",
  prediction_confidence: "confidence",
  monthly_sentiment: "monthly",
  sentiment_alerts: "alerts",
  review_samples: "samples",
  aspect_summary: "aspects",
  negative_reasons: "reasons",
  review_count: "reviews",
};

export function CoverageStrip({ health }: Props) {
  const counts = health.record_counts || {};
  const entries = Object.entries(counts).filter(([k]) => k !== "review_count");
  return (
    <section className="coverage-strip" aria-label="服务库表覆盖">
      <div className="cap-strip__head">
        <h2>服务库覆盖 · {health.serving_release || "serving"}</h2>
        <p>以下行数来自 /api/health.record_counts，对应 MySQL serving v2 全表</p>
      </div>
      <ul className="coverage-strip__list">
        {entries.map(([key, value]) => (
          <li key={key}>
            <span className="mono">{LABELS[key] || key}</span>
            <strong className="mono">{Number(value).toLocaleString()}</strong>
          </li>
        ))}
      </ul>
    </section>
  );
}
