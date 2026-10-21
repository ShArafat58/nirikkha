"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AdminDemosTab } from "../../components/admin/demos";
import { AdminOverviewTab } from "../../components/admin/overview";
import { useApp } from "../../components/providers";
import { useSession } from "../../components/session";
import { Alert, Button, Field, Input } from "../../components/ui";
import { ApiError, adminSession, login } from "../../lib/api";
import type { Key } from "../../lib/i18n";

const TABS = ["overview", "demos"] as const;
type Tab = (typeof TABS)[number];

function StepUp({ onUnlock }: { onUnlock: (token: string, ttl: number) => void }) {
  const { t } = useApp();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const s = await adminSession(password);
      setPassword("");
      onUnlock(s.token, s.expires_in);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("auth.err.generic"));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="mx-auto mt-16 max-w-md rounded-2xl border border-conf-medium/40 bg-surface p-8 shadow-2xl shadow-black/30">
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-conf-medium/15 text-2xl" aria-hidden>🔒</span>
      <h1 className="mt-5 text-2xl font-bold">{t("adm.confirm")}</h1>
      <p className="mt-2 text-sm text-muted">{t("adm.confirmNote")}</p>
      <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
        <Field label={t("auth.password")} htmlFor="admin-password">
          <Input id="admin-password" type="password" autoComplete="current-password" autoFocus value={password}
                 onChange={(e) => setPassword(e.target.value)} />
        </Field>
        {error && <Alert>{error}</Alert>}
        <Button type="submit" className="w-full" loading={busy} disabled={!password}>{t("adm.unlock")}</Button>
      </form>
    </div>
  );
}

function AdminSignIn({ currentEmail, onUnlock }: {
  currentEmail?: string | null;
  onUnlock: (token: string, ttl: number) => void;
}) {
  const { t } = useApp();
  const { signIn } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const session = await login(email.trim(), password);
      if (session.user.role !== "admin") {
        setError(t("adm.notAdmin"));
        return;
      }
      await signIn(session);
      const s = await adminSession(password);
      setPassword("");
      onUnlock(s.token, s.expires_in);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("auth.err.generic"));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="mx-auto mt-16 max-w-md rounded-2xl border border-conf-medium/40 bg-surface p-8 shadow-2xl shadow-black/30">
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-conf-medium/15 text-2xl" aria-hidden>🛡️</span>
      <h1 className="mt-5 text-2xl font-bold">{t("adm.signinTitle")}</h1>
      <p className="mt-2 text-sm text-muted">{t("adm.signinNote")}</p>
      {currentEmail && (
        <p className="mt-3 rounded-lg bg-surface-2 px-3 py-2 text-xs text-muted">{t("adm.signedInAs")} {currentEmail}</p>
      )}
      <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
        <Field label={t("auth.email")} htmlFor="admin-email">
          <Input id="admin-email" type="email" autoComplete="username" autoFocus value={email}
                 onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label={t("auth.password")} htmlFor="admin-signin-password">
          <Input id="admin-signin-password" type="password" autoComplete="current-password" value={password}
                 onChange={(e) => setPassword(e.target.value)} />
        </Field>
        {error && <Alert>{error}</Alert>}
        <Button type="submit" className="w-full" loading={busy} disabled={!email || !password}>{t("adm.signinButton")}</Button>
      </form>
    </div>
  );
}

export default function AdminPage() {
  const { t } = useApp();
  const { user, loading } = useSession();
  const [token, setToken] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState(0);
  const [now, setNow] = useState(0);
  const [tab, setTab] = useState<Tab>("overview");


  useEffect(() => {
    if (!token) return;
    setNow(Date.now());
    const timer = setInterval(() => setNow(Date.now()), 15_000);
    return () => clearInterval(timer);
  }, [token]);

  const lock = useCallback(() => setToken(null), []);
  useEffect(() => {
    if (token && now && now >= expiresAt) lock();
  }, [token, now, expiresAt, lock]);

  const shell = (children: React.ReactNode) => (
    <main className="bg-admin min-h-[calc(100vh-4rem)] text-text">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">{children}</div>
    </main>
  );

  if (loading) return shell(<p className="text-muted">{t("dash.loading")}</p>);
  if (!user || user.role !== "admin") return shell(<AdminSignIn currentEmail={user?.email} onUnlock={(tok, ttl) => { setToken(tok); setExpiresAt(Date.now() + ttl * 1000); }} />);
  if (!token) return shell(<StepUp onUnlock={(tok, ttl) => { setToken(tok); setExpiresAt(Date.now() + ttl * 1000); }} />);

  const minutes = Math.max(0, Math.ceil((expiresAt - (now || Date.now())) / 60_000));

  return shell(
    <>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-conf-medium">{t("nav.admin")}</p>
          <h1 className="mt-1 text-3xl font-bold">{t("adm.title")}</h1>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="rounded-full border border-conf-medium/40 bg-conf-medium/10 px-3 py-1 font-mono text-xs">
            {t("adm.session")}: {minutes} {t("adm.minLeft")}
          </span>
          <Button variant="ghost" onClick={lock}>🔒 {t("adm.lock")}</Button>
        </div>
      </div>

      <nav className="mt-6 flex gap-1 overflow-x-auto border-b border-border" role="tablist">
        {TABS.map((id) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(id)}
                  className={`whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-semibold transition ${tab === id ? "border-conf-medium text-text" : "border-transparent text-muted hover:text-text"}`}>
            {t(`adm.tab.${id}` as Key)}
          </button>
        ))}
      </nav>

      <div className="mt-6">
        {tab === "overview" && <AdminOverviewTab token={token} onAuthError={lock} />}
        {tab === "demos" && <AdminDemosTab token={token} onAuthError={lock} />}
      </div>
    </>,
  );
}