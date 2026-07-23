/** Fashion aspect controlled vocabulary — display labels only. */
export const ASPECT_LABELS: Record<string, string> = {
  size: "尺码",
  color: "颜色",
  material: "材质",
  comfort: "舒适度",
  workmanship: "做工",
  description_mismatch: "描述不符",
  packaging: "包装",
  delivery: "物流相关",
  price: "价格",
  other: "其他",
};

export function aspectLabel(aspect: string): string {
  const key = aspect.trim().toLowerCase();
  const zh = ASPECT_LABELS[key];
  return zh ? `${aspect} · ${zh}` : aspect;
}

export function pct(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

export function truncate(text: string, max = 42): string {
  const t = text.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}
