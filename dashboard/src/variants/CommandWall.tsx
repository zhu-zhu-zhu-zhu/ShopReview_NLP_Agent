import { useEffect, useMemo, useState } from "react";
import { pct, truncate } from "../labels";
import type { ServingBoardData } from "../hooks/useServingBoardData";
import { healthIndex } from "../hooks/useServingBoardData";
import { HealthRing } from "../components/HealthRing";
import { TrendLineChart } from "../components/TrendLineChart";
import { RatingHeatmap } from "../components/RatingHeatmap";
import { ConfidenceChart } from "../components/ConfidenceChart";
import "./wall.css";

type Props = {
  data: ServingBoardData;
  onRefresh: () => void;
  loading: boolean;
};

type TrendMode = "monthly" | "daily";

function useClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);
  return now.toLocaleString("zh-CN", { hour12: false });
}

export function CommandWall({ data, onRefresh, loading }: Props) {
  const clock = useClock();
  const [trendMode, setTrendMode] = useState<TrendMode>("monthly");

  const highAlerts = useMemo(
    () =>
      data.alerts.filter((a) =>
        ["high", "critical"].includes(String(a.alert_level).toLowerCase()),
      ),
    [data.alerts],
  );

  const score = healthIndex(
    data.kpi,
    highAlerts.length,
    data.stores.map((s) => Number(s.negative_rate || 0)),
  );

  const ticker = useMemo(() => {
    const parts = [
      ...data.aspects.slice(0, 6).map(
        (a) => `${a.aspect} 负提及 ${a.negative_count}`,
      ),
      ...data.reasons.slice(0, 5).map(
        (r) => `${r.reason_name} ${pct(r.reason_share)}`,
      ),
      ...data.verified.map(
        (v) => `${v.purchase_status} n=${v.review_count} 负${pct(v.negative_rate)}`,
      ),
      ...data.samples.slice(0, 3).map((s) => `样例 ${s.pred_label} ★${s.rating}`),
    ];
    return parts.join("     ◆     ");
  }, [data]);

  const trendRows = trendMode === "monthly" ? data.monthly : data.daily;

  return (
    <div className="wall">
      <div className="wall__veil" aria-hidden />
      <div className="wall__scan" aria-hidden />

      {/* 1. Chrome — identity + provenance only */}
      <header className="wall__chrome">
        <div className="wall__chrome-left">
          <p className="wall__brand">SHOPREVIEW</p>
          <h1>
            情感作战室 <span className="wall__live">LIVE</span>
          </h1>
        </div>
        <div className="wall__chrome-center mono">
          <span>{clock}</span>
          <span className="wall__sep">|</span>
          <span>{data.health.load_batch_id || "prod_v1_100k"}</span>
          <span className="wall__sep">|</span>
          <span>{data.health.model_version || "tfidf_logreg_oof_v1"}</span>
        </div>
        <div className="wall__chrome-right">
          <button type="button" className="wall__btn" onClick={onRefresh} disabled={loading}>
            {loading ? "同步中" : "同步"}
          </button>
        </div>
      </header>

      {/* 2. Situation ribbon — one glance status */}
      <section className="wall__situation" aria-label="态势条">
        <div className="wall-sit__ring">
          <HealthRing kpi={data.kpi} score={score} dark />
        </div>
        <div className="wall-sit__kpis">
          <div>
            <span>评论量</span>
            <strong className="mono">{data.kpi.review_count.toLocaleString()}</strong>
          </div>
          <div>
            <span>正面</span>
            <strong className="mono wall-pos">{pct(data.kpi.positive_rate)}</strong>
          </div>
          <div>
            <span>中性</span>
            <strong className="mono">{pct(data.kpi.neutral_rate)}</strong>
          </div>
          <div>
            <span>负面</span>
            <strong className="mono wall-neg">{pct(data.kpi.negative_rate)}</strong>
          </div>
          <div>
            <span>均分</span>
            <strong className="mono">{data.kpi.average_rating.toFixed(2)}</strong>
          </div>
        </div>
        <div className="wall-sit__pulse">
          <div className="wall-sit__pulse-item">
            <span>HIGH+</span>
            <strong className={`mono ${highAlerts.length ? "wall-neg" : "wall-pos"}`}>
              {highAlerts.length}
            </strong>
          </div>
          <div className="wall-sit__pulse-item">
            <span>告警总数</span>
            <strong className="mono">{data.alerts.length}</strong>
          </div>
          <div className="wall-sit__pulse-item wall-sit__pulse-item--wide">
            <span>最高风险店铺</span>
            <strong title={data.stores[0]?.store_name}>
              {data.stores[0]
                ? `${truncate(data.stores[0].store_name, 16)} ${pct(data.stores[0].negative_rate)}`
                : "—"}
            </strong>
          </div>
        </div>
      </section>

      {/* 3. Main ops — risk | trend | alerts */}
      <div className="wall__ops">
        <section className="wall-pane wall-pane--risk" aria-label="风险热力榜">
          <header className="wall-pane__head">
            <h2>风险热力榜</h2>
            <span>store · product</span>
          </header>
          <div className="wall-risk">
            <div className="wall-risk__col">
              <h3>店铺 TOP</h3>
              <ol>
                {data.stores.slice(0, 8).map((s, i) => (
                  <li key={s.store_key}>
                    <span className="wall-rank mono">{i + 1}</span>
                    <span className="wall-risk-name" title={s.store_name}>
                      {truncate(s.store_name, 22)}
                    </span>
                    <span className="mono wall-neg">{pct(s.negative_rate)}</span>
                    <span className="mono wall-dim">n={s.review_count}</span>
                  </li>
                ))}
              </ol>
            </div>
            <div className="wall-risk__col">
              <h3>商品 TOP</h3>
              <ol>
                {data.products.slice(0, 8).map((p, i) => (
                  <li key={p.parent_asin}>
                    <span className="wall-rank mono">{i + 1}</span>
                    <span className="wall-risk-name mono" title={p.product_title}>
                      {p.parent_asin}
                    </span>
                    <span className="mono wall-neg">{pct(p.negative_rate)}</span>
                    <span className="mono wall-dim">n={p.review_count}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        <section className="wall-pane wall-pane--trend" aria-label="情感时间河">
          <header className="wall-pane__head">
            <h2>情感时间河</h2>
            <div className="wall-tabs" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={trendMode === "monthly"}
                className={trendMode === "monthly" ? "is-active" : undefined}
                onClick={() => setTrendMode("monthly")}
              >
                月度全景
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={trendMode === "daily"}
                className={trendMode === "daily" ? "is-active" : undefined}
                onClick={() => setTrendMode("daily")}
              >
                近 365 日
              </button>
            </div>
          </header>
          <div className="wall-trend">
            {trendRows.length ? (
              <TrendLineChart rows={trendRows} mode={trendMode} />
            ) : (
              <p className="wall-empty">无趋势数据</p>
            )}
          </div>
        </section>

        <section className="wall-pane wall-pane--alerts" aria-label="告警雷达">
          <header className="wall-pane__head">
            <h2>告警雷达</h2>
            <span className={highAlerts.length ? "wall-neg" : undefined}>
              {highAlerts.length} HIGH+
            </span>
          </header>
          <ul className="wall-alert-rail">
            {(data.alerts.length ? data.alerts : []).slice(0, 12).map((a) => (
              <li
                key={a.alert_id}
                className={`wall-alert-rail__item wall-alert-rail__item--${a.alert_level}`}
              >
                <div className="wall-alert-rail__top">
                  <em>{a.alert_level}</em>
                  <span className="mono">{a.alert_type}</span>
                </div>
                <p>{truncate(a.alert_message, 68)}</p>
                <div className="wall-alert-rail__meta mono">
                  <span>{truncate(a.entity_name || a.entity_id, 26)}</span>
                  <span>
                    {a.metric_name} {pct(a.metric_value)}
                  </span>
                </div>
              </li>
            ))}
            {!data.alerts.length ? <li className="wall-empty">暂无告警</li> : null}
          </ul>
        </section>
      </div>

      {/* 4. Model QA band — diagnostics, secondary */}
      <section className="wall__qa" aria-label="模型诊断">
        <div className="wall-qa__matrix">
          <header className="wall-pane__head">
            <h2>星级 × 预测</h2>
            <span>偏差矩阵</span>
          </header>
          {data.matrix.length ? (
            <RatingHeatmap rows={data.matrix} />
          ) : (
            <p className="wall-empty">无矩阵</p>
          )}
        </div>
        <div className="wall-qa__conf">
          <header className="wall-pane__head">
            <h2>置信度</h2>
            <span>分桶</span>
          </header>
          {data.confidence.length ? (
            <ConfidenceChart rows={data.confidence} />
          ) : (
            <p className="wall-empty">无分桶</p>
          )}
        </div>
        <div className="wall-qa__aspects">
          <header className="wall-pane__head">
            <h2>负面方面</h2>
            <span>keyword_rules</span>
          </header>
          <ul className="wall-aspect-list">
            {data.aspects.slice(0, 8).map((a) => (
              <li key={a.aspect}>
                <span title={a.aspect}>{truncate(String(a.aspect), 18)}</span>
                <strong className="mono wall-neg">{a.negative_count}</strong>
              </li>
            ))}
            {!data.aspects.length ? <li className="wall-empty">无方面数据</li> : null}
          </ul>
        </div>
      </section>

      <footer className="wall__ticker" aria-label="跑马灯">
        <span className="wall__ticker-tag">FEED</span>
        <div className="wall__ticker-mask">
          <div className="wall__ticker-track">{ticker}</div>
        </div>
      </footer>
    </div>
  );
}
