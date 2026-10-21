// Legal memo for a finished Crash-Test (English draft + cached Bengali translation).
import { API_URL } from "./api";

export type MemoResponse = { cached: boolean; memo: Record<string, unknown>; markdown: string; markdown_bn?: string | null };

async function call<T>(path: string, method: "GET" | "POST", allow404 = false): Promise<T | null> {
  const res = await fetch(`${API_URL}${path}`, { method, cache: "no-store" });
  if (allow404 && res.status === 404) return null;
  if (!res.ok) {
    let message = `The server returned an error (${res.status}).`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") message = body.detail;
    } catch { /* keep generic */ }
    throw new Error(message);
  }
  return (await res.json()) as T;
}

const base = (id: string) => `/api/crash-tests/${encodeURIComponent(id)}/memo`;
export const getMemo = (id: string) => call<MemoResponse>(base(id), "GET", true);
export const draftMemo = (id: string) => call<MemoResponse>(base(id), "POST") as Promise<MemoResponse>;
export const translateMemo = (id: string) => call<{ markdown: string; cached: boolean }>(`${base(id)}/bn`, "POST") as Promise<{ markdown: string; cached: boolean }>;