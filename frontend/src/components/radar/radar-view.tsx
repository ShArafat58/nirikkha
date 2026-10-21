"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import {
  decideAlert, edgarUrl, getAlertHistory,
  type RadarAlert, type RadarData, type RadarHistoryItem, type RadarPriority,
} from "../../lib/radar";

export type RadarLang = "en" | "bn";

const TXT = {
  en: {
    kicker: "Regulatory Change Radar",
    title: "When the rules change, see which disclosures need a second look",
    sub: "Two data streams, rule-based priority, and a person approves or rejects every alert before any follow-up starts.",
    streams: "Data streams", priority: { high: "High", medium: "Medium", low: "Low" },
    decision: { pending: "Pending review", approved: "Approved", rejected: "Rejected" },
    tabs: { all: "All", pending: "Pending", decided: "Decided" },
    stream: { regulatory: "Rule change", filing: "New filing" },
    evidence: {
      addressed: "Disclosure found", gap: "Disclosure not found", not_yet_required: "Not yet required",
      no_filing: "Insufficient evidence", not_analysed: "Not analysed yet",
    } as Record<string, string>,
    whatChanged: "What changed", affected: "Affected requirements", review: "Disclosure to review",
    found: "Evidence", followUp: "Follow-up", why: "How applicability was decided", sources: "Sources",
    note: "Note for the audit trail (optional)", approve: "Approve follow-up", reject: "Reject",
    signIn: "Sign in to approve or reject", by: "by", history: "Decision history", change: "Change decision",
    empty: "No alerts in this view.", mock: "Mock data: the backend is not reachable, decisions are not saved.",
    saved: "Saved", failed: "Could not save",
  },
  bn: {
    kicker: "রেগুলেটরি চেঞ্জ রাডার",
    title: "নিয়ম বদলালে দেখুন কোন disclosure আবার দেখা দরকার",
    sub: "দুটি data stream, নিয়মভিত্তিক অগ্রাধিকার, আর যেকোনো follow-up শুরুর আগে প্রতিটি alert একজন মানুষ approve বা reject করেন।",
    streams: "Data stream", priority: { high: "উচ্চ", medium: "মাঝারি", low: "নিম্ন" },
    decision: { pending: "পর্যালোচনার অপেক্ষায়", approved: "অনুমোদিত", rejected: "প্রত্যাখ্যাত" },
    tabs: { all: "সব", pending: "অপেক্ষমাণ", decided: "সিদ্ধান্ত হয়েছে" },
    stream: { regulatory: "নিয়ম পরিবর্তন", filing: "নতুন filing" },
    evidence: {
      addressed: "Disclosure পাওয়া গেছে", gap: "Disclosure পাওয়া যায়নি", not_yet_required: "এখনো প্রযোজ্য নয়",
      no_filing: "অপর্যাপ্ত প্রমাণ", not_analysed: "এখনো বিশ্লেষণ হয়নি",
    } as Record<string, string>,
    whatChanged: "কী বদলেছে", affected: "প্রভাবিত requirement", review: "যে disclosure দেখতে হবে",
    found: "প্রমাণ", followUp: "পরবর্তী পদক্ষেপ", why: "প্রযোজ্যতা কীভাবে ঠিক হয়েছে", sources: "উৎস",
    note: "Audit trail-এর জন্য নোট (ঐচ্ছিক)", approve: "Follow-up অনুমোদন", reject: "প্রত্যাখ্যান",
    signIn: "Approve বা reject করতে sign in করুন", by: "করেছেন", history: "সিদ্ধান্তের ইতিহাস", change: "সিদ্ধান্ত বদলান",
    empty: "এই তালিকায় কোনো alert নেই।", mock: "Mock data: backend পাওয়া যাচ্ছে না, সিদ্ধান্ত সংরক্ষণ হবে না।",
    saved: "সংরক্ষিত", failed: "সংরক্ষণ করা যায়নি",
  },
};
type T = (typeof TXT)["en"];

const STRIPE: Record<RadarPriority, string> = { high: "bg-rose-500", medium: "bg-amber-500", low: "bg-sky-500" };
const PRIO_PILL: Record<RadarPriority, string> = {
  high: "border-rose-500/50 bg-rose-500/10 text-rose-500",
  medium: "border-amber-500/50 bg-amber-500/10 text-amber-500",
  low: "border-sky-500/50 bg-sky-500/10 text-sky-500",
};
const EVID: Record<string, string> = {
  addressed: "text-emerald-500", gap: "text-rose-500", not_yet_required: "text-slate-400",
  no_filing: "text-amber-500", not_analysed: "text-amber-500",
};
const DECISION_PILL = {
  pending: "border-slate-500/40 text-slate-400",
  approved: "border-emerald-500/50 bg-emerald-500/10 text-emerald-500",
  rejected: "border-rose-500/50 bg-rose-500/10 text-rose-500",
};
const panel = "rounded-2xl border border-slate-500/20 bg-slate-500/[0.04]";

function when(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function AlertCard({ a, t, signedIn, mock, onChange }: {
  a: RadarAlert; t: T; signedIn: boolean; mock: boolean; onChange: (a: RadarAlert, h?: RadarHistoryItem[]) => void;
}) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [editing, setEditing] = useState(a.status === "pending");
  const [history, setHistory] = useState<RadarHistoryItem[] | null>(null);
  const d = a.disclosure_to_review;

  async function decide(decision: "approve" | "reject") {
    setBusy(true); setMsg("");
    try {
      if (mock) {
        const status = decision === "approve" ? "approved" : "rejected";
        onChange({ ...a, status, note: note || null, decided_at: new Date().toISOString(), decided_by_email: "demo" });
      } else {
        const r = await decideAlert(a.id, decision, note);
        onChange(r.alert); setHistory(r.history);
      }
      setEditing(false); setNote(""); setMsg(t.saved);
    } catch (e) {
      setMsg(`${t.failed}: ${e instanceof Error ? e.message : ""}`);
    } finally { setBusy(false); }
  }

  async function loadHistory() {
    if (mock || history) return;
    try { setHistory((await getAlertHistory(a.id)).history); } catch { setHistory([]); }
  }

  return (
    <article className={`relative overflow-hidden ${panel}`}>
      <span className={`absolute inset-y-0 left-0 w-1.5 ${STRIPE[a.priority]}`} aria-hidden />
      <div className="space-y-4 p-5 pl-7 sm:p-6 sm:pl-8">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className={`rounded-full border px-2.5 py-0.5 font-semibold ${PRIO_PILL[a.priority]}`}>{t.priority[a.priority]}</span>
          <span className="rounded-full border border-slate-500/30 px-2.5 py-0.5 opacity-80">{t.stream[a.stream]}</span>
          <span className="opacity-60">{a.company}</span>
          <span className={`ml-auto rounded-full border px-2.5 py-0.5 font-semibold ${DECISION_PILL[a.status]}`}>{t.decision[a.status]}</span>
        </div>

        <div>
          <h3 className="text-lg font-semibold leading-snug">{a.title}</h3>
          <p className={`mt-1 text-sm font-medium ${EVID[a.evidence.status] ?? ""}`}>● {t.evidence[a.evidence.status] ?? a.evidence.status}</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider opacity-60">{t.whatChanged}</p>
            <p className="mt-1 text-sm leading-relaxed opacity-90">{a.what_changed}</p>
            {a.affected_items.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {a.affected_items.map((i) => (
                  <span key={i} className="rounded bg-slate-500/15 px-1.5 py-0.5 font-mono text-[11px]">{i}</span>
                ))}
              </div>
            )}
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider opacity-60">{t.review}</p>
            {d ? (
              <a href={d.url || edgarUrl(a.cik, d.accession_no)} target="_blank" rel="noreferrer"
                 className="mt-1 inline-block text-sm hover:text-sky-400">
                {d.form} · {d.filing_date} ↗
              </a>
            ) : <p className="mt-1 text-sm opacity-60">—</p>}
            <p className="mt-3 text-[11px] font-semibold uppercase tracking-wider opacity-60">{t.followUp}</p>
            <p className="mt-1 text-sm leading-relaxed opacity-90">{a.follow_up}</p>
          </div>
        </div>

        {a.evidence.passage && (
          <blockquote className="rounded-lg border-l-2 border-emerald-500/60 bg-slate-500/[0.06] p-3 text-sm">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-emerald-500">
              {t.found} · {a.evidence.passage.form}{a.evidence.passage.page ? ` p.${a.evidence.passage.page}` : ""}
            </p>
            <p className="mt-1 italic leading-relaxed opacity-90">“{a.evidence.passage.quote}”</p>
          </blockquote>
        )}

        {(a.applicability_note || a.sources.length > 0) && (
          <details className="text-xs opacity-70">
            <summary className="cursor-pointer">{t.why}</summary>
            <p className="mt-2">{a.applies}</p>
            <p className="mt-1">{a.applicability_note}</p>
            <p className="mt-1">{a.sources.map((s) => (
              <a key={s.url} href={s.url} target="_blank" rel="noreferrer" className="mr-3 underline">{s.title} ↗</a>
            ))}</p>
          </details>
        )}

        <div className="border-t border-slate-500/15 pt-4">
          {a.status !== "pending" && !editing && (
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <span className="opacity-80">
                {t.decision[a.status]} {a.decided_by_email ? `${t.by} ${a.decided_by_email}` : ""} · {when(a.decided_at)}
              </span>
              {a.note && <span className="opacity-70">“{a.note}”</span>}
              {signedIn && <button type="button" className="text-xs underline opacity-70" onClick={() => setEditing(true)}>{t.change}</button>}
            </div>
          )}
          {editing && (signedIn || mock ? (
            <div className="space-y-3">
              <textarea value={note} onChange={(e) => setNote(e.target.value.slice(0, 500))} rows={2}
                placeholder={t.note}
                className="w-full rounded-lg border border-slate-500/30 bg-transparent px-3 py-2 text-sm outline-none focus:border-sky-500" />
              <div className="flex flex-wrap gap-2">
                <button type="button" disabled={busy} onClick={() => decide("approve")}
                  className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50">
                  ✓ {t.approve}
                </button>
                <button type="button" disabled={busy} onClick={() => decide("reject")}
                  className="rounded-lg border border-rose-500/60 px-4 py-2 text-sm font-semibold text-rose-500 hover:bg-rose-500/10 disabled:opacity-50">
                  ✕ {t.reject}
                </button>
              </div>
            </div>
          ) : (
            <Link href="/login?next=/radar" className="inline-block rounded-lg border border-sky-500/50 px-4 py-2 text-sm text-sky-500 hover:bg-sky-500/10">
              {t.signIn}
            </Link>
          ))}
          {msg && <p className="mt-2 text-xs opacity-70">{msg}</p>}
          {a.status !== "pending" && !mock && (
            <details className="mt-3 text-xs" onToggle={loadHistory}>
              <summary className="cursor-pointer opacity-70">{t.history}</summary>
              <ul className="mt-2 space-y-1 opacity-80">
                {(history ?? []).map((h, i) => (
                  <li key={i}>{when(h.at)} · {h.decision} · {h.by ?? ""}{h.note ? ` · “${h.note}”` : ""}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      </div>
    </article>
  );
}

const BN_FOLLOW: Record<string, string> = {
  gap: "কোম্পানির কাছে জানতে চান বা অন্য ফাইলিংয়ে এই disclosure খুঁজুন; তবুও না পেলে লিগ্যাল বা কমপ্লায়েন্স পর্যালোচনায় পাঠান।",
  addressed: "নতুন নিয়ম পূরণ হয়েছে কি না নিশ্চিত হতে অনুচ্ছেদটি পড়ুন; হলে আর কিছু করতে হবে না।",
  not_yet_required: "নিয়ম প্রযোজ্য হলে পরের বার্ষিক প্রতিবেদন বা প্রক্সিতে এই disclosure আছে কি না দেখুন।",
  no_filing: "অপর্যাপ্ত প্রমাণ: এই ধরনের সর্বশেষ ফাইলিং যোগ করে আবার রাডার চালান।",
};

function localise(a: RadarAlert, lang: RadarLang): RadarAlert {
  if (lang !== "bn") return a;
  const d = a.disclosure_to_review;
  if (a.stream === "filing") {
    const is8k = d?.form === "8-K";
    return {
      ...a,
      title: d ? `নতুন ${d.form} জমা পড়েছে ${d.filing_date}` : a.title,
      what_changed: is8k
        ? "চলতি প্রতিবেদনে কোনো গভর্ন্যান্স ঘটনা (পরিচালক বা কর্মকর্তা পরিবর্তন, গুরুত্বপূর্ণ চুক্তি, কোনো ঘটনা) ঘোষিত হতে পারে।"
        : "নতুন বার্ষিক প্রতিবেদন বা প্রক্সি স্টেটমেন্ট এসেছে, এখনো বিশ্লেষণ হয়নি।",
      follow_up: is8k
        ? "8-K-এর বিষয়গুলো পড়ুন; কোনো পরিচালক, কর্মকর্তা বা নিরীক্ষক বদলালে আবার ক্র্যাশ-টেস্ট চালান।"
        : "এই ফাইলিং যোগ করে আবার ক্র্যাশ-টেস্ট ও রাডার চালান।",
    };
  }
  return { ...a, title: a.title_bn || a.title, what_changed: a.what_changed_bn || a.what_changed,
           follow_up: BN_FOLLOW[a.evidence.status] ?? a.follow_up };
}

export function RadarView({ data, lang, signedIn }: { data: RadarData; lang: RadarLang; signedIn: boolean }) {
  const t = TXT[lang];
  const num = (v: number) => (lang === "bn" ? String(v).replace(/\d/g, (d) => "০১২৩৪৫৬৭৮৯"[Number(d)]) : String(v));
  const [alerts, setAlerts] = useState<RadarAlert[]>(data.alerts);
  const [tab, setTab] = useState<"all" | "pending" | "decided">("all");

  const counts = useMemo(() => ({
    pending: alerts.filter((a) => a.status === "pending").length,
    approved: alerts.filter((a) => a.status === "approved").length,
    rejected: alerts.filter((a) => a.status === "rejected").length,
    high: alerts.filter((a) => a.priority === "high").length,
    medium: alerts.filter((a) => a.priority === "medium").length,
    low: alerts.filter((a) => a.priority === "low").length,
  }), [alerts]);

  const shown = alerts.filter((a) => tab === "all" || (tab === "pending" ? a.status === "pending" : a.status !== "pending"));
  const update = (next: RadarAlert) => setAlerts((list) => list.map((a) => (a.id === next.id ? next : a)));

  return (
    <div className="space-y-8">
      {data.mock && (
        <div className="rounded-xl border border-amber-500/50 bg-amber-500/10 px-4 py-2.5 text-sm text-amber-500">{t.mock}</div>
      )}

      <section className="relative overflow-hidden rounded-3xl border border-slate-500/20 bg-gradient-to-br from-sky-500/[0.10] via-transparent to-amber-500/[0.08] p-6 sm:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-500">{t.kicker}</p>
        <h1 className="mt-3 max-w-3xl text-2xl font-bold leading-tight sm:text-4xl">{t.title}</h1>
        <p className="mt-4 max-w-2xl text-base leading-relaxed opacity-75">{t.sub}</p>

        <div className="mt-8 grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-slate-500/30 bg-slate-500/[0.07] p-4">
            <p className="text-xs uppercase tracking-wider opacity-60">{t.streams}</p>
            <ul className="mt-2 space-y-1 text-sm">
              {data.streams.map((s) => (
                <li key={s.id}>● {s.title} <span className="opacity-50">({num(data.summary.by_stream[s.id] ?? 0)})</span></li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border border-slate-500/30 bg-slate-500/[0.07] p-4">
            <div className="flex gap-4">
              {(["high", "medium", "low"] as RadarPriority[]).map((p) => (
                <div key={p}>
                  <p className={`text-2xl font-bold ${PRIO_PILL[p].split(" ").pop()}`}>{num(counts[p])}</p>
                  <p className="text-xs opacity-60">{t.priority[p]}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-2xl border border-slate-500/30 bg-slate-500/[0.07] p-4">
            <div className="flex gap-4">
              <div><p className="text-2xl font-bold">{num(counts.pending)}</p><p className="text-xs opacity-60">{t.tabs.pending}</p></div>
              <div><p className="text-2xl font-bold text-emerald-500">{num(counts.approved)}</p><p className="text-xs opacity-60">{t.decision.approved}</p></div>
              <div><p className="text-2xl font-bold text-rose-500">{num(counts.rejected)}</p><p className="text-xs opacity-60">{t.decision.rejected}</p></div>
            </div>
          </div>
        </div>
        <p className="mt-6 text-xs opacity-60">{data.note}</p>
      </section>

      <div className="flex flex-wrap gap-2" role="tablist">
        {(["all", "pending", "decided"] as const).map((k) => (
          <button key={k} type="button" role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`rounded-full border px-4 py-1.5 text-sm ${tab === k ? "border-sky-500 bg-sky-500/15 text-sky-500" : "border-slate-500/30 opacity-70 hover:opacity-100"}`}>
            {t.tabs[k]}
          </button>
        ))}
      </div>

      <div className="space-y-4">
        {shown.length === 0 && <p className="py-10 text-center text-sm opacity-60">{t.empty}</p>}
        {shown.map((a) => (
          <AlertCard key={a.id} a={localise(a, lang)} t={t} signedIn={signedIn} mock={Boolean(data.mock)} onChange={update} />
        ))}
      </div>
    </div>
  );
}