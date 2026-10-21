// Single place where the frontend talks to the backend.
// The frontend never imports backend code; it only calls the REST API (see docs/API.md).

import { MOCK_ME, MOCK_PLANS, MOCK_QUESTIONS, MOCK_STATUS } from "./mock";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

// Free-tier backend may need ~50 s to wake up, so allow a long timeout.
const TIMEOUT_MS = 70_000;
const TOKEN_KEY = "nirikkha.token";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// ---------- types (mirror docs/API.md) ----------
export type ServerHealth = { status: string; app: string; version: string; env: string; time_utc: string;
  providers_configured: Record<string, boolean> };
export type Status = { live_mode: "inline" | "worker"; worker_online: boolean;
  worker: { last_seen: string; busy: boolean } | null; rerank_enabled: boolean | null };
export type Role = "user" | "demo" | "admin";
export type PlanId = "free" | "analyst_pro" | "team" | "enterprise";
export type User = { id: string; email: string; name: string; organization: string | null; job_role: string | null;
  role: Role; plan: PlanId; created_at: string };
export type Usage = { used_this_month: number; limit: number | null; unlimited: boolean; remaining: number | null };
export type Session = { token: string; user: User };
export type MeResponse = { user: User; usage: Usage };
export type Plan = { id: PlanId; name: string; audience: string; price_usd: number | null; price_unit: string;
  price_label: string; crash_tests_per_month: number | null; radar_companies: number | null; features: string[] };
export type AddOn = { id: string; name: string; price_usd: number; description: string };
export type PlansResponse = { currency: string; plans: Plan[]; add_ons: AddOn[]; note: string };
export type SignupInput = { name: string; email: string; password: string; date_of_birth: string;
  security_question: string; security_answer: string; organization?: string; job_role?: string };

// ---------- token ----------
export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage blocked: the session lasts until the page closes */
  }
}

// ---------- request helper ----------
async function request<T>(path: string, options: { method?: string; body?: unknown; auth?: boolean; token?: string } = {}): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = options.token ?? (options.auth === false ? null : getToken());
  if (token) headers.Authorization = `Bearer ${token}`;
  try {
    const res = await fetch(`${API_URL}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: controller.signal,
      cache: "no-store",
    });
    if (!res.ok) {
      let detail = `Request failed (HTTP ${res.status}).`;
      try {
        const data = await res.json();
        if (typeof data.detail === "string") detail = data.detail;
        else if (Array.isArray(data.detail)) detail = data.detail.map((d: { msg?: string }) => d.msg).join("; ");
      } catch {
        /* not JSON */
      }
      throw new ApiError(res.status, detail);
    }
    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(0, "The server took too long to answer. It may be waking up; please try again.");
    }
    throw new ApiError(0, "Cannot reach the server. Check your connection and try again.");
  } finally {
    clearTimeout(timer);
  }
}

function mockUnavailable(): never {
  throw new ApiError(503, "Not available in mock mode.");
}

// ---------- endpoints ----------
export async function getHealth(): Promise<ServerHealth> {
  if (USE_MOCK) return { status: "ok", app: "Nirikkha", version: "mock", env: "mock",
    time_utc: new Date().toISOString(), providers_configured: {} };
  return request<ServerHealth>("/health", { auth: false });
}

export async function getStatus(): Promise<Status> {
  if (USE_MOCK) return MOCK_STATUS;
  return request<Status>("/api/status", { auth: false });
}

export async function getPlans(): Promise<PlansResponse> {
  if (USE_MOCK) return { currency: "USD", plans: MOCK_PLANS, add_ons: [], note: "Mock data." };
  return request<PlansResponse>("/api/plans", { auth: false });
}

export async function getQuestions(): Promise<string[]> {
  if (USE_MOCK) return MOCK_QUESTIONS;
  return request<string[]>("/api/auth/questions", { auth: false });
}

export async function signup(input: SignupInput): Promise<Session> {
  if (USE_MOCK) mockUnavailable();
  return request<Session>("/api/auth/signup", { method: "POST", body: input, auth: false });
}

export async function login(email: string, password: string): Promise<Session> {
  if (USE_MOCK) mockUnavailable();
  return request<Session>("/api/auth/login", { method: "POST", body: { email, password }, auth: false });
}

export async function demoLogin(): Promise<Session> {
  if (USE_MOCK) return { token: "mock", user: MOCK_ME.user };
  return request<Session>("/api/auth/demo", { method: "POST", auth: false });
}

export async function forgotPassword(email: string): Promise<{ question: string }> {
  if (USE_MOCK) return { question: MOCK_QUESTIONS[0] };
  return request<{ question: string }>("/api/auth/forgot", { method: "POST", body: { email }, auth: false });
}

export async function resetPassword(email: string, answer: string, new_password: string): Promise<Session> {
  if (USE_MOCK) mockUnavailable();
  return request<Session>("/api/auth/reset", { method: "POST", body: { email, answer, new_password }, auth: false });
}

export async function getMe(): Promise<MeResponse> {
  if (USE_MOCK) return MOCK_ME;
  return request<MeResponse>("/api/auth/me");
}

export async function requestPlan(plan: PlanId, kind: "upgrade" | "pilot", note?: string) {
  if (USE_MOCK) return { id: "mock", status: "open", message: "Mock mode: request not sent." };
  return request<{ id: string; status: string; message: string }>("/api/plans/request",
    { method: "POST", body: { plan, kind, note } });
}

// ---------- crash-tests ----------
export type CrashTestSummary = { id: string; cik: string; as_of: string; decision: string; source: string;
  updated_at: string; has_memo: boolean; score: number | null; band: string | null; coverage_pct: number | null };
export type Company = { cik: string; company: string; filing_count: number; chunk_count: number;
  filings: { accession_no: string; form: string; filing_date: string; has_page_markers: boolean; url: string }[];
  crash_tests: CrashTestSummary[] };
export type JobStatus = "queued" | "running" | "done" | "failed" | "blocked";
export type PipelineEvent = { node: string; message: string; ms: number; model?: string };
export type HealthFactor = { id: string; title: string; investigation: string; severity: string; confidence: string;
  points: number; human_review: boolean };
export type Health = { score: number; band: string; deducted: number; formula: string;
  coverage: { pct: number; label: string; rules_resolved: number; rules_total: number; questions_credit: number;
              questions_total: number };
  factors: HealthFactor[]; by_investigation: Record<string, { raw: number; deducted: number; capped: boolean }>;
  insufficient_evidence: { count: number; items: { id: string; title: string; severity: string }[] };
  excluded: { id: string; title: string; reason: string }[]; human_review: number; warnings: string[] };
export type Report = { company: string; cik: string; as_of: string; decision: string; health?: Health;
  summary?: { findings: number; sentinel?: { verified: number; needs_review: number; downgraded: number; unsupported: number;
    human_review: number; judge_model: string | null } }; retrieval_mode?: string;
  usage?: { llm_calls: number; input_tokens: number; output_tokens: number; cost_usd: number };
  [key: string]: unknown };
export type CrashTestJob = { id: string; cik: string; as_of: string; decision: string; status: JobStatus;
  pipeline: string[]; done_nodes: string[]; events: PipelineEvent[]; report: Report | null; error: string | null;
  source: string; created_at: string; updated_at: string; worker_online?: boolean };
export type CrashTestStarted = { id: string; status: JobStatus; cached: boolean; worker_online: boolean | null };

export async function getCompanies(): Promise<Company[]> {
  if (USE_MOCK) return [];
  return request<Company[]>("/api/companies", { auth: false });
}

export async function startCrashTest(cik: string, as_of: string, decision: string): Promise<CrashTestStarted> {
  if (USE_MOCK) mockUnavailable();
  return request<CrashTestStarted>("/api/crash-tests", { method: "POST", body: { cik, as_of, decision } });
}

export async function getCrashTest(id: string): Promise<CrashTestJob> {
  if (USE_MOCK) mockUnavailable();
  return request<CrashTestJob>(`/api/crash-tests/${encodeURIComponent(id)}`, { auth: false });
}

// ---------- admin (step-up token kept in memory by the admin page) ----------
export type AdminOverview = {
  accounts: { role: string; plan: string; n: number }[];
  signups: { users: number; last_30_days: number } | null;
  crash_tests_by_status: { status: string; n: number }[];
  crash_tests_this_month: number;
  open_plan_requests: number;
  simulated_payments?: { n: number; total_usd: number } | null;
  model_usage: { model: string; node: string; calls: number; input_tokens: number; output_tokens: number; avg_latency_ms: number }[];
  users_by_plan: Record<string, number>;
  projected_revenue: { total_monthly_usd: number; label: string;
    lines: { plan: string; accounts: number; monthly_usd: number | null; note?: string }[] };
  unit_economics: {
    measured: { crash_tests: number; avg_tokens: number | null; avg_llm_calls: number | null; avg_seconds: number | null;
                infra_cost_usd_total: number };
    revenue_per_crash_test: { plan: string; revenue_per_crash_test_usd: number }[];
    note: string;
  };
};
export type AdminDemo = { id: string; cik: string; company: string; as_of: string; decision: string; featured: boolean;
  source: string; updated_at: string; score: number | null; band: string | null; email: string | null };

export async function adminSession(password: string): Promise<{ token: string; expires_in: number }> {
  return request("/api/admin/session", { method: "POST", body: { password } });
}
export async function adminOverview(token: string): Promise<AdminOverview> {
  return request<AdminOverview>("/api/admin/overview", { token });
}
export async function adminDemos(token: string): Promise<AdminDemo[]> {
  return request<AdminDemo[]>("/api/admin/demos", { token });
}
export async function adminSetDemo(token: string, id: string, featured: boolean): Promise<{ id: string; featured: boolean }> {
  return request(`/api/admin/demos/${encodeURIComponent(id)}`, { method: "POST", body: { featured }, token });
}

// ---------- demo checkout (no money is charged; no card/account/PIN data is ever sent) ----------
export type CheckoutMethod = "mobile_banking" | "card" | "bank_transfer";
export type PaymentRecord = { id: string; plan: PlanId; method: CheckoutMethod | "none"; amount_usd: number; reference: string;
  status: string; created_at: string; plan_name?: string; simulated?: boolean; note?: string };

export async function checkout(plan: PlanId, method: CheckoutMethod): Promise<PaymentRecord> {
  if (USE_MOCK) mockUnavailable();
  return request<PaymentRecord>("/api/billing/checkout", { method: "POST", body: { plan, method } });
}
export async function cancelPlan(): Promise<PaymentRecord> {
  if (USE_MOCK) mockUnavailable();
  return request<PaymentRecord>("/api/billing/cancel", { method: "POST" });
}
