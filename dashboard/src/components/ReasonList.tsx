import type { ReasonRow } from "../types";
import { pct, truncate } from "../labels";

type Props = {
  rows: ReasonRow[];
};

export function ReasonList({ rows }: Props) {
  return (
    <ul className="reason-list">
      {rows.map((row, index) => (
        <li key={`${row.reason_code}-${row.parent_asin || "global"}-${index}`}>
          <div className="reason-list__top">
            <span className="reason-list__name">{row.reason_name}</span>
            <span className="mono">{pct(row.reason_share)}</span>
          </div>
          <div className="reason-list__meta">
            <span className="mono">{row.reason_code}</span>
            {row.parent_asin ? (
              <span className="mono">{row.parent_asin}</span>
            ) : (
              <span>全局原因</span>
            )}
          </div>
          {row.product_title ? (
            <p className="reason-list__title" title={row.product_title}>
              {truncate(row.product_title, 52)}
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
