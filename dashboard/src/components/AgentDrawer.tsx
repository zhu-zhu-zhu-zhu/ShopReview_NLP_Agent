import { useEffect, useId, useRef, useState } from "react";
import { ApiError, fetchAgentChat, getApiBase } from "../api";
import type {
  DashboardTarget,
  InvestigationKind,
  InvestigationResult,
} from "../agentTypes";
import type { HealthPayload } from "../types";
import {
  inferInvestigationKind,
  runInvestigation,
} from "../investigation";
import { InvestigationTimeline } from "./InvestigationTimeline";
import { QuickActions } from "./QuickActions";
import "./agent.css";

type Props = {
  open: boolean;
  health: HealthPayload;
  onClose: () => void;
  onFocus: (target: DashboardTarget) => void;
};

type LastRun =
  | { mode: "quick"; kind: InvestigationKind }
  | { mode: "chat"; question: string };

export function AgentDrawer({ open, health, onClose, onFocus }: Props) {
  const titleId = useId();
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [agentUnavailable, setAgentUnavailable] = useState(false);
  const [lastRun, setLastRun] = useState<LastRun | null>(null);

  const warehouseReady =
    health.ok &&
    health.data_mode === "warehouse" &&
    health.production_business_metrics;

  useEffect(() => {
    if (!open) return;
    const focusTimer = window.setTimeout(() => inputRef.current?.focus(), 80);
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.clearTimeout(focusTimer);
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  async function runQuick(kind: InvestigationKind) {
    if (loading) return;
    setLoading(true);
    setError(null);
    setLastRun({ mode: "quick", kind });
    try {
      const next = await runInvestigation(kind, health);
      setResult(next);
      onFocus(next.target);
    } catch (err) {
      setError(err instanceof Error ? err.message : "快捷调查失败");
    } finally {
      setLoading(false);
    }
  }

  async function runChat(textOverride?: string) {
    const text = (textOverride ?? question).trim();
    if (!text || loading) return;
    setQuestion(text);
    setLoading(true);
    setError(null);
    setAgentUnavailable(false);
    setLastRun({ mode: "chat", question: text });
    try {
      const agent = await fetchAgentChat(text);
      if (agent.ok === false || agent.error || !agent.answer) {
        throw new ApiError(
          agent.error || "自然语言 Agent 暂不可用",
          503,
        );
      }
      const kind = inferInvestigationKind(text);
      const evidence = await runInvestigation(kind, health, text);
      evidence.conclusion = agent.answer;
      evidence.agentMode = agent.mode || "llm";
      evidence.agentSteps = agent.steps || [];
      setResult(evidence);
      onFocus(evidence.target);
    } catch (err) {
      setAgentUnavailable(true);
      setError(
        err instanceof ApiError
          ? `自然语言 Agent 暂不可用：${err.message}`
          : err instanceof Error
            ? err.message
            : "自然语言 Agent 暂不可用",
      );
    } finally {
      setLoading(false);
    }
  }

  function retry() {
    if (!lastRun) return;
    if (lastRun.mode === "quick") void runQuick(lastRun.kind);
    else void runChat(lastRun.question);
  }

  if (!open) return null;

  return (
    <div className="reviewops-shell">
      <aside
        id="reviewops-drawer"
        className="reviewops-drawer"
        role="dialog"
        aria-modal="false"
        aria-labelledby={titleId}
      >
        <header className="reviewops-drawer__head">
          <div>
            <p>INTELLIGENCE / EVIDENCE / ACTION</p>
            <h2 id={titleId}>ReviewOps Copilot</h2>
            <span>智能风险调查</span>
          </div>
          <button type="button" aria-label="关闭调查面板" onClick={onClose}>
            ×
          </button>
        </header>

        <div className="reviewops-health">
          <div>
            <span className={health.ok ? "is-online" : "is-offline"} />
            <small>BACKEND</small>
            <strong>{health.ok ? "ONLINE" : "UNAVAILABLE"}</strong>
          </div>
          <div>
            <small>DATA_MODE</small>
            <strong className="mono">{health.data_mode || "—"}</strong>
          </div>
          <div>
            <small>LOAD BATCH</small>
            <strong className="mono">{health.load_batch_id || "—"}</strong>
          </div>
          <div>
            <small>MODEL</small>
            <strong className="mono">{health.model_version || "—"}</strong>
          </div>
        </div>

        {!warehouseReady ? (
          <div className="reviewops-state reviewops-state--error" role="alert">
            <strong>生产 warehouse 数据不可用</strong>
            <p>
              当前 DATA_MODE 为 {health.data_mode || "unknown"}。为避免使用非生产
              数据，调查功能已停止。
            </p>
          </div>
        ) : null}

        <QuickActions
          loading={loading}
          disabled={!warehouseReady}
          onRun={(kind) => void runQuick(kind)}
        />

        <section className="reviewops-query">
          <div className="reviewops-section-label">
            <span>NATURAL LANGUAGE</span>
            <em className={agentUnavailable ? "is-unavailable" : ""}>
              {agentUnavailable ? "AGENT UNAVAILABLE" : "/api/agent/chat"}
            </em>
          </div>
          <div className="reviewops-query__box">
            <textarea
              ref={inputRef}
              value={question}
              rows={2}
              disabled={loading || !warehouseReady}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void runChat();
                }
              }}
              placeholder="例如：一星评论和模型预测是否一致？"
              aria-label="风险调查问题"
            />
            <button
              type="button"
              disabled={loading || !warehouseReady || !question.trim()}
              onClick={() => void runChat()}
            >
              调查
            </button>
          </div>
          <small>
            自由提问调用 {getApiBase()}/api/agent/chat；失败时快捷调查仍直接使用
            warehouse GET API。
          </small>
        </section>

        {loading ? (
          <div className="reviewops-state reviewops-state--progress" aria-live="polite">
            <span className="reviewops-spinner" aria-hidden />
            <div>
              <strong>正在构建证据链</strong>
              <ol className="reviewops-progress" aria-label="调查进度">
                <li>读取数据</li>
                <li>分析风险</li>
                <li>整理证据</li>
                <li>生成结论</li>
              </ol>
            </div>
          </div>
        ) : null}

        {error ? (
          <div className="reviewops-state reviewops-state--error" role="alert">
            <div>
              <strong>{agentUnavailable ? "自然语言 Agent 暂不可用" : "调查失败"}</strong>
              <p>{error}</p>
              {agentUnavailable ? (
                <small>上方快捷调查不依赖 LLM，仍可正常使用。</small>
              ) : null}
            </div>
            <button type="button" onClick={retry}>
              重试
            </button>
          </div>
        ) : null}

        {!loading && !error && !result ? (
          <div className="reviewops-state reviewops-state--empty">
            <strong>等待调查指令</strong>
            <p>选择快捷调查，或输入一个与当前生产批次有关的问题。</p>
          </div>
        ) : null}

        {result ? <InvestigationTimeline result={result} onFocus={onFocus} /> : null}
      </aside>
    </div>
  );
}
