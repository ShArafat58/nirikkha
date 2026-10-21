"use client";

import Link from "next/link";
import { useState } from "react";

import { adminAddReview, adminReviews, type AdminRow } from "../../lib/api";
import { Loader } from "../loader";
import { useApp } from "../providers";
import { Alert } from "../ui";
import { Chip, Spinner, pick, str, when } from "./cells";
import { useAdminFetch } from "./overview";

const DECISIONS = ["approve", "reject"];
const isApprove = (d: string) => DECISIONS.indexOf(d) === 0;
const keyOf = (r: AdminRow) => `${str(r.crash_test_id)}:${str(pick(r, ["finding_id", "id"]))}`;
const decided = (r: AdminRow) => str(pick(r, ["review_decision", "reviewed_decision", "r_decision"]));

function ReviewCard({ row, token, bn, fresh, onSaved }: {
  row: AdminRow; token: string; bn: boolean; fresh: boolean; onSaved: (r: AdminRow) => void;
}) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState("");
  const runId = str(pick(row, ["crash_test_id"]));
  const findingId = str(pick(row, ["finding_id", "finding.id", "id"]));
  const title = str(pick(row, ["finding_title", "title", "finding.title", "claim", "finding.claim", "statement"]));
  const reason = str(pick(row, ["review_reason", "reason", "sentinel_reason", "finding.sentinel.reason", "finding.review_reason"]));
  const quote = str(pick(row, ["quote", "finding.citations.0.quote", "citation.quote"]));
  const done = decided(row);

  async function decide(decision: string) {
    setBusy(decision); setErr("");
    try {
      await adminAddReview(token, { crash_test_id: runId, finding_id: findingId, decision, note: note.trim() || undefined });
      onSaved({ ...row, review_decision: decision, review_note: note.trim() || null, reviewed_at: new Date().toISOString() });
      setNote("");
    } catch (e) { setErr(e instanceof Error ? e.message : "Error"); }
    finally { setBusy(null); }
  }

  const tone = done ? (isApprove(done) ? "border-emerald-500/50 bg-emerald-500/[0.06]" : "border-rose-500/50 bg-rose-500/[0.06]") : "border-border";
  return (
    <li className={`rounded-xl border p-4 transition-colors duration-500 ${tone}`}>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-semibold">{str(row.company)}</span>
        <span className="text-muted">{bn ? "ফ্রিজ" : "as of"} {str(row.as_of)}</span>
        <span className="font-mono text-muted">{findingId}</span>
        <Chip value={pick(row, ["severity", "finding.severity"])} />
        <Chip value={pick(row, ["confidence", "finding.confidence"])} />
        {done && <span className="ml-auto"><Chip value={done} /></span>}
      </div>
      <p className="mt-2 font-medium">{title || findingId}</p>
      {reason && <p className="mt-1 text-sm text-conf-medium">⚠ {reason}</p>}
      {quote && <p className="mt-2 border-l-2 border-border pl-3 text-xs italic text-muted" lang="en">“{quote.slice(0, 300)}”</p>}
      {row.decision ? <p className="mt-2 text-xs text-muted">{bn ? "সিদ্ধান্ত" : "Decision"}: “{str(row.decision).slice(0, 140)}”</p> : null}

      {done ? (
        <div className={`mt-3 rounded-lg px-3 py-2 text-sm font-medium ${isApprove(done) ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"}`}>
          {isApprove(done) ? "✓" : "✕"} {fresh
            ? (bn ? `${done} হয়েছে · অডিট ট্রেইলে সংরক্ষিত` : `${done} · saved to the audit trail`)
            : (bn ? `${done} করা হয়েছে` : `${done}`)}
          <span className="ml-2 text-xs font-normal opacity-80">{when(pick(row, ["reviewed_at", "review_created_at"]))}
            {pick(row, ["review_note"]) ? ` · “${str(pick(row, ["review_note"]))}”` : ""}</span>
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <input value={note} onChange={(e) => setNote(e.target.value.slice(0, 500))} placeholder={bn ? "নোট (ঐচ্ছিক)" : "Note (optional)"}
                 disabled={busy !== null}
                 className="min-w-[220px] flex-1 rounded-md border border-border bg-transparent px-3 py-1.5 text-sm" />
          {DECISIONS.map((d) => (
            <button key={d} type="button" disabled={busy !== null} onClick={() => decide(d)}
              className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-semibold disabled:opacity-60 ${isApprove(d)
                ? "bg-emerald-600 text-white hover:bg-emerald-500" : "border border-rose-500/60 text-rose-500 hover:bg-rose-500/10"}`}>
              {busy === d ? <Spinner /> : <span>{isApprove(d) ? "✓" : "✕"}</span>}
              {busy === d ? (isApprove(d) ? (bn ? "অনুমোদন হচ্ছে…" : "Approving…") : (bn ? "প্রত্যাখ্যান হচ্ছে…" : "Rejecting…")) : d}
            </button>
          ))}
          {runId && <Link href={`/report/${runId}`} className="text-xs text-sky-500 hover:underline">{bn ? "রিপোর্ট" : "Report"} ↗</Link>}
        </div>
      )}
      {err && <p className="mt-2 text-xs text-rose-500">{err}</p>}
    </li>
  );
}

export function AdminReviewsTab({ token, onAuthError }: { token: string; onAuthError: () => void }) {
  const app = useApp();
  const bn = (app as unknown as { lang?: string }).lang === "bn";
  const { data, error, setData } = useAdminFetch<AdminRow[]>(() => adminReviews(token), onAuthError, [token]);
  const [show, setShow] = useState<"open" | "all">("open");
  const [recent, setRecent] = useState<Set<string>>(new Set());
  const open = (data ?? []).filter((r) => !decided(r));
  const rows = (data ?? []).filter((r) => show === "all" || !decided(r) || recent.has(keyOf(r)));
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">{bn
        ? "রিলায়েবিলিটি সেন্টিনেল যে ফাইন্ডিংগুলো মানুষের পর্যালোচনার জন্য চিহ্নিত করেছে। প্রতিটি সিদ্ধান্ত অডিট ট্রেইলে থাকে।"
        : "Findings the Reliability Sentinel flagged for human review. Every decision is kept in the audit trail."}</p>
      {error && <Alert>{error}</Alert>}
      {!data && !error ? <Loader className="py-10" /> : (
        <>
          <div className="flex gap-2">{(["open", "all"] as const).map((k) => (
            <button key={k} type="button" onClick={() => { setShow(k); setRecent(new Set()); }}
              className={`rounded-full border px-3 py-1 text-sm ${show === k ? "border-conf-medium text-conf-medium" : "border-border text-muted"}`}>
              {k === "open" ? (bn ? "অপেক্ষমাণ" : "Open") : (bn ? "সব" : "All")} ({k === "open" ? open.length : (data ?? []).length})
            </button>))}</div>
          <ul className="space-y-3">
            {rows.length === 0 && <li className="text-sm text-muted">{bn ? "পর্যালোচনার কিছু নেই।" : "Nothing to review."}</li>}
            {rows.map((r) => (
              <ReviewCard key={keyOf(r)} row={r} token={token} bn={bn} fresh={recent.has(keyOf(r))}
                onSaved={(next) => {
                  setRecent((s) => new Set(s).add(keyOf(r)));
                  setData((list) => (list ?? []).map((x) => (keyOf(x) === keyOf(r) ? next : x)));
                }} />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
