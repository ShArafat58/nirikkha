"use client";

import type { ReplayData, ReplayEvent, ReplaySignResult, ReplayStatus } from "../../lib/replay";

export type ReplayLang = "en" | "bn";

const TXT = {
  en: {
    kicker: "First Warning Sign Replay",
    title: "Could the warning signs have been questioned before {company} failed?",
    sub: "We froze the public evidence on {freeze}, ran Nirikkha on that alone, then compared what it said with what became known later.",
    frozen: "Evidence frozen", failed: "Bank failed", seen: "visible to the system", hidden: "hidden from the system",
    daysBefore: "{n} days before the failure",
    stripSeen: "What the system could see", stripHidden: "Hidden: news, 8-K, regulators' reviews",
    steps: ["Timeline", "Reconstruct", "Freeze", "Run", "Compare"],
    timeline: "Timeline", showHidden: "{n} later events were hidden from the system · show",
    happened: "happened {d}, made public {p}",
    results: "Result", signs: "Documented warning signs",
    status: { detected: "Flagged", questioned: "Questioned", partial: "Partial", missed: "Missed", not_knowable: "Not knowable" },
    statusHelp: {
      detected: "flagged as a finding or rule gap", questioned: "raised as an unanswered question",
      partial: "only a weak match", missed: "knowable, but not raised", not_knowable: "no public evidence then",
    },
    knowable: "Public evidence existed before the freeze", notKnowable: "No public evidence before the freeze",
    said: "What Nirikkha said, using frozen evidence only", nothing: "Nothing in the report matched this sign.",
    question: "Open question", finding: "Finding", rule: "Rule", confirmed: "Confirmed later by",
    valid: "Valid replay · no citation from after the freeze",
    noResult: "The comparison has not been published yet. The timeline and the documented warning signs are shown.",
    other: "{n} other signals were raised that are not in the documented outcome. They count neither as hits nor as errors.",
    evidenceNote: "",
    limitsTitle: "What this replay does not claim",
    limits: [
      "It does not claim the failure could have been predicted.",
      "Only public filings available on the freeze date were used.",
      "Confidential supervisory findings could not be known, and are marked as such.",
      "Every match is deterministic and links to its passage, so anyone can check it.",
    ],
    mock: "Mock data: the backend is not reachable, so a saved sample is shown.",
    sources: "Sources",
    kind: { filing: "filing", disclosure: "disclosure", market: "market", outcome: "outcome", regulatory: "regulatory", review: "review" } as Record<string, string>,
    category: {
      interest_rate_risk: "Interest-rate risk", funding_concentration: "Deposit concentration",
      risk_leadership_gap: "Risk leadership gap", board_risk_oversight: "Board risk oversight",
      compensation_incentives: "Pay incentives", supervisory_findings: "Supervisory findings",
    } as Record<string, string>,
  },
  bn: {
    kicker: "ফার্স্ট ওয়ার্নিং সাইন রিপ্লে",
    title: "{company} ব্যর্থ হওয়ার আগে কি সতর্কসংকেতগুলো নিয়ে প্রশ্ন তোলা যেত?",
    sub: "{freeze} তারিখে প্রকাশ্য প্রমাণ ফ্রিজ করে শুধু সেটুকু দিয়ে Nirikkha চালানো হয়েছে, তারপর পরে জানা ঘটনার সাথে মিলিয়ে দেখা হয়েছে।",
    frozen: "প্রমাণ ফ্রিজ", failed: "ব্যাংক বন্ধ", seen: "সিস্টেম দেখতে পেয়েছে", hidden: "সিস্টেমের কাছে লুকানো",
    daysBefore: "ব্যর্থতার {n} দিন আগে",
    stripSeen: "সিস্টেম যা দেখতে পেয়েছে", stripHidden: "লুকানো: খবর, 8-K, নিয়ন্ত্রকের পর্যালোচনা",
    steps: ["টাইমলাইন", "প্রমাণ সংগ্রহ", "ফ্রিজ", "রান", "তুলনা"],
    timeline: "টাইমলাইন", showHidden: "পরের {n}টি ঘটনা সিস্টেমের কাছে লুকানো ছিল · দেখাও",
    happened: "ঘটেছে {d}, প্রকাশ {p}",
    results: "ফলাফল", signs: "নথিভুক্ত সতর্কসংকেত",
    status: { detected: "চিহ্নিত", questioned: "প্রশ্ন তোলা", partial: "আংশিক", missed: "বাদ পড়েছে", not_knowable: "জানা সম্ভব ছিল না" },
    statusHelp: {
      detected: "ফাইন্ডিং বা নিয়মের ঘাটতি হিসেবে", questioned: "উত্তর না পাওয়া প্রশ্ন হিসেবে",
      partial: "দুর্বল মিল", missed: "জানা যেত, তবু ওঠেনি", not_knowable: "তখন প্রকাশ্য প্রমাণ ছিল না",
    },
    knowable: "ফ্রিজের আগে প্রকাশ্য প্রমাণ ছিল", notKnowable: "ফ্রিজের আগে কোনো প্রকাশ্য প্রমাণ ছিল না",
    said: "Nirikkha যা বলেছে, শুধু ফ্রিজ করা প্রমাণ থেকে", nothing: "রিপোর্টের কিছুই এই সংকেতের সাথে মেলেনি।",
    question: "খোলা প্রশ্ন", finding: "ফাইন্ডিং", rule: "নিয়ম", confirmed: "পরে নিশ্চিত করেছে",
    valid: "বৈধ রিপ্লে · ফ্রিজের পরের কোনো উদ্ধৃতি নেই",
    noResult: "তুলনা এখনো প্রকাশ হয়নি। টাইমলাইন আর নথিভুক্ত সতর্কসংকেত দেখানো হচ্ছে।",
    other: "আরও {n}টি সংকেত উঠেছে যা নথিভুক্ত ফলাফলের অংশ নয়। এগুলো সঠিক বা ভুল কোনোটাই ধরা হয়নি।",
    evidenceNote: "উদ্ধৃতি আর AI-এর ফাইন্ডিং মূল ইংরেজি ফাইলিং থেকে অপরিবর্তিত রাখা হয়েছে, যাতে যে কেউ মিলিয়ে দেখতে পারে।",
    limitsTitle: "এই রিপ্লে যা দাবি করে না",
    limits: [
      "ব্যর্থতা আগে থেকে অনুমান করা যেত, এমন দাবি করে না।",
      "শুধু ফ্রিজের দিন পর্যন্ত প্রকাশিত ফাইলিং ব্যবহার করা হয়েছে।",
      "গোপন তদারকি পর্যবেক্ষণ জানা সম্ভব ছিল না, আর সেটা স্পষ্ট দেখানো হয়েছে।",
      "প্রতিটি মিল নির্দিষ্ট নিয়মে করা এবং মূল অনুচ্ছেদের সাথে যুক্ত, তাই যে কেউ যাচাই করতে পারে।",
    ],
    mock: "নমুনা ডেটা: ব্যাকএন্ড পাওয়া যাচ্ছে না, তাই সংরক্ষিত নমুনা দেখানো হচ্ছে।",
    sources: "উৎস",
    kind: { filing: "ফাইলিং", disclosure: "প্রকাশ", market: "বাজার", outcome: "ফলাফল", regulatory: "নিয়ন্ত্রক", review: "পর্যালোচনা" } as Record<string, string>,
    category: {
      interest_rate_risk: "সুদের হারের ঝুঁকি", funding_concentration: "আমানতের কেন্দ্রীভবন",
      risk_leadership_gap: "ঝুঁকি-নেতৃত্বে শূন্যতা", board_risk_oversight: "বোর্ডের ঝুঁকি তদারকি",
      compensation_incentives: "প্রণোদনা কাঠামো", supervisory_findings: "তদারকি সংস্থার পর্যবেক্ষণ",
    } as Record<string, string>,
  },
};
type T = (typeof TXT)["en"];

const ICON: Record<string, string> = {
  interest_rate_risk: "📉", funding_concentration: "🏦", risk_leadership_gap: "👤",
  board_risk_oversight: "🧭", compensation_incentives: "💰", supervisory_findings: "🔐",
};
const TONE: Record<ReplayStatus, string> = {
  detected: "border-emerald-500/50 bg-emerald-500/10 text-emerald-500",
  questioned: "border-sky-500/50 bg-sky-500/10 text-sky-500",
  partial: "border-amber-500/50 bg-amber-500/10 text-amber-500",
  missed: "border-rose-500/50 bg-rose-500/10 text-rose-500",
  not_knowable: "border-slate-500/50 bg-slate-500/10 text-slate-400",
};
const ORDER: ReplayStatus[] = ["detected", "questioned", "partial", "missed", "not_knowable"];
const panel = "rounded-2xl border border-slate-500/20 bg-slate-500/[0.04] p-5 sm:p-6";
const BN_DIGITS = "০১২৩৪৫৬৭৮৯";

function num(v: string | number, lang: ReplayLang): string {
  const s = String(v);
  return lang === "bn" ? s.replace(/\d/g, (d) => BN_DIGITS[Number(d)]) : s;
}

function fill(s: string, vars: Record<string, string | number>, lang: ReplayLang): string {
  return s.replace(/\{(\w+)\}/g, (_, k: string) => {
    const v = vars[k];
    return typeof v === "number" ? num(v, lang) : String(v ?? "");
  });
}

function fmt(iso: string, lang: ReplayLang): string {
  const d = new Date(`${iso}T00:00:00Z`);
  return d.toLocaleDateString(lang === "bn" ? "bn-BD" : "en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

function days(a: string, b: string): number {
  return Math.round((Date.parse(b) - Date.parse(a)) / 86_400_000);
}

function Badge({ status, t }: { status: ReplayStatus; t: T }) {
  return (
    <span className={`inline-flex shrink-0 items-center rounded-full border px-3 py-1 text-xs font-semibold ${TONE[status]}`}>
      {t.status[status]}
    </span>
  );
}

function FreezeStrip({ events, freeze, outcome, t }: { events: ReplayEvent[]; freeze: string; outcome: string; t: T }) {
  const start = Date.parse(events[0].public_date);
  const end = Date.parse(events[events.length - 1].public_date);
  const f = Date.parse(freeze);
  const SPLIT = 70; // the hidden part gets a fixed share of the bar so it stays readable
  const pos = (iso: string) => {
    const x = Date.parse(iso);
    const p = x <= f
      ? ((x - start) / Math.max(f - start, 1)) * SPLIT
      : SPLIT + ((x - f) / Math.max(end - f, 1)) * (100 - SPLIT);
    return `${p.toFixed(2)}%`;
  };
  return (
    <div className="mt-8">
      <div className="relative h-3 rounded-full bg-slate-500/15">
        <div className="absolute inset-y-0 left-0 rounded-l-full bg-emerald-500/40" style={{ width: pos(freeze) }} />
        <div
          className="absolute inset-y-0 right-0 rounded-r-full"
          style={{
            left: pos(freeze),
            backgroundImage: "repeating-linear-gradient(135deg, rgba(244,63,94,.45) 0 6px, rgba(244,63,94,.12) 6px 12px)",
          }}
        />
        {events.map((e) => (
          <span
            key={e.id}
            title={`${e.public_date} · ${e.title}`}
            className={`absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--background,#0b1220)] ${
              e.visible_at_freeze ? "bg-emerald-400" : "bg-rose-400"}`}
            style={{ left: pos(e.public_date) }}
          />
        ))}
        <span className="absolute -top-2 bottom-[-8px] w-0.5 bg-rose-500" style={{ left: pos(freeze) }} />
        <span className="absolute -top-2 bottom-[-8px] w-0.5 bg-slate-300/70" style={{ left: pos(outcome) }} />
      </div>
      <div className="mt-3 flex justify-between gap-4 text-xs">
        <span className="text-emerald-500">● {t.stripSeen}</span>
        <span className="text-right text-rose-500">{t.stripHidden} ●</span>
      </div>
    </div>
  );
}

function EventRow({ e, t, lang }: { e: ReplayEvent; t: T; lang: ReplayLang }) {
  const title = lang === "bn" && e.title_bn ? e.title_bn : e.title;
  return (
    <li className="relative pb-6 pl-7 last:pb-0">
      <span className={`absolute left-0 top-1 h-3 w-3 -translate-x-[7px] rounded-full ring-4 ring-[var(--background,#0b1220)] ${
        e.visible_at_freeze ? "bg-emerald-400" : "bg-slate-500"}`} />
      <p className="text-xs font-medium uppercase tracking-wider opacity-60">
        {fmt(e.public_date, lang)} · {t.kind[e.kind] ?? e.kind}
      </p>
      <p className="mt-1 text-[15px] leading-snug">{title}</p>
      {e.public_date !== e.event_date && (
        <p className="mt-1 text-xs text-amber-500">{fill(t.happened, { d: fmt(e.event_date, lang), p: fmt(e.public_date, lang) }, lang)}</p>
      )}
      <p className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-xs">
        {e.sources.slice(0, 1).map((s) => (
          <a key={s.url + s.title} href={s.url} target="_blank" rel="noreferrer" title={s.title}
             className="opacity-50 transition hover:text-sky-400 hover:opacity-100">
            {t.sources} ↗
          </a>
        ))}
      </p>
    </li>
  );
}

function SignItem({ s, t, events, lang, statementBn }: {
  s: ReplaySignResult; t: T; events: Map<string, ReplayEvent>; lang: ReplayLang; statementBn?: string;
}) {
  const statement = lang === "bn" && statementBn ? statementBn : s.statement;
  return (
    <details className="group rounded-xl border border-slate-500/20 bg-slate-500/[0.03] transition open:bg-slate-500/[0.07]">
      <summary className="flex cursor-pointer list-none items-center gap-4 p-4 sm:p-5">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-slate-500/10 text-xl" aria-hidden>
          {ICON[s.category] ?? "•"}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-semibold">{t.category[s.category] ?? s.category}</span>
          <span className="mt-0.5 block text-sm leading-snug opacity-70">{statement}</span>
        </span>
        <Badge status={s.status} t={t} />
        <span className="hidden text-lg opacity-40 transition group-open:rotate-90 sm:block" aria-hidden>›</span>
      </summary>

      <div className="space-y-3 border-t border-slate-500/15 px-4 pb-5 pt-4 sm:px-5">
        <p className="text-xs opacity-60">{s.knowable_before_freeze ? t.knowable : t.notKnowable}</p>
        <p className="text-xs font-semibold uppercase tracking-wider opacity-60">{t.said}</p>
        {s.evidence.length === 0 && s.rules.length === 0 && <p className="text-sm opacity-60">{t.nothing}</p>}
        {s.evidence.map((ev, i) => (
          <div key={i} className="rounded-lg border-l-2 border-sky-500/60 bg-slate-500/[0.06] p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-sky-500">
              {ev.type === "question" ? t.question : t.finding}
            </p>
            <p className="mt-1 text-sm leading-relaxed" lang="en">{ev.finding}</p>
            {ev.citations.map((c, j) => (
              <p key={j} className="mt-2 text-xs opacity-70" lang="en">
                <span className="font-mono">{[c.form, c.page ? `p.${c.page}` : null].filter(Boolean).join(" · ")}</span>
                {c.quote && <span className="mt-0.5 block italic">“{c.quote}”</span>}
              </p>
            ))}
          </div>
        ))}
        {s.rules.map((r) => (
          <div key={r.rule_id} className="rounded-lg border-l-2 border-amber-500/60 bg-slate-500/[0.06] p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-amber-500">{t.rule} · {r.rule_id}</p>
            <p className="mt-1 text-sm leading-relaxed" lang="en">{r.rationale}</p>
            {r.citation?.quote && (
              <p className="mt-2 text-xs opacity-80" lang="en">
                <span className="font-mono">{[r.citation.form, r.citation.page ? `p.${r.citation.page}` : null].filter(Boolean).join(" · ")}</span>
                <span className="mt-0.5 block italic">“{r.citation.quote}”</span>
              </p>
            )}
          </div>
        ))}
        {s.confirmed_by.length > 0 && (
          <p className="pt-1 text-xs opacity-60">
            <span className="font-semibold">{t.confirmed}: </span>
            {s.confirmed_by.map((id) => {
              const e = events.get(id);
              if (!e) return id;
              const title = lang === "bn" && e.title_bn ? e.title_bn : e.title;
              return `${title} (${fmt(e.public_date, lang)})`;
            }).join(" · ")}
          </p>
        )}
      </div>
    </details>
  );
}

export function ReplayView({ data, lang }: { data: ReplayData; lang: ReplayLang }) {
  const t = TXT[lang];
  const c = data.case;
  const r = data.result;
  const events = [...c.timeline].sort((a, b) => a.public_date.localeCompare(b.public_date));
  const byId = new Map(events.map((e) => [e.id, e]));
  const statementsBn = new Map(c.warning_signs.map((s) => [s.id, s.statement_bn]));
  const open = events.filter((e) => e.visible_at_freeze);
  const hidden = events.filter((e) => !e.visible_at_freeze);
  const done = r ? 5 : 3;

  return (
    <div className="space-y-8">
      {data.mock && (
        <div className="rounded-xl border border-amber-500/50 bg-amber-500/10 px-4 py-2.5 text-sm text-amber-500">{t.mock}</div>
      )}

      <section className="relative overflow-hidden rounded-3xl border border-slate-500/20 bg-gradient-to-br from-emerald-500/[0.08] via-transparent to-rose-500/[0.10] p-6 sm:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-500">{t.kicker}</p>
        <h1 className="mt-3 max-w-3xl text-2xl font-bold leading-tight sm:text-4xl">{fill(t.title, { company: c.company }, lang)}</h1>
        <p className="mt-4 max-w-2xl text-base leading-relaxed opacity-75">{fill(t.sub, { freeze: fmt(c.freeze_date, lang) }, lang)}</p>

        <div className="mt-8 grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/[0.07] p-4">
            <p className="text-xs uppercase tracking-wider text-emerald-500">{t.frozen}</p>
            <p className="mt-1 text-xl font-bold">{fmt(c.freeze_date, lang)}</p>
            <p className="text-xs opacity-60">{fill(t.daysBefore, { n: days(c.freeze_date, c.outcome_date) }, lang)}</p>
          </div>
          <div className="rounded-2xl border border-rose-500/30 bg-rose-500/[0.07] p-4">
            <p className="text-xs uppercase tracking-wider text-rose-500">{t.failed}</p>
            <p className="mt-1 text-xl font-bold">{fmt(c.outcome_date, lang)}</p>
            <p className="text-xs opacity-60">California DFPI · FDIC</p>
          </div>
          <div className="rounded-2xl border border-slate-500/30 bg-slate-500/[0.07] p-4">
            <p className="text-xl font-bold">
              <span className="text-emerald-500">{num(open.length, lang)}</span>
              <span className="mx-1.5 opacity-40">/</span>
              <span className="text-rose-500">{num(hidden.length, lang)}</span>
            </p>
            <p className="mt-1 text-xs opacity-60">{t.seen} / {t.hidden}</p>
          </div>
        </div>

        <FreezeStrip events={events} freeze={c.freeze_date} outcome={c.outcome_date} t={t} />

        <ol className="mt-8 flex flex-wrap gap-2">
          {t.steps.map((s, i) => (
            <li key={s} className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium ${
              i < done ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-500" : "border-slate-500/30 opacity-50"}`}>
              <span>{i < done ? "✓" : num(i + 1, lang)}</span>{s}
            </li>
          ))}
        </ol>
      </section>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <section className={panel}>
          <h2 className="mb-6 text-lg font-semibold">{t.timeline}</h2>
          <ol className="ml-1.5 border-l border-slate-500/25">
            {open.map((e) => <EventRow key={e.id} e={e} t={t} lang={lang} />)}
          </ol>
          <div className="my-6 flex items-center gap-3">
            <span className="h-px flex-1 bg-rose-500/60" />
            <span className="rounded-full border border-rose-500/60 bg-rose-500/10 px-3 py-1 text-xs font-semibold text-rose-500">
              ❄ {t.frozen} · {fmt(c.freeze_date, lang)}
            </span>
            <span className="h-px flex-1 bg-rose-500/60" />
          </div>
          <details className="group">
            <summary className="cursor-pointer list-none rounded-lg px-1 py-1 text-sm opacity-70 hover:opacity-100">
              🔒 {fill(t.showHidden, { n: hidden.length }, lang)}
            </summary>
            <ol className="ml-1.5 mt-5 border-l border-slate-500/25 opacity-60">
              {hidden.map((e) => <EventRow key={e.id} e={e} t={t} lang={lang} />)}
            </ol>
          </details>
        </section>

        <div className="space-y-8">
          <section className={panel}>
            <h2 className="mb-5 text-lg font-semibold">{t.results}</h2>
            {r ? (
              <>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                  {ORDER.map((st) => (
                    <div key={st} className={`rounded-xl border p-3 ${TONE[st]}`}>
                      <p className="text-3xl font-bold leading-none">{num(r.summary[st], lang)}</p>
                      <p className="mt-2 text-xs font-semibold">{t.status[st]}</p>
                      <p className="mt-0.5 text-[11px] leading-tight opacity-75">{t.statusHelp[st]}</p>
                    </div>
                  ))}
                </div>
                <p className={`mt-4 text-sm font-medium ${r.verdict === "VALID" ? "text-emerald-500" : "text-rose-500"}`}>
                  {r.verdict === "VALID" ? `✓ ${t.valid}` : r.verdict}
                </p>
                {r.summary.other_signals > 0 && (
                  <p className="mt-1 text-xs opacity-60">{fill(t.other, { n: r.summary.other_signals }, lang)}</p>
                )}
              </>
            ) : (
              <p className="text-sm opacity-70">{t.noResult}</p>
            )}
          </section>

          <section className={panel}>
            <h2 className="mb-2 text-lg font-semibold">{t.signs}</h2>
            {t.evidenceNote && <p className="mb-4 text-xs opacity-60">{t.evidenceNote}</p>}
            <div className="space-y-3">
              {r
                ? r.signs.map((s) => (
                    <SignItem key={s.id} s={s} t={t} events={byId} lang={lang} statementBn={statementsBn.get(s.id)} />
                  ))
                : c.warning_signs.map((s) => (
                    <div key={s.id} className="flex items-center gap-4 rounded-xl border border-slate-500/20 p-4">
                      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-slate-500/10 text-xl" aria-hidden>
                        {ICON[s.category] ?? "•"}
                      </span>
                      <span className="min-w-0">
                        <span className="block font-semibold">{t.category[s.category] ?? s.category}</span>
                        <span className="mt-0.5 block text-sm opacity-70">{lang === "bn" && s.statement_bn ? s.statement_bn : s.statement}</span>
                      </span>
                    </div>
                  ))}
            </div>
          </section>
        </div>
      </div>

      <section className={panel}>
        <h2 className="mb-4 text-lg font-semibold">{t.limitsTitle}</h2>
        <ul className="grid gap-3 sm:grid-cols-2">
          {t.limits.map((l) => (
            <li key={l} className="flex gap-3 text-sm leading-relaxed opacity-80">
              <span className="text-emerald-500" aria-hidden>✓</span>{l}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}