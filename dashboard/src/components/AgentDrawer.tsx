import { useEffect, useId, useRef, useState } from "react";
import { ApiError, fetchAgentChat, getApiBase } from "../api";
import type { AgentChatResponse, AgentStep } from "../agentTypes";
import { DEMO_SCRIPTS } from "../demoScripts";

type Props = {
  open: boolean;
  onClose: () => void;
  dataModeHint?: string;
};

function lightFormat(text: string): string {
  // Escape then apply a few markdown-ish replacements for readability.
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return escaped
    .replace(/^### (.+)$/gm, "<strong>$1</strong>")
    .replace(/^## (.+)$/gm, "<strong>$1</strong>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n/g, "<br />");
}

export function AgentDrawer({ open, onClose, dataModeHint }: Props) {
  const titleId = useId();
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [question, setQuestion] = useState<string>(DEMO_SCRIPTS[0].question);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rawOpen, setRawOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const t = window.setTimeout(() => inputRef.current?.focus(), 50);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.clearTimeout(t);
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  async function send(q?: string) {
    const text = (q ?? question).trim();
    if (!text || loading) return;
    setQuestion(text);
    setLoading(true);
    setError(null);
    setRawOpen(false);
    try {
      const res = await fetchAgentChat(text);
      setResult(res);
      if (res.error && res.ok === false && !res.answer) {
        setError(res.error);
      }
    } catch (err) {
      setResult(null);
      setError(err instanceof ApiError ? err.message : "问答失败");
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  const modeLabel = result?.data_mode || dataModeHint || "—";

  return (
    <div className="agent-overlay" role="presentation" onClick={onClose}>
      <aside
        className="agent-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="agent-drawer__head">
          <div>
            <p className="eyebrow">Intelligent Q&A</p>
            <h2 id={titleId}>智能问答</h2>
          </div>
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            关闭
          </button>
        </header>

        <p className="agent-drawer__meta">
          API <span className="mono">{getApiBase()}/api/agent/chat</span>
          {" · "}
          data_mode <span className="mono">{modeLabel}</span>
          {" · "}
          mode <span className="mono">{result?.mode || "llm"}</span>
        </p>

        <div className="agent-chips" aria-label="答辩剧本">
          {DEMO_SCRIPTS.map((script) => (
            <button
              key={script.id}
              type="button"
              className="agent-chip"
              disabled={loading}
              onClick={() => {
                setQuestion(script.question);
                void send(script.question);
              }}
            >
              {script.label}
            </button>
          ))}
        </div>

        <label className="agent-label" htmlFor="agent-q">
          问题
        </label>
        <textarea
          id="agent-q"
          ref={inputRef}
          className="agent-input"
          rows={3}
          value={question}
          disabled={loading}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
          placeholder="输入问题，Enter 发送，Shift+Enter 换行"
        />

        <div className="agent-actions">
          <button
            type="button"
            className="btn"
            disabled={loading || !question.trim()}
            onClick={() => void send()}
          >
            {loading ? "思考与取数中…" : "发送"}
          </button>
        </div>

        {loading && (
          <div className="agent-loading" aria-live="polite">
            正在调用大模型与白名单工具，通常需要数十秒…
          </div>
        )}

        {error && (
          <div className="banner banner--error agent-banner" role="alert">
            <strong>问答失败</strong>
            <p>{error}</p>
          </div>
        )}

        {result && (
          <div className="agent-result">
            {result.error && (
              <p className="agent-error-tag mono">error={result.error}</p>
            )}

            <h3 className="agent-section-title">Tool steps</h3>
            {result.steps?.length ? (
              <ul className="agent-steps">
                {result.steps.map((step: AgentStep, idx: number) => (
                  <li
                    key={`${step.tool}-${idx}`}
                    className={`agent-step ${step.ok ? "agent-step--ok" : "agent-step--bad"}`}
                    title={step.source}
                  >
                    <span className="agent-step__dot" aria-hidden />
                    <span className="agent-step__tool mono">{step.tool}</span>
                    <span className="agent-step__summary">{step.summary}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="agent-empty">本次无 tool call（若问数却为空，请检查模型/提示词）</p>
            )}

            <h3 className="agent-section-title">Answer</h3>
            <div
              className="agent-answer"
              dangerouslySetInnerHTML={{
                __html: lightFormat(result.answer || "（无文本）"),
              }}
            />

            <button
              type="button"
              className="btn btn--ghost agent-raw-toggle"
              onClick={() => setRawOpen((v) => !v)}
            >
              {rawOpen ? "收起原始 JSON" : "展开原始 JSON"}
            </button>
            {rawOpen && (
              <pre className="agent-raw mono">{JSON.stringify(result, null, 2)}</pre>
            )}
          </div>
        )}
      </aside>
    </div>
  );
}
