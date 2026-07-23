import type { CategoryRow, VerifiedRow } from "../types";
import { pct } from "../labels";

type Props = {
  categories: CategoryRow[];
  verified: VerifiedRow[];
};

export function SegmentCards({ categories, verified }: Props) {
  return (
    <div className="segment-grid">
      {categories.map((c) => (
        <article key={c.main_category} className="segment-card">
          <p className="segment-card__eyebrow">品类</p>
          <h3>{c.main_category}</h3>
          <p className="segment-card__stats mono">
            n={c.review_count} · SKU={c.product_count}
          </p>
          <p>
            正 {pct(c.positive_rate)} · 中 {pct(c.neutral_rate)} · 负{" "}
            <span className="neg">{pct(c.negative_rate)}</span>
          </p>
        </article>
      ))}
      {verified.map((v) => (
        <article key={v.purchase_status} className="segment-card">
          <p className="segment-card__eyebrow">购买认证</p>
          <h3>{v.purchase_status}</h3>
          <p className="segment-card__stats mono">n={v.review_count}</p>
          <p>
            正 {pct(v.positive_rate)} · 负{" "}
            <span className="neg">{pct(v.negative_rate)}</span>
            {v.average_rating != null ? ` · ★${v.average_rating.toFixed(2)}` : ""}
          </p>
        </article>
      ))}
    </div>
  );
}
