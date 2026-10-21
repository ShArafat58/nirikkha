"use client";

import Link from "next/link";

import { adminJobs, type AdminRow } from "../../lib/api";
import { useApp } from "../providers";
import { Alert } from "../ui";
import { Chip, pick, str, when } from "./cells";
import { useAdminFetch } from "./overview";
import { Loader } from "../loader";

export function AdminJobsTab({ token, onAuthError }: { token: string; onAuthError: () => void }) {
  const app = useApp();
  const bn = (app as unknown as { lang?: string }).lang === "bn";
  const { data, error } = useAdminFetch<AdminRow[]>(() => adminJobs(token), onAuthError, [token]);
  const th = "px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-muted";
  const td = "px-3 py-2.5 align-top";
  const counts = (data ?? []).reduce<Record<string, number>>((m, j) => { const s = str(j.status); m[s] = (m[s] ?? 0) + 1; return m; }, {});
  return (
    <div className="space-y-4">
      {error && <Alert>{error}</Alert>}
      {!data && !error && <Loader className="py-10" />}
      <div className="flex flex-wrap gap-2">{Object.entries(counts).map(([s, n]) => (
        <span key={s} className="flex items-center gap-1.5 text-sm"><Chip value={s} /> {n}</span>))}</div>
      {data && (<div className="overflow-x-auto rounded-xl border border-border">
        <table className="w-full min-w-[900px] text-sm">
          <thead className="bg-surface-2"><tr>
            <th className={th}>{bn ? "সময়" : "Created"}</th><th className={th}>{bn ? "কোম্পানি" : "Company"}</th>
            <th className={th}>{bn ? "ফ্রিজ" : "As of"}</th><th className={th}>{bn ? "অবস্থা" : "Status"}</th>
            <th className={th}>{bn ? "উৎস" : "Source"}</th><th className={th}>{bn ? "সময় / টোকেন" : "Time / tokens"}</th>
            <th className={th}>{bn ? "ত্রুটি" : "Error"}</th><th className={th}></th>
          </tr></thead>
          <tbody>
            {(data ?? []).map((j) => {
              const ms = Number(pick(j, ["elapsed_ms", "duration_ms", "ms"]) ?? 0);
              const tokens = pick(j, ["tokens", "total_tokens", "usage.tokens"]);
              return (
                <tr key={str(j.id)} className="border-t border-border">
                  <td className={`${td} text-xs`}>{when(pick(j, ["created_at", "started_at", "updated_at"]))}</td>
                  <td className={td}><p className="font-medium">{str(j.company) || str(j.cik)}</p><p className="font-mono text-[11px] text-muted">{str(j.id).slice(0, 8)}</p></td>
                  <td className={`${td} text-xs`}>{str(j.as_of)}</td>
                  <td className={td}><Chip value={j.status} /></td>
                  <td className={`${td} text-xs`}>{str(j.source)}</td>
                  <td className={`${td} text-xs`}>{ms ? `${Math.round(ms / 1000)} s` : "—"}{tokens ? ` · ${str(tokens)}` : ""}</td>
                  <td className={`${td} max-w-[260px] text-xs text-rose-500`}>{str(j.error).slice(0, 160)}</td>
                  <td className={td}>{str(j.status) === "done" && <Link href={`/report/${str(j.id)}`} className="text-xs text-sky-500 hover:underline">{bn ? "রিপোর্ট" : "Report"} ↗</Link>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>)}
    </div>
  );
}
