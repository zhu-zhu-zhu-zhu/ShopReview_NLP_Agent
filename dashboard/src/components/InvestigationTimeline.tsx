import { pct, truncate } from "../labels";
import type { InvestigationResult } from "../agentTypes";
import { EvidenceCard } from "./EvidenceCard";
import { SourceBadge } from "./SourceBadge";

type Props = {
  result: InvestigationResult;
  onFocus: (target: InvestigationResult["target"]) => void;
};

const emptyText = "本次调查未返回该类证据，不做推断。";

export function InvestigationTimeline({ result, onFocus }: Props) {
  return (
    <section className="investigation-result" aria-live="polite">
      <div className="investigation-result__head">
        <div>
          <span>INVESTIGATION COMPLETE</span>
          <time dateTime={result.generatedAt}>
            {new Date(result.generatedAt).toLocaleString("zh-CN", {
              hour12: false,
            })}
          </time>
        </div>
        <button type="button" onClick={() => onFocus(result.target)}>
          定位大屏证据
        </button>
      </div>

      <div className="investigation-timeline">
        <EvidenceCard step={1} title="调查结论" tag={result.agentMode || "GET EVIDENCE"}>
          <p className="evidence-conclusion">{result.conclusion}</p>
        </EvidenceCard>

        <EvidenceCard step={2} title="风险对象" tag={result.riskObject.kind}>
          <div className="risk-object-card">
            <span>{result.riskObject.kind}</span>
            <strong>{result.riskObject.name}</strong>
            <code>{result.riskObject.id}</code>
            {result.riskObject.detail ? <small>{result.riskObject.detail}</small> : null}
          </div>
        </EvidenceCard>

        <EvidenceCard step={3} title="核心指标">
          {result.metrics.length ? (
            <div className="evidence-metrics">
              {result.metrics.map((metric) => (
                <div key={metric.label} className={`tone-${metric.tone || "agent"}`}>
                  <span>{metric.label}</span>
                  <strong className="mono">{metric.value}</strong>
                </div>
              ))}
            </div>
          ) : (
            <p className="evidence-empty">{emptyText}</p>
          )}
          {result.ranking.length ? (
            <ol className="evidence-ranking">
              {result.ranking.map((row, index) => (
                <li key={row.id}>
                  <b className="mono">{index + 1}</b>
                  <span title={row.name}>{truncate(row.name, 26)}</span>
                  <strong className="mono">{pct(row.value)}</strong>
                  <small className="mono">n={row.count}</small>
                </li>
              ))}
            </ol>
          ) : null}
        </EvidenceCard>

        <EvidenceCard
          step={4}
          title="告警证据"
          tag={result.alerts.length ? `${result.alerts.length} 条` : "无匹配"}
          empty={!result.alerts.length}
        >
          {result.alerts.length ? (
            <ul className="evidence-alerts">
              {result.alerts.slice(0, 5).map((alert) => (
                <li key={alert.alert_id} data-level={alert.alert_level.toUpperCase()}>
                  <div>
                    <em>{alert.alert_level}</em>
                    <span className="mono">{alert.alert_type}</span>
                  </div>
                  <p>{alert.alert_message}</p>
                  <small className="mono">
                    {alert.entity_name || alert.entity_id} · {alert.metric_name}{" "}
                    {pct(alert.metric_value)}
                  </small>
                </li>
              ))}
            </ul>
          ) : (
            <p className="evidence-empty">{emptyText}</p>
          )}
        </EvidenceCard>

        <EvidenceCard
          step={5}
          title="负面方面"
          tag="keyword_rules_v1"
          empty={!result.aspects.length}
        >
          {result.aspects.length ? (
            <div className="evidence-bars">
              {result.aspects.slice(0, 6).map((aspect) => (
                <div key={aspect.aspect}>
                  <span>{aspect.aspect}</span>
                  <div>
                    <i style={{ width: `${Math.min(100, aspect.negative_rate * 100)}%` }} />
                  </div>
                  <strong className="mono">{pct(aspect.negative_rate)}</strong>
                </div>
              ))}
            </div>
          ) : (
            <p className="evidence-empty">{emptyText}</p>
          )}
        </EvidenceCard>

        <EvidenceCard
          step={6}
          title="全局差评原因"
          tag="keyword_rules_v1 · 全局粒度"
          empty={!result.reasons.length}
        >
          {result.reasons.length ? (
            <>
              <p className="evidence-scope-note">
                仅表示当前批次全局规则命中分布，不归因到单个商品，也不是 LLM 抽取。
              </p>
              <div className="evidence-bars evidence-bars--reason">
                {result.reasons.slice(0, 6).map((reason) => (
                  <div key={reason.reason_code}>
                    <span>{reason.reason_name}</span>
                    <div>
                      <i
                        style={{
                          width: `${Math.min(100, reason.reason_share * 100)}%`,
                        }}
                      />
                    </div>
                    <strong className="mono">{pct(reason.reason_share)}</strong>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="evidence-empty">{emptyText}</p>
          )}
        </EvidenceCard>

        <EvidenceCard
          step={7}
          title="脱敏评论样例"
          tag="preview only"
          empty={!result.samples.length}
        >
          {result.samples.length ? (
            <div className="evidence-samples">
              {result.samples.slice(0, 3).map((sample) => (
                <blockquote key={sample.sample_id}>
                  <p>{sample.review_text_preview || "（无文本预览）"}</p>
                  <footer className="mono">
                    {sample.parent_asin || "—"} · ★{sample.rating} ·{" "}
                    {sample.pred_label} {pct(sample.pred_score)}
                  </footer>
                </blockquote>
              ))}
            </div>
          ) : (
            <p className="evidence-empty">{emptyText}</p>
          )}
        </EvidenceCard>

        <EvidenceCard step={8} title="数据来源" tag={`${result.sources.length} APIs`}>
          <div className="evidence-sources">
            {result.sources.map((source) => (
              <SourceBadge key={source.api} source={source} />
            ))}
          </div>
        </EvidenceCard>

        <EvidenceCard step={9} title="建议动作">
          <ol className="evidence-actions">
            {result.recommendation.map((action, index) => (
              <li key={action}>
                <b>{index + 1}</b>
                <span>{action}</span>
              </li>
            ))}
          </ol>
          {result.agentSteps?.length ? (
            <details className="agent-tool-trace">
              <summary>查看自然语言 Agent 工具轨迹</summary>
              <ul>
                {result.agentSteps.map((step, index) => (
                  <li key={`${step.tool}-${index}`}>
                    <span className={step.ok ? "is-ok" : "is-bad"} />
                    <code>{step.tool}</code>
                    <p>{step.summary}</p>
                    <small>{step.source}</small>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </EvidenceCard>
      </div>
    </section>
  );
}
