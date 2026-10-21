"use client";

import { useState } from "react";

import { adminPlanRequests, adminSetPlan, adminSetRequestStatus, adminUsers, type AdminRow, type PlanId } from "../../lib/api";
import { useApp } from "../providers";
import { Alert } from "../ui";
import { Chip, pick, str, when } from "./cells";
import { useAdminFetch } from "./overview";
import { Loader } from "../loader";

const PLANS: PlanId[] = ["free", "analyst_pro", "team", "enterprise"];
const PLAN_TONE: Record<string, string> = {
  free: "border-slate-500/50 text-slate-400", analyst_pro: "border-sky-500/60 text-sky-500",
  team: "border-emerald-500/60 text-emerald-500", enterprise: "border-amber-500/60 text-amber-500",
};
const STATUSES = ["open", "contacted", "closed"];

export function AdminUsersTab({ token, onAuthError }: { token: string; onAuthError: () => void }) {
  const app = useApp();
  const bn = (app as unknown as { lang?: string }).lang === "bn";
  const users = useAdminFetch<AdminRow[]>(() => adminUsers(token), onAuthError, [token]);
  const reqs = useAdminFetch<AdminRow[]>(() => adminPlanRequests(token), onAuthError, [token]);
  const [msg, setMsg] = useState("");

  async function changePlan(id: string, plan: PlanId) {
    try {
      await adminSetPlan(token, id, plan);
      users.setData((list) => (list ?? []).map((u) => (str(u.id) === id ? { ...u, plan } : u)));
      setMsg(bn ? "প্ল্যান বদলানো হয়েছে" : "Plan updated");
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }
  async function changeStatus(id: string, status: string) {
    try {
      await adminSetRequestStatus(token, id, status);
      reqs.setData((list) => (list ?? []).map((r) => (str(r.id) === id ? { ...r, status } : r)));
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }

  const th = "px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-muted";
  const td = "px-3 py-2.5 align-top";
  return (
    <div className="space-y-8">
      {msg && <p className="text-sm text-conf-medium">{msg}</p>}
      <section>
        <h2 className="text-lg font-semibold">{bn ? "অ্যাকাউন্ট" : "Accounts"} {users.data && <span className="text-muted">({users.data.length})</span>}</h2>
        {users.error && <Alert>{users.error}</Alert>}
        {!users.data && !users.error && <Loader className="py-10" />}
        {users.data && (<div className="mt-3 overflow-x-auto rounded-xl border border-border">
          <table className="w-full min-w-[820px] text-sm">
            <thead className="bg-surface-2"><tr>
              <th className={th}>{bn ? "নাম / ইমেইল" : "Name / email"}</th><th className={th}>{bn ? "প্রতিষ্ঠান" : "Organization"}</th>
              <th className={th}>{bn ? "ভূমিকা" : "Role"}</th><th className={th}>{bn ? "প্ল্যান" : "Plan"}</th>
              <th className={th}>{bn ? "এই মাসে রান" : "Runs this month"}</th><th className={th}>{bn ? "যোগদান" : "Joined"}</th>
              <th className={th}>{bn ? "শেষ লগইন" : "Last login"}</th>
            </tr></thead>
            <tbody>
              {(users.data ?? []).map((u) => (
                <tr key={str(u.id)} className="border-t border-border">
                  <td className={td}><p className="font-medium">{str(u.name)}</p><p className="text-xs text-muted">{str(u.email)}</p></td>
                  <td className={td}>{str(pick(u, ["organization"])) || "—"}<p className="text-xs text-muted">{str(u.job_role)}</p></td>
                  <td className={td}><Chip value={u.role} /></td>
                  <td className={td}>
                    <select value={str(u.plan)} onChange={(e) => changePlan(str(u.id), e.target.value as PlanId)}
                            className={`rounded-md border bg-transparent px-2 py-1 text-xs font-semibold ${PLAN_TONE[str(u.plan)] ?? "border-border"}`}>
                      {PLANS.map((p) => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </td>
                  <td className={td}>{str(pick(u, ["crash_tests_this_month", "used_this_month", "runs_this_month", "usage"])) || "0"}</td>
                  <td className={`${td} text-xs`}>{when(u.created_at)}</td>
                  <td className={`${td} text-xs`}>{when(u.last_login_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>)}
      </section>

      <section>
        <h2 className="text-lg font-semibold">{bn ? "আপগ্রেড ও পাইলট অনুরোধ" : "Upgrade and pilot requests"}</h2>
        {reqs.error && <Alert>{reqs.error}</Alert>}
        {!reqs.data && !reqs.error && <Loader className="py-6" />}
        <ul className="mt-3 space-y-2">
          {reqs.data && reqs.data.length === 0 && <li className="text-sm text-muted">{bn ? "কোনো অনুরোধ নেই।" : "No requests yet."}</li>}
          {(reqs.data ?? []).map((r) => (
            <li key={str(r.id)} className="flex flex-wrap items-center gap-3 rounded-xl border border-border p-3 text-sm">
              <Chip value={r.kind} /><span className="font-medium">{str(r.plan)}</span>
              <span className="text-muted">{str(r.name)} · {str(r.email)}{r.organization ? ` · ${str(r.organization)}` : ""}</span>
              {r.note ? <span className="text-xs italic text-muted">“{str(r.note)}”</span> : null}
              <span className="ml-auto text-xs text-muted">{when(r.created_at)}</span>
              <select value={str(r.status)} onChange={(e) => changeStatus(str(r.id), e.target.value)}
                      className="rounded-md border border-border bg-transparent px-2 py-1 text-xs">
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
