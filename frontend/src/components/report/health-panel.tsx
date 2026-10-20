"use client";

import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { Health, HealthFactor, Report } from "../../lib/api";
import type { Key } from "../../lib/i18n";
import { useApp } from "../providers";

const SEV_COLOR: Record<string, string> = {
  critical: "var(--sev-critical)", high: "var(--sev-high)", medium: "var(--sev-medium)", low: "var(--sev-low)",
};
const RULE_PREFIX = "Cannot confirm: ";
const QUESTION_PREFIX = "Not answered by public filings: ";

export function Card({ title, icon, children, className = "" }: { title?: string; icon?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl border border-border bg-surface/90 p-6 shadow-lg shadow-black/10 backdrop-blur ${className}`}>
      {title && <h2 className="flex items-center gap-2 text-lg font-semibold">{icon}{title}</h2>}
      <div className={title ? "mt-4" : ""}>{children}</div>
    </section>
  );
}

export function IdBadge({ id }: { id: string }) {
  return <span className="shrink-0 whitespace-nowrap rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-muted">{id}</span>;
}

export function FactorsCard({ health }: { health: Health }) {
  const { t } = useApp();
  const factors = health.factors.slice(0, 10);
  return (
    <Card title={t("health.factors")}>
      {factors.length === 0 ? (
        <p className="text-sm text-muted">{t("health.none")}</p>
      ) : (
        <div style={{ height: factors.length * 36 + 16 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={factors} layout="vertical" margin={{ top: 0, right: 36, bottom: 0, left: 0 }}>
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="id" width={64} axisLine={false} tickLine={false}
                     tick={{ fill: "var(--muted)", fontSize: 12, fontFamily: "var(--font-plex-mono)" }} />
              <Tooltip cursor={{ fill: "var(--surface-2)" }} wrapperStyle={{ maxWidth: 340, zIndex: 20, outline: "none" }}
                       content={({ active, payload }) => {
                         const f = active ? (payload?.[0]?.payload as HealthFactor | undefined) : undefined;
                         if (!f) return null;
                         return (
                           <div className="rounded-lg border border-border bg-surface p-3 text-sm shadow-xl">
                             <p className="leading-snug text-text">{f.title}</p>
                             <div className="mt-2 flex flex-wrap items-center gap-2">
                               <span className="font-mono text-base font-semibold text-accent">-{f.points} {t("health.points")}</span>
                               <span className="rounded-full border border-border px-2 py-0.5 text-xs text-muted">{t("rep.severity")}: {f.severity}</span>
                               <span className="rounded-full border border-border px-2 py-0.5 text-xs text-muted">{t("rep.confidence")}: {f.confidence}</span>
                             </div>
                           </div>
                         );
                       }} />
              <Bar dataKey="points" radius={[0, 6, 6, 0]} barSize={18}
                   label={{ position: "right", fill: "var(--muted)", fontSize: 12, formatter: (v: unknown) => `-${v}` }}>
                {factors.map((f) => <Cell key={f.id} fill={SEV_COLOR[f.severity] ?? "var(--muted)"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      <h3 className="mt-6 text-sm font-semibold text-muted">{t("health.byInv")}</h3>
      <ul className="mt-2 grid gap-2 sm:grid-cols-2">
        {Object.entries(health.by_investigation).map(([inv, d]) => (
          <li key={inv} className="flex items-center justify-between rounded-lg bg-surface-2 px-3 py-2 text-sm">
            <span>{t(`inv.${inv}` as Key)}</span>
            <span className="font-mono">-{d.deducted}{d.capped && <span className="ml-2 text-xs text-sev-medium">({t("health.capped")})</span>}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function GapsCard({ items }: { items: { id: string; title: string; severity: string }[] }) {
  const { t } = useApp();
  if (!items.length) return null;
  const rules = items.filter((i) => i.title.startsWith(RULE_PREFIX)).map((i) => ({ ...i, text: i.title.slice(RULE_PREFIX.length) }));
  const questions = items.filter((i) => i.title.startsWith(QUESTION_PREFIX)).map((i) => ({ ...i, text: i.title.slice(QUESTION_PREFIX.length) }));
  const other = items.filter((i) => !i.title.startsWith(RULE_PREFIX) && !i.title.startsWith(QUESTION_PREFIX));
  return (
    <Card title={t("health.insufficient")} icon={<span className="stripes inline-block h-4 w-4 shrink-0 rounded" aria-hidden />}>
      {rules.length > 0 && (
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-muted"><span aria-hidden>📋</span>{t("health.gapRules")}</h3>
          <ul className="mt-2 flex flex-wrap gap-2">
            {rules.map((r) => (
              <li key={r.id} className="flex items-center gap-2 rounded-full border border-border bg-surface-2/60 py-1 pl-1.5 pr-3 text-sm">
                <IdBadge id={r.id} />{r.text}
              </li>
            ))}
          </ul>
        </div>
      )}
      {questions.length > 0 && (
        <div className={rules.length ? "mt-6" : ""}>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-muted"><span aria-hidden>❓</span>{t("health.gapQuestions")}</h3>
          <ul className="mt-2 space-y-2">
            {questions.map((q) => (
              <li key={q.id} className="flex items-start gap-3 rounded-lg border border-border bg-surface-2/60 p-3 text-sm leading-relaxed">
                <IdBadge id={q.id} /><span>{q.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {other.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-semibold text-muted">{t("health.gapOther")}</h3>
          <ul className="mt-2 space-y-2">
            {other.map((o) => <li key={o.id} className="flex items-start gap-3 text-sm leading-relaxed"><IdBadge id={o.id} /><span>{o.title}</span></li>)}
          </ul>
        </div>
      )}
    </Card>
  );
}

export function SentinelCard({ report }: { report: Report }) {
  const { t } = useApp();
  const s = report.summary?.sentinel;
  if (!s) return null;
  const rows: [string, number, string][] = [
    [t("rep.verified"), s.verified, "bg-conf-high"], [t("rep.needsReview"), s.needs_review, "bg-sev-medium"],
    [t("rep.downgraded"), s.downgraded, "bg-conf-medium"], [t("rep.unsupported"), s.unsupported, "bg-sev-critical"],
  ];
  const total = rows.reduce((n, r) => n + r[1], 0) || 1;
  return (
    <Card title={t("rep.sentinel")} icon={<span aria-hidden>🛡</span>}>
      <p className="text-sm text-muted">{t("rep.sentinelNote")}</p>
      <div className="mt-4 flex h-2.5 overflow-hidden rounded-full bg-surface-2">
        {rows.map(([label, n, color]) => n > 0 && <div key={label} className={color} style={{ width: `${(n / total) * 100}%` }} />)}
      </div>
      <ul className="mt-4 space-y-2 text-sm">
        {rows.map(([label, n, color]) => (
          <li key={label} className="flex items-center justify-between">
            <span className="flex items-center gap-2"><span className={`h-2.5 w-2.5 rounded-full ${color}`} aria-hidden />{label}</span>
            <span className="font-mono">{n}</span>
          </li>
        ))}
      </ul>
      {s.judge_model && <p className="mt-4 font-mono text-xs text-muted">{t("rep.judge")}: {s.judge_model}</p>}
    </Card>
  );
}

export function ExcludedCard({ items }: { items: { id: string; title: string; reason: string }[] }) {
  const { t } = useApp();
  if (!items.length) return null;
  return (
    <Card title={t("health.excluded")}>
      <ul className="space-y-3 text-sm">
        {items.map((it) => (
          <li key={it.id} className="flex items-start gap-3"><IdBadge id={it.id} />
            <span>{it.title}<span className="block text-xs text-muted">{it.reason}</span></span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function MethodCard({ report }: { report: Report }) {
  const { t } = useApp();
  const u = report.usage;
  return (
    <Card title={t("rep.costTitle")}>
      {u && (
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div className="rounded-lg bg-surface-2 p-3"><dt className="text-xs text-muted">LLM calls</dt><dd className="font-mono text-lg">{u.llm_calls}</dd></div>
          <div className="rounded-lg bg-surface-2 p-3"><dt className="text-xs text-muted">Tokens</dt><dd className="font-mono text-lg">{(u.input_tokens + u.output_tokens).toLocaleString()}</dd></div>
          <div className="rounded-lg bg-surface-2 p-3"><dt className="text-xs text-muted">Cost</dt><dd className="font-mono text-lg">${u.cost_usd.toFixed(2)}</dd></div>
          <div className="rounded-lg bg-surface-2 p-3"><dt className="text-xs text-muted">Retrieval</dt><dd className="text-xs">{report.retrieval_mode ?? "-"}</dd></div>
        </dl>
      )}
      {report.health && (
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer font-semibold">{t("health.formula")}</summary>
          <p className="mt-2 font-mono text-xs leading-relaxed text-muted">{report.health.formula}</p>
        </details>
      )}
    </Card>
  );
}