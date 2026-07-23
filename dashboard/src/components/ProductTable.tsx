import type { ProductRow } from "../types";
import { pct, truncate } from "../labels";

type Props = {
  rows: ProductRow[];
};

export function ProductTable({ rows }: Props) {
  return (
    <div className="table-wrap">
      <p className="panel-note">smoke 下多数商品 review_count 可能为 1（小样本）</p>
      <table className="data-table">
        <thead>
          <tr>
            <th>ASIN</th>
            <th>商品</th>
            <th>店铺</th>
            <th>负面率</th>
            <th>评论数</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.parent_asin}>
              <td className="mono">{row.parent_asin}</td>
              <td title={row.product_title}>{truncate(row.product_title, 36)}</td>
              <td>{row.store_name || "—"}</td>
              <td className="mono neg">{pct(row.negative_rate)}</td>
              <td className="mono">{row.review_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
