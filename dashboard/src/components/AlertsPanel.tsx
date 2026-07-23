import type { AlertRow } from "../types";
import { pct, truncate } from "../labels";

type Props = { rows: AlertRow[] };

export function AlertsPanel({ rows }: Props) {
  return (
    <ul className="alert-list">
      {rows.map((row) => (
        <li key={row.alert_id} className={`alert-item alert-item--${row.alert_level}`}>
          <div className="alert-item__top">
            <span className="alert-item__level">{row.alert_level}</span>
            <span className="mono">{row.alert_type}</span>
          </div>
          <p className="alert-item__msg">{row.alert_message}</p>
          <div className="alert-item__meta">
            <span title={row.entity_name || row.entity_id}>
              {truncate(row.entity_name || row.entity_id, 36)}
            </span>
            <span className="mono">
              {row.metric_name}={pct(row.metric_value)} · n={row.review_count}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}
