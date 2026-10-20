"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { useApp } from "../../../components/providers";
import { LivePanel } from "../../../components/report/live-panel";
import { Alert } from "../../../components/ui";
import { ApiError, getCrashTest, type CrashTestJob } from "../../../lib/api";
import type { Key } from "../../../lib/i18n";

const POLL_MS = 2500;
const OPEN_DELAY_MS = 1500;

function seconds(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`;
}

function Timeline({ job }: { job: CrashTestJob }) {
  const { t } = useApp();
  const byNode = new Map(job.events.map((e) => [e.node, e]));
  const active = job.status === "running" ? job.pipeline.find((n) => !job.done_nodes.includes(n)) : undefined;
  return (
    <ol className="relative space-y-1 border-l border-border pl-6">
      {job.pipeline.map((node) => {
        const ev = byNode.get(node);
        const done = job.done_nodes.includes(node);
        const isActive = node === active;
        return (
          <li key={node} className="relative py-2">
            <span className={`absolute -left-[31px] top-2.5 flex h-4 w-4 items-center justify-center rounded-full border-2 ${done ? "border-conf-high bg-conf-high" : isActive ? "border-accent bg-bg" : "border-border bg-bg"}`}>
              {done && <span className="text-[10px] font-bold leading-none text-bg">✓</span>}
              {isActive && <span className="h-2 w-2 animate-ping rounded-full bg-accent" />}
            </span>
            <div className="flex flex-wrap items-baseline justify-between gap-x-4">
              <span className={`font-medium ${done ? "text-text" : isActive ? "text-accent" : "text-muted"}`}>{t(`node.${node}` as Key)}</span>
              {ev && <span className="font-mono text-xs text-muted">{seconds(ev.ms)}</span>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

function CompleteCard({ id }: { id: string }) {
  const { t } = useApp();
  return (
    <div className="flex flex-col items-center rounded-2xl border border-conf-high/40 bg-conf-high/10 p-10 text-center">
      <span className="flex h-20 w-20 items-center justify-center rounded-full bg-conf-high text-4xl font-bold text-bg shadow-lg shadow-conf-high/30">✓</span>
      <h2 className="mt-6 text-2xl font-bold">{t("run.done")}</h2>
      <p className="mt-2 flex items-center gap-2 text-muted">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />{t("rep.opening")}
      </p>
      <Link href={`/report/${id}`} className="mt-6 text-sm font-semibold text-accent hover:underline">{t("rep.openNow")} →</Link>
    </div>
  );
}

function RunView() {
  const { t } = useApp();
  const router = useRouter();
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<CrashTestJob | null>(null);
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const sawRunning = useRef(false);
  const started = useRef<number | null>(null);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const next = await getCrashTest(id);
        if (!alive) return;
        setJob(next);
        setError("");
        if (next.status === "queued" || next.status === "running") {
          sawRunning.current = true;
          timer = setTimeout(poll, POLL_MS);
        }
      } catch (err) {
        if (!alive) return;
        setError(err instanceof ApiError ? err.message : t("auth.err.generic"));
        if (!(err instanceof ApiError && err.status === 404)) timer = setTimeout(poll, POLL_MS * 2);
      }
    };
    void poll();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [id, t]);

  useEffect(() => {
    if (job?.status !== "done") return;
    const timer = setTimeout(() => router.replace(`/report/${id}`), sawRunning.current ? OPEN_DELAY_MS : 0);
    return () => clearTimeout(timer);
  }, [job?.status, id, router]);

  const running = job && (job.status === "queued" || job.status === "running");
  useEffect(() => {
    if (!running) return;
    started.current ??= Date.now();
    const timer = setInterval(() => setElapsed(Math.round((Date.now() - (started.current ?? Date.now())) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [running]);

  const heading = !job ? t("dash.loading") : running ? t("run.title") : job.status === "done" ? t("run.done")
    : job.status === "blocked" ? t("run.blocked") : t("run.failed");

  return (
    <main className="bg-app min-h-[calc(100vh-4rem)] text-text">
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <Link href="/crash-test" className="text-sm text-muted hover:text-text">← {t("run.retry")}</Link>
        <div className="mt-3 flex flex-wrap items-baseline gap-x-4">
          <h1 className="text-3xl font-bold">{heading}</h1>
          {running && <span className="font-mono text-sm text-muted">{t("run.elapsed")}: {elapsed} s</span>}
        </div>
        {job && <p className="mt-2 max-w-3xl text-sm text-muted"><span className="font-mono">as of {job.as_of}</span> · {job.decision}</p>}
        {error && <div className="mt-4"><Alert>{error}</Alert></div>}

        {job && (
          <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,22rem)_1fr]">
            <section className="h-fit rounded-2xl border border-border bg-surface p-6">
              {job.status === "queued" && (
                <div className="mb-4"><Alert kind="info">{job.worker_online === false ? t("run.workerOff") : t("run.queued")}</Alert></div>
              )}
              <Timeline job={job} />
            </section>
            <section>
              {running && <LivePanel job={job} />}
              {job.status === "done" && <CompleteCard id={id} />}
              {(job.status === "failed" || job.status === "blocked") && <Alert>{job.error ?? t("auth.err.generic")}</Alert>}
            </section>
          </div>
        )}
      </div>
    </main>
  );
}

export default function CrashTestRunPage() {
  return (
    <Suspense fallback={null}>
      <RunView />
    </Suspense>
  );
}