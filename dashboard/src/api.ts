import type {
  AlertRow,
  AspectRow,
  CategoryRow,
  ConfidenceRow,
  HealthPayload,
  KpiRecord,
  MatrixCell,
  ProductRow,
  ReasonRow,
  SampleRow,
  StoreRow,
  TrendPoint,
  VerifiedRow,
  Wrapped,
} from "./types";
import type { AgentChatResponse } from "./agentTypes";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(
  /\/$/,
  "",
) || "http://127.0.0.1:8080";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function getJson<T>(path: string): Promise<T> {
  const url = `${API_BASE}${path}`;
  let response: Response;
  try {
    response = await fetch(url);
  } catch {
    throw new ApiError(
      `无法连接后端 ${API_BASE}。请先启动 backend\\start.bat`,
      0,
    );
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as {
        message?: string;
        detail?: { message?: string } | string;
      };
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else {
        detail = body.message || body.detail?.message || detail;
      }
    } catch {
      /* ignore */
    }
    throw new ApiError(`${path} → HTTP ${response.status}: ${detail}`, response.status);
  }
  return (await response.json()) as T;
}

async function getJsonOptional<T>(path: string): Promise<T | null> {
  const url = `${API_BASE}${path}`;
  let response: Response;
  try {
    response = await fetch(url);
  } catch {
    throw new ApiError(
      `无法连接后端 ${API_BASE}。请先启动 backend\\start.bat`,
      0,
    );
  }
  if (response.status === 501) return null;
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as {
        message?: string;
        detail?: { message?: string } | string;
      };
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else {
        detail = body.message || body.detail?.message || detail;
      }
    } catch {
      /* ignore */
    }
    throw new ApiError(`${path} → HTTP ${response.status}: ${detail}`, response.status);
  }
  return (await response.json()) as T;
}

export function getApiBase(): string {
  return API_BASE;
}

export const fetchHealth = () => getJson<HealthPayload>("/api/health");
export const fetchKpi = () => getJson<Wrapped<KpiRecord>>("/api/kpi");
export const fetchProducts = () =>
  getJson<Wrapped<ProductRow[]>>(
    "/api/top-negative-products?limit=10&min_reviews=20",
  );
export const fetchAspects = () =>
  getJsonOptional<Wrapped<AspectRow[]>>("/api/aspects");
export const fetchReasons = () =>
  getJsonOptional<Wrapped<ReasonRow[]>>("/api/negative-reasons?limit=20");
export const fetchDailyTrend = () =>
  getJsonOptional<Wrapped<TrendPoint[]>>("/api/trend?recent_days=365");
export const fetchMonthlyTrend = () =>
  getJsonOptional<Wrapped<TrendPoint[]>>("/api/trends/monthly");
export const fetchAlerts = () =>
  getJsonOptional<Wrapped<AlertRow[]>>("/api/alerts?limit=12");
export const fetchSamples = () =>
  getJsonOptional<Wrapped<SampleRow[]>>("/api/samples?limit=9");
export const fetchCategories = () =>
  getJsonOptional<Wrapped<CategoryRow[]>>("/api/categories");
export const fetchStores = () =>
  getJsonOptional<Wrapped<StoreRow[]>>("/api/stores?limit=10&min_reviews=20");
export const fetchVerified = () =>
  getJsonOptional<Wrapped<VerifiedRow[]>>("/api/verified-purchase");
export const fetchRatingMatrix = () =>
  getJsonOptional<Wrapped<MatrixCell[]>>("/api/rating-matrix");
export const fetchConfidence = () =>
  getJsonOptional<Wrapped<ConfidenceRow[]>>("/api/confidence");

export async function fetchAgentChat(question: string): Promise<AgentChatResponse> {
  const url = `${API_BASE}/api/agent/chat`;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 120_000);
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError("智能问答超时（120s）。请确认后端与 DeepSeek 网络可用。", 0);
    }
    throw new ApiError(
      `无法连接后端 ${API_BASE}。请先启动 backend\\start.bat`,
      0,
    );
  } finally {
    window.clearTimeout(timer);
  }

  let body: AgentChatResponse & {
    detail?: { message?: string; error?: string } | string;
    message?: string;
  };
  try {
    body = (await response.json()) as typeof body;
  } catch {
    throw new ApiError(
      `/api/agent/chat → HTTP ${response.status}: 非 JSON 响应`,
      response.status,
    );
  }

  if (!response.ok) {
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : body.detail?.message || body.message || response.statusText;
    throw new ApiError(
      `/api/agent/chat → HTTP ${response.status}: ${detail}`,
      response.status,
    );
  }

  return body;
}
