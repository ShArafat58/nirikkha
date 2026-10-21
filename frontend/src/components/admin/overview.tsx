"use client";

import { useEffect, useState } from "react";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { adminOverview, getStatus, type AdminOverview } from "../../lib/api";
import { useApp } from "../providers";
import { Card } from "../report/health-panel";

const PLAN_LABEL: Record<string, string> = { free: "Free", analyst_pro: "Analyst Pro", team: "Team", enterprise: "Enterprise" };
const PLAN_COLOR: Record<string, string> = { free: "var(--muted)", analyst_pro: "var(--accent)", team: "var(--conf-medium)", enterprise: "var(--conf-high)" };
const STATUS_COLOR: Record<string, string> = { done: "bg-conf-high", running: "bg-accent", queued: "bg-conf-medium", failed: "bg-sev-critical", blocked: "bg-sev-high" };

export function useAdminFetch<T>(load: () => Promise<T>, onAuthError: () => void, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    load()
      .then((d) => {
        if (alive) setData(d);
      })
      .catch((err: { status?: number; message?: string }) => {
        if (!alive) return;
        if (err?.status === 401) onAuthError();
        else setError(err?.message ?? "Error");
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { data, error, reload: () => setTick((n) => n + 1), setData };
}

function Kpi({ label, value, note }: { label: string; value: React.ReactNode; note?: string }) {
  return (
    <div className="rounded-2xl border border-border bg-surface/90 p-5 shadow-lg shadow-black/10">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-3xl font-semibold tabular-nums">{value}</p>
      {note && <p className="mt-1 text-xs text-muted">{note}</p>}
    </div>
  );
}

export function AdminOverviewTab({ token, onAuthError }: { token: string; onAuthError: () => void }) {
  const { t } = useApp();
  const { data: o, error } = useAdminFetch<AdminOverview>(() => adminOverview(token), onAuthError, [token]);
  const [worker, setWorker] = useState<boolean | null>(null);
  useEffect(() => {
    getStatus().then((s) => setWorker(s.worker_online)).catch(() => setWorker(null));
  }, []);

  if (error) return <p className="text-sev-critical">{error}</p>;
  if (!o) return <p className="text-muted">{t("dash.loading")}</p>;

  const plans = ["free", "analyst_pro", "team", "enterprise"].map((p) => ({ plan: p, label: PLAN_LABEL[p], n: o.users_by_plan[p] ?? 0 }));
  const m = o.unit_economics.measured;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <Kpi label={t("adm.users")} value={o.signups?.users ?? 0} note={`+${o.signups?.last_30_days ?? 0} ${t("adm.new30")}`} />
        <Kpi label={t("adm.runsMonth")} value={o.crash_tests_this_month} />
        <Kpi label={t("adm.openReq")} value={o.open_plan_requests} />
        <Kpi label={t("adm.simSubs")} value={o.simulated_payments?.n ?? 0} note={`$${(o.simulated_payments?.total_usd ?? 0).toLocaleString()} · ${t("co.notCharged")}`} />
        <Kpi label={t("adm.mrr")} value={`$${o.projected_revenue.total_monthly_usd.toLocaleString()}`} note={o.projected_revenue.label} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title={t("adm.byPlan")}>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={plans} margin={{ top: 10, right: 10, bottom: 0, left: -20 }}>
                <XAxis dataKey="label" tick={{ fill: "var(--muted)", fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fill: "var(--muted)", fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip cursor={{ fill: "var(--surface-2)" }}
                         contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text)" }} />
                <Bar dataKey="n" name="accounts" radius={[6, 6, 0, 0]} barSize={36}>
                  {plans.map((p) => <Cell key={p.plan} fill={PLAN_COLOR[p.plan]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <ul className="mt-4 space-y-1 text-sm">
            {o.projected_revenue.lines.map((l) => (
              <li key={l.plan} className="flex justify-between"><span>{PLAN_LABEL[l.plan]} · {l.accounts}</span>
                <span className="font-mono">{l.monthly_usd === null ? l.note : `$${l.monthly_usd.toLocaleString()}/mo`}</span></li>
            ))}
          </ul>
        </Card>

        <Card title={t("adm.unit")}>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-lg bg-surface-2 p-3"><dt className="text-xs text-muted">{t("adm.avgTokens")}</dt><dd className="font-mono text-lg">{m.avg_tokens?.toLocaleString() ?? "-"}</dd></div>
            <div className="rounded-lg bg-surface-2 p-3"><dt className="text-xs text-muted">{t("adm.avgCalls")}</dt><dd className="font-mono text-lg">{m.avg_llm_calls ?? "-"}</dd></div>
            <div className="rounded-lg bg-surface-2 p-3"><dt className="text-xs text-muted">{t("adm.avgTime")}</dt><dd className="font-mono text-lg">{m.avg_seconds ? `${m.avg_seconds} s` : "-"}</dd></div>
            <div className="rounded-lg bg-surface-2 p-3"><dt className="text-xs text-muted">{t("adm.infra")}</dt><dd className="font-mono text-lg">${m.infra_cost_usd_total.toFixed(2)}</dd></div>
          </dl>
          <h3 className="mt-5 text-sm font-semibold text-muted">{t("adm.revPer")}</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {o.unit_economics.revenue_per_crash_test.map((r) => (
              <li key={r.plan} className="flex justify-between"><span>{PLAN_LABEL[r.plan]}</span><span className="font-mono">${r.revenue_per_crash_test_usd.toFixed(2)}</span></li>
            ))}
          </ul>
          <p className="mt-4 text-xs leading-relaxed text-muted">{o.unit_economics.note}</p>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title={t("adm.models")} className="lg:col-span-2">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[32rem] text-sm">
              <thead><tr className="text-left text-xs text-muted"><th className="py-2">Model</th><th>Step</th><th className="text-right">Calls</th><th className="text-right">Tokens in / out</th><th className="text-right">Avg latency</th></tr></thead>
              <tbody>
                {o.model_usage.map((u) => (
                  <tr key={`${u.model}-${u.node}`} className="border-t border-border">
                    <td className="py-2 font-mono text-xs">{u.model}</td><td>{u.node}</td><td className="text-right font-mono">{u.calls}</td>
                    <td className="text-right font-mono">{u.input_tokens.toLocaleString()} / {u.output_tokens.toLocaleString()}</td>
                    <td className="text-right font-mono">{(u.avg_latency_ms / 1000).toFixed(1)} s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <Card title={t("adm.status")}>
          <ul className="space-y-2 text-sm">
            {o.crash_tests_by_status.map((s) => (
              <li key={s.status} className="flex items-center justify-between">
                <span className="flex items-center gap-2"><span className={`h-2.5 w-2.5 rounded-full ${STATUS_COLOR[s.status] ?? "bg-muted"}`} />{s.status}</span>
                <span className="font-mono">{s.n}</span>
              </li>
            ))}
          </ul>
          <p className="mt-5 flex items-center gap-2 text-sm">
            <span className={`h-2.5 w-2.5 rounded-full ${worker ? "bg-conf-high" : "bg-sev-critical"}`} />
            {t("adm.worker")}: {worker ? t("adm.workerOn") : t("adm.workerOff")}
          </p>
        </Card>
      </div>
    </div>
  );
}