import { useEffect, useState } from "react";
import { getApiBase } from "../api";

type CapStatus = "pending" | "unavailable" | "error" | "ok";

type Cap = {
  path: string;
  label: string;
  status: CapStatus;
  detail: string;
};

const CAPS = [
  { path: "/api/trend", label: "日趋势" },
  { path: "/api/alerts", label: "告警" },
  { path: "/api/samples", label: "样例评论" },
] as const;

async function probe(path: string): Promise<{ status: CapStatus; detail: string }> {
  const base = getApiBase();
  try {
    const res = await fetch(`${base}${path}`);
    if (res.status === 501) {
      return { status: "unavailable", detail: "暂未接入（501）" };
    }
    if (!res.ok) {
      return { status: "error", detail: `HTTP ${res.status}` };
    }
    return { status: "ok", detail: "已返回数据" };
  } catch {
    return { status: "error", detail: "后端不可达" };
  }
}

export function CapabilityStrip() {
  const [items, setItems] = useState<Cap[]>(
    CAPS.map((c) => ({
      path: c.path,
      label: c.label,
      status: "pending",
      detail: "检测中…",
    })),
  );

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const next: Cap[] = [];
      for (const cap of CAPS) {
        const result = await probe(cap.path);
        next.push({
          path: cap.path,
          label: cap.label,
          status: result.status,
          detail: result.detail,
        });
      }
      if (!cancelled) setItems(next);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="cap-strip" aria-label="预留能力状态">
      <div className="cap-strip__head">
        <h2>预留能力</h2>
        <p>告警 / 样例 / 趋势按服务库就绪情况探测；未接入则诚实 501</p>
      </div>
      <ul className="cap-strip__list">
        {items.map((item) => (
          <li key={item.path} className={`cap-chip cap-chip--${item.status}`}>
            <span className="cap-chip__label">{item.label}</span>
            <span className="cap-chip__path mono">{item.path}</span>
            <span className="cap-chip__detail">{item.detail}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
