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
