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
export type Health = { status: string; app: string; version: string; env: string; time_utc: string;
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
async function request<T>(path: string, options: { method?: string; body?: unknown; auth?: boolean } = {}): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = options.auth === false ? null : getToken();
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
export async function getHealth(): Promise<Health> {
  if (USE_MOCK) return { status: "ok", app: "Nirikkha", version: "mock", env: "mock",
    time_utc: new Date().toISOString(), providers_configured: {} };
  return request<Health>("/health", { auth: false });
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