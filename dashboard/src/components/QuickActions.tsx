import type { InvestigationKind } from "../agentTypes";

const ACTIONS: Array<{
  kind: InvestigationKind;
  label: string;
  icon: string;
}> = [
  { kind: "product", label: "调查最高风险商品", icon: "P" },
  { kind: "store", label: "调查最高风险店铺", icon: "S" },
  { kind: "alerts", label: "查看 HIGH 告警", icon: "!" },
  { kind: "reasons", label: "分析主要差评原因", icon: "R" },
  { kind: "confidence", label: "检查模型置信度", icon: "C" },
  { kind: "summary", label: "生成当前批次总结", icon: "Σ" },
];

type Props = {
  loading: boolean;
  disabled?: boolean;
  onRun: (kind: InvestigationKind) => void;
};

export function QuickActions({ loading, disabled, onRun }: Props) {
  return (
    <section className="reviewops-quick" aria-label="快捷调查">
      <div className="reviewops-section-label">
        <span>QUICK INVESTIGATION</span>
        <em>真实 GET API</em>
      </div>
      <div className="reviewops-quick__grid">
        {ACTIONS.map((action) => (
          <button
            key={action.kind}
            type="button"
            disabled={loading || disabled}
            onClick={() => onRun(action.kind)}
          >
            <i aria-hidden>{action.icon}</i>
            <span>{action.label}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
