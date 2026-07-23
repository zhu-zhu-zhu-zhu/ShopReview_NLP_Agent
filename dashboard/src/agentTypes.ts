export type AgentStep = {
  tool: string;
  args: Record<string, unknown>;
  ok: boolean;
  summary: string;
  source: string;
};

export type AgentChatResponse = {
  ok?: boolean;
  answer: string;
  steps: AgentStep[];
  mode?: string;
  data_mode?: string;
  error?: string | null;
};

export type InvestigationKind =
  | "product"
  | "store"
  | "alerts"
  | "reasons"
  | "confidence"
  | "summary"
  | "trend"
  | "rating";

export type DashboardTarget =
  | "kpi"
  | "products"
  | "stores"
  | "trend"
  | "alerts"
  | "aspects"
  | "rating"
  | "confidence";

export type EvidenceMetric = {
  label: string;
  value: string;
  tone?: "agent" | "positive" | "neutral" | "negative" | "alert";
};

export type EvidenceSource = {
  api: string;
  source: string;
  load_batch_id: string;
  model_version: string;
  extraction_method: string;
  generated_at?: string;
};

export type RiskObject = {
  kind: "商品" | "店铺" | "全局";
  id: string;
  name: string;
  detail?: string;
};

export type InvestigationResult = {
  id: string;
  title: string;
  question: string;
  conclusion: string;
  riskObject: RiskObject;
  metrics: EvidenceMetric[];
  alerts: import("./types").AlertRow[];
  aspects: import("./types").AspectRow[];
  reasons: import("./types").ReasonRow[];
  samples: import("./types").SampleRow[];
  ranking: Array<{ name: string; value: number; count: number; id: string }>;
  sources: EvidenceSource[];
  recommendation: string[];
  target: DashboardTarget;
  generatedAt: string;
  agentMode?: string;
  agentSteps?: AgentStep[];
};
