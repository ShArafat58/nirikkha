"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useApp } from "../../components/providers";
import { useSession } from "../../components/session";
import { Alert } from "../../components/ui";
import { getCompanies, getMyCrashTests, type MyCrashTest } from "../../lib/api";
import { Loader } from "../../components/loader";
import ReportsEmptyState, { EMPTY_LABELS_BN } from "../../components/reports-empty-state";

type Row = {
  id: string; company: string; cik: string; as_of: string; decision: string;
  score: number | null; band: string | null; status: string | null; created: string | null;
};

const TXT = {
  en: {
    kicker: "Reports", title: "Every Crash-Test in one place", sub: "Open a report, or its legal memo. Featured runs are public examples anyone can open.",
    featured: "Featured demos", featuredNote: "Public examples chosen by the admin.", mine: "My reports", mineNote: "Private to your account.",
    signIn: "Log in to see your own reports.", noneMine: "You have not run a Crash-Test yet.", run: "Run a Crash-Test",
    asOf: "Evidence frozen", report: "Report", memo: "Legal memo", noneFeatured: "No featured demos yet.",
    band: { low_concern: "Low concern", moderate_concern: "Moderate concern", elevated_concern: "Elevated concern", high_concern: "High concern" } as Record<string, string>,
    status: { queued: "Queued", running: "Running", failed: "Failed", blocked: "Blocked", done: "Done" } as Record<string, string>,
  },
  bn: {
    kicker: "রিপোর্ট", title: "সব ক্র্যাশ-টেস্ট এক জায়গায়", sub: "রিপোর্ট বা তার লিগ্যাল মেমো খুলুন। ফিচার্ড রানগুলো যে কেউ খুলতে পারে।",
    featured: "ফিচার্ড ডেমো", featuredNote: "অ্যাডমিনের বাছাই করা প্রকাশ্য উদাহরণ।", mine: "আমার রিপোর্ট", mineNote: "শুধু আপনার অ্যাকাউন্টের জন্য।",
    signIn: "নিজের রিপোর্ট দেখতে লগ ইন করুন।", noneMine: "আপনি এখনো কোনো ক্র্যাশ-টেস্ট চালাননি।", run: "ক্র্যাশ-টেস্ট চালান",
    asOf: "প্রমাণ ফ্রিজ", report: "রিপোর্ট", memo: "লিগ্যাল মেমো", noneFeatured: "এখনো কোনো ফিচার্ড ডেমো নেই।",
    band: { low_concern: "কম উদ্বেগ", moderate_concern: "মাঝারি উদ্বেগ", elevated_concern: "বেশি উদ্বেগ", high_concern: "উচ্চ উদ্বেগ" } as Record<string, string>,
    status: { queued: "অপেক্ষমাণ", running: "চলছে", failed: "ব্যর্থ", blocked: "আটকানো", done: "সম্পন্ন" } as Record<string, string>,
  },
};

function toRow(x: Record<string, unknown>, company?: string): Row {
  const health = (x.health ?? null) as { score?: number; band?: string } | null;
  const num = (v: unknown) => (typeof v === "number" ? v : null);
  const str = (v: unknown) => (typeof v === "string" ? v : null);
  return {
    id: String(x.id), cik: String(x.cik ?? ""), company: company ?? str(x.company) ?? String(x.cik ?? ""),
    as_of: String(x.as_of ?? ""), decision: String(x.decision ?? ""),
    score: num(x.score) ?? num(x.health_score) ?? num(health?.score),
    band: str(x.band) ?? str(health?.band), status: str(x.status), created: str(x.created_at),
  };
}

export default function ReportsPage() {
  const app = useApp();
  const lang = (app as unknown as { lang?: string }).lang === "bn" ? "bn" : "en";
  const t = TXT[lang];
  const { signedIn, loading } = useSession();
  const [featured, setFeatured] = useState<Row[] | null>(null);
  const [mine, setMine] = useState<Row[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getCompanies()
      .then((cs) => setFeatured(cs.flatMap((c) => (c.crash_tests ?? []).map((r) => toRow(r as unknown as Record<string, unknown>, c.company)))))
      .catch((e: unknown) => { setFeatured([]); setError(e instanceof Error ? e.message : "Could not load reports."); });
  }, []);

  useEffect(() => {
    if (loading || !signedIn) return;
    getMyCrashTests()
      .then((rs) => setMine(rs.map((r) => toRow(r as unknown as Record<string, unknown>))))
      .catch(() => setMine([]));
  }, [loading, signedIn]);

  const num = (v: number) => (lang === "bn" ? String(v).replace(/\d/g, (d) => "০১২৩৪৫৬৭৮৯"[Number(d)]) : String(v));
  const tone = (s: number | null) => (s == null ? "text-slate-400" : s >= 80 ? "text-emerald-500" : s >= 60 ? "text-amber-500" : "text-rose-500");

  const card = (r: Row) => (
    <li key={r.id} className="flex flex-col gap-4 rounded-2xl border border-slate-500/20 bg-slate-500/[0.04] p-5 sm:flex-row sm:items-center">
      <div className="w-16 shrink-0 text-center">
        <p className={`text-3xl font-bold leading-none ${tone(r.score)}`}>{r.score == null ? "—" : num(r.score)}</p>
        {r.band && <p className="mt-1 text-[11px] opacity-70">{t.band[r.band] ?? r.band}</p>}
      </div>
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{r.company}</p>
        <p className="text-xs opacity-60">{t.asOf}: {r.as_of}{r.status && r.status !== "done" ? ` · ${t.status[r.status] ?? r.status}` : ""}</p>
        <p className="mt-1 line-clamp-2 text-sm opacity-80">“{r.decision}”</p>
      </div>
      <div className="flex shrink-0 gap-2">
        <Link href={`/report/${r.id}`} className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-amber-400">{t.report}</Link>
        <Link href={`/report/${r.id}/memo`} className="rounded-lg border border-amber-500/50 px-4 py-2 text-sm text-amber-500 hover:bg-amber-500/10">⚖ {t.memo}</Link>
      </div>
    </li>
  );

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:py-10">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-500">{t.kicker}</p>
      <h1 className="mt-2 text-2xl font-bold sm:text-3xl">{t.title}</h1>
      <p className="mt-2 text-sm opacity-70">{t.sub}</p>
      {error && <div className="mt-5"><Alert>{error}</Alert></div>}

      <section id="featured" className="mt-8 scroll-mt-24">
        <h2 className="text-lg font-semibold">{t.featured}</h2>
        <p className="text-xs opacity-60">{t.featuredNote}</p>
        <ul className="mt-4 space-y-3">
          {featured === null ? <li><Loader className="py-6" /></li>
            : featured.length === 0 ? <li className="text-sm opacity-60">{t.noneFeatured}</li>
            : featured.map(card)}
        </ul>
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold">{t.mine}</h2>
        <p className="text-xs opacity-60">{t.mineNote}</p>
        <ul className="mt-4 space-y-3">
          {!signedIn ? (
            <li className="text-sm"><Link href="/login?next=/reports" className="text-sky-500 underline">{t.signIn}</Link></li>
          ) : mine === null ? <li><Loader className="py-6" /></li>
            : mine.length === 0 ? (
              <li><ReportsEmptyState labels={t === TXT.bn ? EMPTY_LABELS_BN : undefined} /></li>
            ) : mine.map(card)}
        </ul>
      </section>
    </main>
  );
}