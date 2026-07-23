import type { SampleRow } from "../types";
import { truncate } from "../labels";

type Props = { rows: SampleRow[] };

export function SamplesGrid({ rows }: Props) {
  return (
    <div className="sample-grid">
      {rows.map((row) => (
        <article key={row.sample_id} className={`sample-card sample-card--${row.pred_label}`}>
          <div className="sample-card__top">
            <span className="sample-card__label">{row.pred_label}</span>
            <span className="mono">
              ★{row.rating} · {(row.pred_score * 100).toFixed(0)}%
            </span>
          </div>
          <p className="sample-card__text">
            {row.review_text_preview || "（无预览文本）"}
          </p>
          <p className="sample-card__meta mono" title={row.product_title || ""}>
            {row.parent_asin || "—"} · {truncate(row.product_title || "", 40)}
          </p>
        </article>
      ))}
    </div>
  );
}
