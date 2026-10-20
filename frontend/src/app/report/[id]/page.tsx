"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { useApp } from "../../../components/providers";
import { ExcludedCard, FactorsCard, GapsCard, MethodCard, SentinelCard } from "../../../components/report/health-panel";
import { ScoreRing } from "../../../components/report/score-ring";
import { BandBadge } from "../../../components/score";
import { Alert } from "../../../components/ui";
import { ApiError, getCrashTest, type CrashTestJob } from "../../../lib/api";
import type { Key } from "../../../lib/i18n";

const COV_COLOR: Record<string, string> = { reliable: "bg-conf-high", limited: "bg-sev-medium", unreliable: "bg-sev-critical" };

function Tile({ label, value, tone = "", striped = false }: { label: string; value: React.ReactNode; tone?: string; striped?: boolean }) {
  return (
    <div className="relative overflow-hidden rounded-xl border border-border bg-surface-2/70 p-4">
      {striped && <span className="stripes absolute inset-y-0 right-0 w-2" aria-hidden />}
      <p className="text-xs text-muted">{label}</p>
      <p className={`mt-1 text-3xl font-semibold tabular-nums ${tone}`}>{value}</p>
    </div>
  );
}

function ReportView() {
  const { t } = useApp();
  const router = useRouter();
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<CrashTestJob | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getCrashTest(id)
      .then((j) => {
        if (j.status !== "done") router.replace(`/crash-test/${id}`);
        else setJob(j);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : t("rep.notFound")));
  }, [id, router, t]);

  if (error) return <main className="bg-app min-h-[calc(100vh-4rem)] px-4 py-16"><div className="mx-auto max-w-xl"><Alert>{error}</Alert></div></main>;
  if (!job?.report) return <main className="bg-app min-h-[calc(100vh-4rem)] px-4 py-16 text-center text-muted">{t("dash.loading")}</main>;

  const r = job.report;
  const h = r.health;
  const s = r.summary?.sentinel;

  return (
    <main className="bg-app min-h-[calc(100vh-4rem)] text-text">
      <section className="relative overflow-hidden border-b border-border">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-accent/10 via-transparent to-conf-medium/10" aria-hidden />
        <div className="relative mx-auto max-w-7xl px-4 py-10 sm:px-6">
          <Link href="/crash-test" className="text-sm text-muted hover:text-text">← {t("rep.back")}</Link>
          <div className="mt-6 grid items-center gap-10 lg:grid-cols-[1fr_auto]">
            <div className="min-w-0">
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">{t("rep.eyebrow")}</p>
              <h1 className="mt-3 text-4xl font-bold leading-tight sm:text-5xl">{r.company}</h1>
              <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
                <span className="rounded-full border border-border bg-surface px-3 py-1 font-mono">{t("rep.frozen")} {r.as_of}</span>
                <span className="rounded-full border border-border bg-surface px-3 py-1 font-mono">CIK {r.cik}</span>
                {r.retrieval_mode && <span className="rounded-full border border-border bg-surface px-3 py-1">{r.retrieval_mode}</span>}
              </div>
              {r.decision && (
                <blockquote className="mt-6 max-w-3xl border-l-4 border-accent pl-4 text-lg leading-relaxed text-text/90">“{r.decision}”</blockquote>
              )}
            </div>
            {h && (
              <div className="flex flex-col items-center rounded-3xl border border-border bg-surface/80 p-6 shadow-2xl shadow-black/20 backdrop-blur">
                <p className="text-xs font-medium uppercase tracking-wider text-muted">{t("run.score")}</p>
                <ScoreRing score={h.score} band={h.band} />
                <BandBadge band={h.band} />
                <div className="mt-5 w-56">
                  <div className="flex justify-between text-xs"><span className="text-muted">{t("run.coverage")}</span>
                    <span className="font-mono">{h.coverage.pct}% · {t(`cov.${h.coverage.label}` as Key)}</span></div>
                  <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-surface-2">
                    <div className={`h-full rounded-full ${COV_COLOR[h.coverage.label] ?? "bg-muted"}`} style={{ width: `${h.coverage.pct}%` }} />
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="mt-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Tile label={t("run.findings")} value={r.summary?.findings ?? "-"} />
            <Tile label={t("rep.verified")} value={s?.verified ?? "-"} tone="text-conf-high" />
            <Tile label={t("run.review")} value={h?.human_review ?? "-"} tone="text-sev-medium" />
            <Tile label={t("run.insufficient")} value={h?.insufficient_evidence.count ?? "-"} striped />
          </div>

          {h && h.warnings.length > 0 && (
            <ul className="mt-6 space-y-1.5 rounded-xl border border-sev-medium/40 bg-sev-medium/10 p-4 text-sm">
              {h.warnings.map((w) => <li key={w}>⚠ {w}</li>)}
            </ul>
          )}
        </div>
      </section>

      <nav className="sticky top-16 z-30 border-b border-border bg-bg/90 backdrop-blur" aria-label="Report sections">
        <div className="mx-auto flex max-w-7xl gap-1 px-4 sm:px-6">
          <span className="border-b-2 border-accent px-3 py-3 text-sm font-semibold">{t("rep.tab.overview")}</span>
        </div>
      </nav>

      {h && (
        <div className="mx-auto grid max-w-7xl gap-6 px-4 py-8 sm:px-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <FactorsCard health={h} />
            <GapsCard items={h.insufficient_evidence.items} />
          </div>
          <div className="space-y-6">
            <SentinelCard report={r} />
            <ExcludedCard items={h.excluded} />
            <MethodCard report={r} />
          </div>
        </div>
      )}
    </main>
  );
}

export default function ReportPage() {
  return (
    <Suspense fallback={null}>
      <ReportView />
    </Suspense>
  );
}