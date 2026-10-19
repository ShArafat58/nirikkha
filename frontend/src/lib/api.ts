// Single place where the frontend talks to the backend.
// The frontend never imports backend code; it only calls the REST API (see docs/API.md).

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

export type Health = {
  status: string;
  app: string;
  version: string;
  env: string;
  time_utc: string;
  providers_configured: Record<string, boolean>;
};

const MOCK_HEALTH: Health = {
  status: "ok",
  app: "Nirikkha",
  version: "mock",
  env: "mock",
  time_utc: new Date().toISOString(),
  providers_configured: { groq: true, gemini: true, neo4j: true },
};

// Free-tier backend may need ~50 s to wake up, so allow a long timeout.
const TIMEOUT_MS = 70_000;

export async function getHealth(): Promise<Health> {
  if (USE_MOCK) return MOCK_HEALTH;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${API_URL}/health`, { signal: controller.signal, cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as Health;
  } finally {
    clearTimeout(timer);
  }
}