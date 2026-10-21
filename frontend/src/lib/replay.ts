// First Warning Sign Replay: types, API call and mock data.
import { API_URL, USE_MOCK } from "./api";

export type ReplaySource = { title: string; url: string };
export type ReplayEvent = {
  id: string; kind: string; precision: string; event_date: string; public_date: string;
  title: string; title_bn?: string; note?: string; sources: ReplaySource[]; visible_at_freeze: boolean;
};
export type ReplaySign = {
  id: string; category: string; statement: string; statement_bn?: string; pre_freeze_evidence: string[];
  confirmed_by: string[]; keywords: string[]; rules?: string[];
};
export type ReplayStatus = "detected" | "questioned" | "partial" | "missed" | "not_knowable";
export type ReplayCitation = {
  form?: string | null; accession_no?: string | null; page?: number | null; section?: string | null; quote: string;
};
export type ReplayEvidence = {
  finding: string; type?: "question" | "finding"; matched_keywords: string[]; citations: ReplayCitation[];
};
export type ReplaySignResult = {
  id: string; category: string; statement: string; knowable_before_freeze: boolean; status: ReplayStatus;
  evidence: ReplayEvidence[];
  rules: { rule_id: string; result: string; rationale: string; citation?: ReplayCitation | null }[];
  confirmed_by: string[];
};
export type ReplaySummary = {
  detected: number; questioned: number; partial: number; missed: number; not_knowable: number;
  signs: number; knowable: number; detection_rate: number | null; flagged_or_questioned_rate: number | null;
  detection_rate_incl_partial: number | null; findings_in_report: number; other_signals: number;
};
export type ReplayResult = {
  case_id: string; company: string; freeze_date: string; outcome_date: string; outcome: string;
  verdict: string; leaks: unknown[]; summary: ReplaySummary; signs: ReplaySignResult[];
  other_signals: string[]; source?: string;
};
export type ReplayCaseInfo = {
  id: string; company: string; cik: string; freeze_date: string; outcome_date: string; outcome: string;
  freeze_rationale?: string; timeline: ReplayEvent[]; warning_signs: ReplaySign[];
};
export type ReplayControl = {
  job: string; company: string | null; cik: string | null; as_of: string | null; decision: string | null;
  health_score: number | null; band: string | null; coverage_pct: number | null; findings: number;
  rules: Record<string, Record<string, number>>;
  gaps: { rule_id: string; title: string | null; result: string; category: string | null }[];
  pattern_matches: { detected: number; questioned: number; partial: number; missed: number };
};
export type ReplayControls = { subject: ReplayControl; controls: ReplayControl[] };
export type ReplayData = { case: ReplayCaseInfo; result: ReplayResult | null; controls?: ReplayControls | null; mock?: boolean };

export async function getReplay(id = "svb"): Promise<ReplayData> {
  if (USE_MOCK) return { ...MOCK_REPLAY, mock: true };
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/replay/${encodeURIComponent(id)}`, { cache: "no-store" });
  } catch {
    return { ...MOCK_REPLAY, mock: true }; // backend unreachable: keep the page usable, clearly labelled
  }
  if (res.status === 404) throw new Error("Replay case not found.");
  if (!res.ok) throw new Error(`The server returned an error (${res.status}). Please try again.`);
  return (await res.json()) as ReplayData;
}

const EDGAR = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000719739";
const BARR = "https://www.federalreserve.gov/publications/files/svb-review-20230428.pdf";
const ev = (
  id: string, kind: string, event_date: string, public_date: string, title: string, url: string, visible: boolean,
): ReplayEvent => ({
  id, kind, precision: "day", event_date, public_date, title, sources: [{ title: "Source", url }], visible_at_freeze: visible,
});

// Mirrors the real comparison of run e3d02af1 (evidence as of the freeze, before the 2023 proxy was added).
export const MOCK_REPLAY: ReplayData = {
  case: {
    id: "svb", company: "SVB Financial Group", cik: "0000719739", freeze_date: "2023-03-07", outcome_date: "2023-03-10",
    outcome: "Silicon Valley Bank was closed by the California DFPI on 10 March 2023 and the FDIC was appointed receiver.",
    freeze_rationale: "Freeze the day before the 8 March 2023 announcement of the securities sale and capital raise.",
    timeline: [
      ev("ev_def14a_2021", "filing", "2021-03-04", "2021-03-04", "DEF 14A proxy statement (2021 annual meeting)", EDGAR, true),
      ev("ev_10k_fy2021", "filing", "2022-03-01", "2022-03-01", "Form 10-K for fiscal year 2021", EDGAR, true),
      ev("ev_def14a_2022", "filing", "2022-03-04", "2022-03-04", "DEF 14A proxy statement (2022 annual meeting)", EDGAR, true),
      ev("ev_10k_fy2022", "filing", "2023-02-24", "2023-02-24", "Form 10-K for fiscal year 2022", EDGAR, true),
      ev("ev_cro_exit", "disclosure", "2022-04-29", "2023-03-03", "Chief Risk Officer stops serving in the role", EDGAR, true),
      ev("ev_pre14a_2023", "filing", "2023-03-03", "2023-03-03", "PRE 14A preliminary proxy (2023); no definitive proxy was ever filed", EDGAR, true),
      ev("ev_8k_afs_sale", "market", "2023-03-08", "2023-03-08", "8-K: $21B securities sale, $1.8B after-tax loss, $2.25B capital raise", EDGAR, false),
      ev("ev_run", "market", "2023-03-09", "2023-03-09", "Deposit run: more than $42B withdrawn in one day", BARR, false),
      ev("ev_failure", "outcome", "2023-03-10", "2023-03-10", "Bank closed by California DFPI; FDIC appointed receiver", BARR, false),
      ev("ev_systemic", "regulatory", "2023-03-12", "2023-03-12", "Systemic risk exception: all depositors protected", BARR, false),
      ev("ev_fed_irr_finding", "regulatory", "2022-11-01", "2023-04-28", "Fed supervisory finding on interest rate risk (confidential then)", BARR, false),
      ev("ev_barr_review", "review", "2023-04-28", "2023-04-28", "Federal Reserve publishes its review of SVB's failure", BARR, false),
    ],
    warning_signs: [],
  },
  result: {
    case_id: "svb", company: "SVB Financial Group", freeze_date: "2023-03-07", outcome_date: "2023-03-10",
    outcome: "Silicon Valley Bank was closed on 10 March 2023.", verdict: "VALID", leaks: [],
    summary: {
      detected: 1, questioned: 3, partial: 1, missed: 0, not_knowable: 1, signs: 6, knowable: 5,
      detection_rate: 0.2, flagged_or_questioned_rate: 0.8, detection_rate_incl_partial: 1,
      findings_in_report: 23, other_signals: 18,
    },
    signs: [
      { id: "ws_interest_rate", category: "interest_rate_risk", knowable_before_freeze: true, status: "detected",
        statement: "A large, long-duration securities portfolio left the bank exposed to rising interest rates.",
        evidence: [{ finding: "Item 7A. Quantitative and Qualitative Disclosures About Market Risk shrank sharply year over year",
          type: "finding", matched_keywords: ["market risk"], citations: [] }],
        rules: [{ rule_id: "II_YOY_CHANGE", result: "POTENTIAL_GAP", rationale: "Item 7A market risk disclosure 14,505 -> 7,957 chars (-45.1%)." }],
        confirmed_by: ["ev_8k_afs_sale", "ev_barr_review"] },
      { id: "ws_deposit_concentration", category: "funding_concentration", knowable_before_freeze: true, status: "questioned",
        statement: "Deposits were concentrated in one client sector and mostly above the insured limit, making a fast run possible.",
        evidence: [{ finding: "What specific deposit risk metrics (e.g. liquidity ratios, deposit concentration) does the board monitor?",
          type: "question", matched_keywords: ["deposit concentration", "liquidity"], citations: [] }],
        rules: [], confirmed_by: ["ev_run", "ev_failure"] },
      { id: "ws_cro_vacancy", category: "risk_leadership_gap", knowable_before_freeze: true, status: "partial",
        statement: "The Chief Risk Officer role was without a permanent holder for most of 2022.",
        evidence: [{ finding: "Board and officer facts may have changed since the last proxy", type: "finding",
          matched_keywords: ["chief risk officer"], citations: [] }],
        rules: [], confirmed_by: ["ev_barr_review"] },
      { id: "ws_board_oversight", category: "board_risk_oversight", knowable_before_freeze: true, status: "questioned",
        statement: "The board and management did not manage the bank's risks effectively.",
        evidence: [{ finding: "Decision question: what governance structures ensure the risk committee oversees risk appetite?",
          type: "question", matched_keywords: ["risk committee", "risk oversight", "risk appetite"], citations: [] }],
        rules: [], confirmed_by: ["ev_barr_review"] },
      { id: "ws_compensation", category: "compensation_incentives", knowable_before_freeze: true, status: "questioned",
        statement: "Executive incentives were not tied to risk management outcomes.",
        evidence: [{ finding: "Decision question: how have executive compensation metrics changed?", type: "question",
          matched_keywords: ["performance metric", "return on equity", "earnings per share"], citations: [] }],
        rules: [], confirmed_by: ["ev_barr_review"] },
      { id: "ws_supervisory_findings", category: "supervisory_findings", knowable_before_freeze: false, status: "not_knowable",
        statement: "Supervisors had raised many open findings, far more than peer banks. These were confidential.",
        evidence: [], rules: [], confirmed_by: ["ev_fed_irr_finding", "ev_barr_review"] },
    ],
    other_signals: [], source: "mock (from run e3d02af1)",
  },
};