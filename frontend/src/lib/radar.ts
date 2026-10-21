// Regulatory Change Radar: types, API calls and mock data.
import { API_URL, USE_MOCK, getToken } from "./api";

export type RadarPriority = "high" | "medium" | "low";
export type RadarDecisionStatus = "pending" | "approved" | "rejected";
export type RadarPassage = { form?: string | null; accession_no?: string | null; page?: number | null; quote: string };
export type RadarAlert = {
  id: string; key: string; stream: "regulatory" | "filing"; cik: string; company: string; title: string;
  title_bn?: string | null; what_changed_bn?: string | null;
  priority: RadarPriority; status: RadarDecisionStatus; what_changed: string; affected_items: string[];
  affected_rules: string[]; applies: string; applicability_note: string;
  disclosure_to_review: { form: string; accession_no: string; filing_date: string; url?: string | null } | null;
  evidence: { status: string; passage: RadarPassage | null }; follow_up: string;
  sources: { title: string; url: string }[]; event_date: string;
  decided_at?: string | null; decided_by_email?: string | null; note?: string | null;
};
export type RadarSummary = {
  total: number; pending: number; approved: number; rejected: number;
  by_priority: Record<RadarPriority, number>; by_stream: Record<string, number>;
};
export type RadarData = {
  summary: RadarSummary; alerts: RadarAlert[]; streams: { id: string; title: string }[]; note: string; mock?: boolean;
};
export type RadarHistoryItem = { decision: string; note: string | null; by: string | null; at: string };

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });
  if (!res.ok) {
    let message = `Request failed (${res.status}).`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") message = body.detail;
    } catch { /* keep the generic message */ }
    const err = new Error(message) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  return (await res.json()) as T;
}

export async function getRadar(): Promise<RadarData> {
  if (USE_MOCK) return { ...MOCK_RADAR, mock: true };
  try {
    return await req<RadarData>("/api/radar");
  } catch (e) {
    if (e instanceof TypeError) return { ...MOCK_RADAR, mock: true }; // backend unreachable
    throw e;
  }
}

export function decideAlert(id: string, decision: "approve" | "reject", note: string) {
  return req<{ alert: RadarAlert; history: RadarHistoryItem[] }>(
    `/api/radar/alerts/${encodeURIComponent(id)}/decision`,
    { method: "POST", body: JSON.stringify({ decision, note: note.trim() || null }) },
  );
}

export function getAlertHistory(id: string) {
  return req<{ history: RadarHistoryItem[] }>(`/api/radar/alerts/${encodeURIComponent(id)}/history`);
}

export function edgarUrl(cik: string, accession: string): string {
  return `https://www.sec.gov/Archives/edgar/data/${Number(cik)}/${accession.replace(/-/g, "")}/`;
}

const base: Pick<RadarAlert, "affected_rules" | "applies" | "applicability_note" | "sources" | "decided_at" | "decided_by_email" | "note"> = {
  affected_rules: [], applies: "", applicability_note: "", sources: [], decided_at: null, decided_by_email: null, note: null,
};

export const MOCK_RADAR: RadarData = {
  summary: { total: 3, pending: 3, approved: 0, rejected: 0, by_priority: { high: 1, medium: 0, low: 2 },
    by_stream: { regulatory: 2, filing: 1 } },
  streams: [{ id: "regulatory", title: "SEC rule changes (curated)" }, { id: "filing", title: "New filings on SEC EDGAR" }],
  note: "Priority is rule-based. No follow-up action counts as started until a person approves it.",
  alerts: [
    { ...base, id: "m1", key: "filing:m1", stream: "filing", cik: "0000320193", company: "Apple Inc.",
      title: "New 8-K filed 2026-07-30", priority: "high", status: "pending",
      what_changed: "A current report may announce a governance event (director or officer change, material agreement, incident).",
      affected_items: [], disclosure_to_review: { form: "8-K", accession_no: "0000320193-26-000000", filing_date: "2026-07-30" },
      evidence: { status: "not_analysed", passage: null },
      follow_up: "Read the 8-K items; if a director, officer or auditor changed, re-run the Crash-Test.", event_date: "2026-07-30" },
    { ...base, id: "m2", key: "reg:sec-2023-cyber:0000320193", stream: "regulatory", cik: "0000320193", company: "Apple Inc.",
      title: "Cybersecurity risk management, strategy and governance", priority: "low", status: "pending",
      what_changed: "Annual reports must describe processes for managing cybersecurity risk and the board's oversight of it.",
      affected_items: ["Reg S-K Item 106", "Form 8-K Item 1.05"],
      disclosure_to_review: { form: "10-K", accession_no: "0000320193-25-000079", filing_date: "2025-10-31" },
      evidence: { status: "addressed", passage: { form: "10-K", page: 19,
        quote: "...the Company's management, led by its Head of Corporate Information Security, has overall responsibility for identifying, assessing and managing..." } },
      follow_up: "Read the passage to confirm it meets the new requirement; no further action if it does.", event_date: "2023-07-26" },
    { ...base, id: "m3", key: "reg:sec-2023-cyber:0000719739", stream: "regulatory", cik: "0000719739", company: "SVB FINANCIAL GROUP",
      title: "Cybersecurity risk management, strategy and governance", priority: "low", status: "pending",
      what_changed: "Annual reports must describe processes for managing cybersecurity risk and the board's oversight of it.",
      affected_items: ["Reg S-K Item 106"],
      disclosure_to_review: { form: "10-K", accession_no: "0000719739-23-000021", filing_date: "2023-02-24" },
      evidence: { status: "not_yet_required", passage: null },
      follow_up: "Check the next annual report or proxy for this disclosure once the rule applies.", event_date: "2023-07-26" },
  ],
};