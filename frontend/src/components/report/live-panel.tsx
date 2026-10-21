"use client";

import type { CrashTestJob } from "../../lib/api";
import type { Key } from "../../lib/i18n";
import { useApp } from "../providers";

function secs(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`;
}

export function LivePanel({ job }: { job: CrashTestJob }) {
  const { t } = useApp();
  const total = job.pipeline.length;
  const done = job.done_nodes.length;
  const current = job.pipeline.find((n) => !job.done_nodes.includes(n));
  const pct = Math.round((done / total) * 100);
  const log = [...job.events].reverse();
  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-border bg-surface p-6">
        <div className="flex items-center justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs font-medium uppercase tracking-wider text-muted">{t("live.progress")}</p>
            {job.private && (
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-400">
                🔒 {t("ct.privateBadge")}
              </span>
            )}
          </div>
          <span className="font-mono text-sm tabular-nums">{pct}%</span>
        </div>
        <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-surface-2">
          <div className="h-full rounded-full bg-gradient-to-r from-accent/70 to-accent transition-all duration-700" style={{ width: `${Math.max(4, pct)}%` }} />
        </div>
        <p className="mt-2 font-mono text-xs text-muted">{done}/{total}</p>

        <p className="mt-6 text-xs font-medium uppercase tracking-wider text-muted">{t("live.now")}</p>
        {job.status === "queued" || !current ? (
          <p className="mt-2 text-text/85">{t("live.waiting")}</p>
        ) : (
          <div className="mt-2 rounded-xl border border-accent/30 bg-accent/5 p-4">
            <p className="flex items-center gap-2 text-lg font-semibold text-accent">
              <span className="relative flex h-2.5 w-2.5"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-75" /><span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-accent" /></span>
              {t(`node.${current}` as Key)}
            </p>
            <p className="mt-2 leading-relaxed text-text/85">{t(`nodeinfo.${current}` as Key)}</p>
          </div>
        )}
      </div>

      {log.length > 0 && (
        <div className="rounded-2xl border border-border bg-surface p-6">
          <p className="text-xs font-medium uppercase tracking-wider text-muted">{t("live.log")}</p>
          <ol className="mt-3 space-y-3">
            {log.map((e) => (
              <li key={e.node} className="flex gap-3 text-sm">
                <span className="mt-0.5 w-16 shrink-0 text-right font-mono text-xs text-muted">{secs(e.ms)}</span>
                <span className="text-conf-high" aria-hidden>✓</span>
                <span className="min-w-0">
                  <span className="font-medium">{t(`node.${e.node}` as Key)}</span>
                  <span className="block break-words text-xs text-muted">{e.message}</span>
                </span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}