"use client";

import Link from "next/link";
import { useState } from "react";

import { adminDemos, adminSetDemo, type AdminDemo } from "../../lib/api";
import { useApp } from "../providers";
import { BandBadge, ScoreNumber } from "../score";
import { useAdminFetch } from "./overview";

export function AdminDemosTab({ token, onAuthError }: { token: string; onAuthError: () => void }) {
  const { t } = useApp();
  const { data, error, setData } = useAdminFetch<AdminDemo[]>(() => adminDemos(token), onAuthError, [token]);
  const [busy, setBusy] = useState<string | null>(null);

  async function toggle(d: AdminDemo) {
    setBusy(d.id);
    try {
      const r = await adminSetDemo(token, d.id, !d.featured);
      setData((list) => (list ?? []).map((x) => (x.id === d.id ? { ...x, featured: r.featured } : x)));
    } catch (err) {
      if ((err as { status?: number }).status === 401) onAuthError();
    } finally {
      setBusy(null);
    }
  }

  if (error) return <p className="text-sev-critical">{error}</p>;
  if (!data) return <p className="text-muted">{t("dash.loading")}</p>;
  return (
    <div>
      <p className="mb-4 text-sm text-muted">{t("adm.demosNote")}</p>
      <ul className="space-y-3">
        {data.map((d) => (
          <li key={d.id} className={`flex flex-col gap-4 rounded-2xl border p-5 sm:flex-row sm:items-center ${d.featured ? "border-accent/50 bg-accent/5" : "border-border bg-surface/90"}`}>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">{d.company}</span>
                <ScoreNumber score={d.score} /><BandBadge band={d.band} />
                <span className="font-mono text-xs text-muted">as of {d.as_of}</span>
              </div>
              <p className="mt-1 line-clamp-2 text-sm text-text/85">{d.decision}</p>
              <p className="mt-1 text-xs text-muted">{d.email ?? "-"} · {new Date(d.updated_at).toLocaleString()}</p>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <Link href={`/report/${d.id}`} className="text-sm font-semibold text-accent hover:underline">{t("ct.open")} →</Link>
              <button type="button" role="switch" aria-checked={d.featured} onClick={() => toggle(d)} disabled={busy === d.id}
                      className={`relative h-7 w-12 rounded-full transition ${d.featured ? "bg-accent" : "bg-surface-2"} disabled:opacity-50`}>
                <span className={`absolute top-1 h-5 w-5 rounded-full bg-white shadow transition-all ${d.featured ? "left-6" : "left-1"}`} />
              </button>
              <span className="w-28 text-xs text-muted">{d.featured ? t("adm.featured") : t("adm.hidden")}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}