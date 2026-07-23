import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import type { DashboardTarget } from "../agentTypes";
import { pct, truncate } from "../labels";
import type { ServingBoardData } from "../hooks/useServingBoardData";
import { healthIndex } from "../hooks/useServingBoardData";
import { AgentDrawer } from "../components/AgentDrawer";
import { AgentLauncher } from "../components/AgentLauncher";
import { HealthRing } from "../components/HealthRing";
import { TrendLineChart } from "../components/TrendLineChart";
import { RatingHeatmap } from "../components/RatingHeatmap";
import { ConfidenceChart } from "../components/ConfidenceChart";
import { AnimatedNumber } from "../components/AnimatedNumber";
import { useReducedMotion } from "../hooks/useReducedMotion";
import "./wall.css";

type Props = {
  data: ServingBoardData;
  onRefresh: () => void;
  loading: boolean;
};

type TrendMode = "monthly" | "daily";
type RankMode = "negative" | "positive";

function useClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    let timer = 0;
    const tick = () => {
      setNow(new Date());
      timer = window.setTimeout(tick, 1000 - (Date.now() % 1000));
    };
    timer = window.setTimeout(tick, 1000 - (Date.now() % 1000));
    return () => window.clearTimeout(timer);
  }, []);
  return now.toLocaleString("zh-CN", { hour12: false });
}

const integer = (value: number) => Math.round(value).toLocaleString("zh-CN");
const percentage = (value: number) => `${(value * 100).toFixed(1)}%`;
const decimal2 = (value: number) => value.toFixed(2);

export function CommandWall({ data, onRefresh, loading }: Props) {
  const clock = useClock();
  const [trendMode, setTrendMode] = useState<TrendMode>("monthly");
  const [rankMode, setRankMode] = useState<RankMode>("negative");
  const [rankPhase, setRankPhase] = useState<"idle" | "leaving" | "entering">(
    "idle",
  );
  const [agentOpen, setAgentOpen] = useState(false);
  const highlightTimer = useRef<number | null>(null);
  const rankTimers = useRef<number[]>([]);
  const reducedMotion = useReducedMotion();

  useEffect(
    () => () => {
      if (highlightTimer.current) window.clearTimeout(highlightTimer.current);
      rankTimers.current.forEach((timer) => window.clearTimeout(timer));
    },
    [],
  );

  function changeRankMode(next: RankMode) {
    if (next === rankMode || rankPhase !== "idle") return;
    if (reducedMotion) {
      setRankMode(next);
      return;
    }
    setRankPhase("leaving");
    rankTimers.current.push(
      window.setTimeout(() => {
        setRankMode(next);
        setRankPhase("entering");
        rankTimers.current.push(
          window.setTimeout(() => setRankPhase("idle"), 360),
        );
      }, 160),
    );
  }

  function focusEvidence(target: DashboardTarget) {
    const current = document.querySelector(".agent-evidence-focus");
    current?.classList.remove("agent-evidence-focus");
    const element = document.querySelector<HTMLElement>(
      `[data-agent-target="${target}"]`,
    );
    if (!element) return;
    element.scrollIntoView({ behavior: "smooth", block: "center" });
    window.setTimeout(() => element.classList.add("agent-evidence-focus"), 180);
    if (highlightTimer.current) window.clearTimeout(highlightTimer.current);
    highlightTimer.current = window.setTimeout(
      () => element.classList.remove("agent-evidence-focus"),
      2800,
    );
  }

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
  const positiveRanking = rankMode === "positive";
  const rankedStores = positiveRanking ? data.positiveStores : data.stores;
  const rankedProducts = positiveRanking
    ? data.positiveProducts
    : data.products;

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
      <section
        className="wall__situation"
        aria-label="态势条"
        data-agent-target="kpi"
      >
        <div className="wall-sit__ring">
          <HealthRing kpi={data.kpi} score={score} dark />
        </div>
        <div className="wall-sit__kpis">
          <div>
            <span>评论量</span>
            <AnimatedNumber
              className="mono"
              value={data.kpi.review_count}
              format={integer}
            />
          </div>
          <div>
            <span>正面</span>
            <AnimatedNumber
              className="mono wall-pos"
              value={data.kpi.positive_rate}
              format={percentage}
            />
          </div>
          <div>
            <span>中性</span>
            <AnimatedNumber
              className="mono"
              value={data.kpi.neutral_rate}
              format={percentage}
            />
          </div>
          <div>
            <span>负面</span>
            <AnimatedNumber
              className="mono wall-neg"
              value={data.kpi.negative_rate}
              format={percentage}
            />
          </div>
          <div>
            <span>均分</span>
            <AnimatedNumber
              className="mono"
              value={data.kpi.average_rating}
              format={decimal2}
            />
          </div>
        </div>
        <div className="wall-sit__pulse">
          <div className="wall-sit__pulse-item">
            <span>HIGH+</span>
            <AnimatedNumber
              className={`mono ${highAlerts.length ? "wall-neg" : "wall-pos"}`}
              value={highAlerts.length}
              format={integer}
            />
          </div>
          <div className="wall-sit__pulse-item">
            <span>告警总数</span>
            <AnimatedNumber
              className="mono"
              value={data.alerts.length}
              format={integer}
            />
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
            <div className="wall-tabs wall-tabs--sentiment" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={rankMode === "negative"}
                className={
                  rankMode === "negative" ? "is-active is-negative" : undefined
                }
                onClick={() => changeRankMode("negative")}
              >
                差评榜
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={rankMode === "positive"}
                className={
                  rankMode === "positive" ? "is-active is-positive" : undefined
                }
                onClick={() => changeRankMode("positive")}
              >
                好评榜
              </button>
            </div>
          </header>
          <div
            className={`wall-risk wall-risk--${rankPhase} ${
              positiveRanking ? "is-positive" : "is-negative"
            }`}
          >
            <div className="wall-risk__col" data-agent-target="stores">
              <h3>店铺 TOP</h3>
              <ol>
                {rankedStores.slice(0, 8).map((s, i) => (
                  <li
                    key={s.store_key}
                    className={i === 0 ? "is-top-one" : undefined}
                    style={
                      {
                        "--row-delay": `${i * 55}ms`,
                        "--rate": `${Math.max(
                          0,
                          Math.min(
                            100,
                            Number(
                              positiveRanking
                                ? s.positive_rate
                                : s.negative_rate,
                            ) * 100,
                          ),
                        )}%`,
                      } as CSSProperties
                    }
                  >
                    <span className="wall-rank mono">{i + 1}</span>
                    <span className="wall-risk-name" title={s.store_name}>
                      {truncate(s.store_name, 22)}
                    </span>
                    <span
                      className={`mono ${
                        positiveRanking ? "wall-pos" : "wall-neg"
                      }`}
                    >
                      {pct(
                        positiveRanking ? s.positive_rate : s.negative_rate,
                      )}
                    </span>
                    <span className="mono wall-dim">n={s.review_count}</span>
                    <i className="wall-risk__progress" aria-hidden />
                  </li>
                ))}
              </ol>
            </div>
            <div className="wall-risk__col" data-agent-target="products">
              <h3>商品 TOP</h3>
              <ol>
                {rankedProducts.slice(0, 8).map((p, i) => (
                  <li
                    key={p.parent_asin}
                    className={i === 0 ? "is-top-one" : undefined}
                    style={
                      {
                        "--row-delay": `${i * 55}ms`,
                        "--rate": `${Math.max(
                          0,
                          Math.min(
                            100,
                            Number(
                              positiveRanking
                                ? p.positive_rate
                                : p.negative_rate,
                            ) * 100,
                          ),
                        )}%`,
                      } as CSSProperties
                    }
                  >
                    <span className="wall-rank mono">{i + 1}</span>
                    <span className="wall-risk-name mono" title={p.product_title}>
                      {p.parent_asin}
                    </span>
                    <span
                      className={`mono ${
                        positiveRanking ? "wall-pos" : "wall-neg"
                      }`}
                    >
                      {pct(
                        positiveRanking ? p.positive_rate : p.negative_rate,
                      )}
                    </span>
                    <span className="mono wall-dim">n={p.review_count}</span>
                    <i className="wall-risk__progress" aria-hidden />
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        <section
          className="wall-pane wall-pane--trend"
          aria-label="情感时间河"
          data-agent-target="trend"
        >
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

        <section
          className="wall-pane wall-pane--alerts"
          aria-label="告警雷达"
          data-agent-target="alerts"
        >
          <header className="wall-pane__head">
            <h2>告警雷达</h2>
            <span className={highAlerts.length ? "wall-neg" : undefined}>
              <AnimatedNumber value={highAlerts.length} format={integer} /> HIGH+
            </span>
          </header>
          <ul className="wall-alert-rail">
            {(data.alerts.length ? data.alerts : []).slice(0, 12).map((a, index) => (
              <li
                key={a.alert_id}
                className={`wall-alert-rail__item wall-alert-rail__item--${String(
                  a.alert_level,
                ).toLowerCase()}`}
                style={{ "--row-delay": `${index * 70}ms` } as CSSProperties}
              >
                <div className="wall-alert-rail__top">
                  <em>
                    <i className="wall-alert-pulse" aria-hidden />
                    {a.alert_level}
                  </em>
                  <span className="mono">{a.alert_type}</span>
                </div>
                <p title={a.alert_message}>{a.alert_message}</p>
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
        <div className="wall-qa__matrix" data-agent-target="rating">
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
        <div className="wall-qa__conf" data-agent-target="confidence">
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
        <div className="wall-qa__aspects" data-agent-target="aspects">
          <header className="wall-pane__head">
            <h2>负面方面</h2>
            <span className="wall-rule-badge">
              keyword_rules_v1 · 规则抽取（非 LLM）
            </span>
          </header>
          <ul className="wall-aspect-list">
            {data.aspects.slice(0, 8).map((a, index) => {
              const total = Math.max(0, Number(a.mention_count || 0));
              const positiveRate =
                a.positive_rate ?? (total ? a.positive_count / total : 0);
              const neutralRate =
                a.neutral_rate ?? (total ? a.neutral_count / total : 0);
              const negativeRate =
                a.negative_rate ?? (total ? a.negative_count / total : 0);
              const tooltip = [
                `mention_count: ${integer(total)}`,
                `product_count: ${integer(Number(a.product_count || 0))}`,
                `positive_rate: ${percentage(positiveRate)}`,
                `neutral_rate: ${percentage(neutralRate)}`,
                `negative_rate: ${percentage(negativeRate)}`,
              ].join("\n");
              return (
              <li
                key={a.aspect}
                title={tooltip}
                style={
                  {
                    "--row-delay": `${index * 65}ms`,
                    "--aspect-rate": `${Math.max(
                      0,
                      Math.min(100, negativeRate * 100),
                    )}%`,
                  } as CSSProperties
                }
              >
                <span title={a.aspect}>{truncate(String(a.aspect), 18)}</span>
                <AnimatedNumber
                  className="mono wall-neg"
                  value={a.negative_count}
                  format={integer}
                />
                <i className="wall-aspect-progress" aria-hidden />
              </li>
              );
            })}
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

      {!agentOpen ? (
        <AgentLauncher open={false} onClick={() => setAgentOpen(true)} />
      ) : null}
      <AgentDrawer
        open={agentOpen}
        health={data.health}
        onClose={() => setAgentOpen(false)}
        onFocus={focusEvidence}
      />
    </div>
  );
}
