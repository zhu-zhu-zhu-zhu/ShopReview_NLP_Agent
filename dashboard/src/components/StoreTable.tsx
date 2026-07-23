import type { StoreRow } from "../types";
import { pct, truncate } from "../labels";

type Props = { rows: StoreRow[] };

export function StoreTable({ rows }: Props) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>店铺</th>
            <th>负面率</th>
            <th>评论量</th>
            <th>均分</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.store_key}>
              <td title={row.store_name}>{truncate(row.store_name, 28)}</td>
              <td className="mono neg">{pct(row.negative_rate)}</td>
              <td className="mono">{row.review_count}</td>
              <td className="mono">
                {row.average_rating != null ? row.average_rating.toFixed(2) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
