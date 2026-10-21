"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { useApp } from "../../components/providers";
import { useSession } from "../../components/session";
import { Alert, Button } from "../../components/ui";
import { ApiError, checkout, getPlans, type CheckoutMethod, type PaymentRecord, type Plan } from "../../lib/api";
import type { Key } from "../../lib/i18n";

const METHODS: { id: CheckoutMethod; icon: string; title: Key; sub: Key }[] = [
  { id: "mobile_banking", icon: "📱", title: "pay.mobile", sub: "pay.mobileSub" },
  { id: "card", icon: "💳", title: "pay.card", sub: "pay.cardSub" },
  { id: "bank_transfer", icon: "🏦", title: "pay.bank", sub: "pay.bankSub" },
];
const MIN_PROCESSING_MS = 1200;

function CheckoutView() {
  const { t } = useApp();
  const { signedIn, loading, refresh } = useSession();
  const router = useRouter();
  const params = useSearchParams();
  const planId = params.get("plan") ?? "";
  const [plan, setPlan] = useState<Plan | null | undefined>(undefined);
  const [method, setMethod] = useState<CheckoutMethod>("mobile_banking");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState<PaymentRecord | null>(null);

  useEffect(() => {
    if (!loading && !signedIn) router.replace(`/login?next=${encodeURIComponent(`/checkout?plan=${planId}`)}`);
  }, [loading, signedIn, router, planId]);

  useEffect(() => {
    getPlans()
      .then((d) => setPlan(d.plans.find((p) => p.id === planId && p.price_usd) ?? null))
      .catch(() => setPlan(null));
  }, [planId]);

  async function confirm() {
    if (!plan) return;
    setBusy(true);
    setError("");
    const started = Date.now();
    try {
      const rec = await checkout(plan.id, method);
      const wait = MIN_PROCESSING_MS - (Date.now() - started);
      if (wait > 0) await new Promise((r) => setTimeout(r, wait));
      setDone(rec);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("auth.err.generic"));
    } finally {
      setBusy(false);
    }
  }

  const shell = (children: React.ReactNode) => (
    <main className="bg-app min-h-[calc(100vh-4rem)] text-text"><div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">{children}</div></main>
  );

  if (plan === undefined || loading) return shell(<p className="text-muted">{t("dash.loading")}</p>);
  if (plan === null) return shell(<><Alert>{t("co.invalid")}</Alert><Link href="/pricing" className="mt-4 inline-block text-accent hover:underline">← {t("nav.pricing")}</Link></>);

  if (done) {
    const m = METHODS.find((x) => x.id === done.method);
    const row = (label: string, value: React.ReactNode) => (
      <div className="flex justify-between gap-4 border-t border-border py-3 text-sm"><span className="text-muted">{label}</span><span className="text-right font-medium">{value}</span></div>
    );
    return shell(
      <div className="mx-auto max-w-lg rounded-2xl border border-conf-high/40 bg-surface p-8 text-center shadow-2xl shadow-black/20">
        <span className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-conf-high text-4xl font-bold text-bg shadow-lg shadow-conf-high/30">✓</span>
        <h1 className="mt-6 text-2xl font-bold">{t("co.done")}</h1>
        <div className="mt-6 text-left">
          {row(t("co.plan"), done.plan_name ?? plan.name)}
          {row(t("co.amount"), `$${done.amount_usd.toFixed(2)} (${t("co.notCharged")})`)}
          {row(t("co.method"), m ? `${m.icon} ${t(m.title)}` : done.method)}
          {row(t("co.reference"), <span className="font-mono">{done.reference}</span>)}
          {row(t("co.date"), new Date(done.created_at).toLocaleString())}
        </div>
        <p className="mt-4 text-xs leading-relaxed text-muted">{done.note}</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link href="/dashboard" className="rounded-lg bg-accent px-5 py-3 font-semibold text-accent-contrast hover:opacity-90">{t("co.toDashboard")}</Link>
          <Link href="/crash-test" className="rounded-lg border border-border px-5 py-3 font-semibold hover:bg-surface-2">{t("co.runTest")}</Link>
        </div>
      </div>,
    );
  }

  return shell(
    <>
      <Link href="/pricing" className="text-sm text-muted hover:text-text">← {t("nav.pricing")}</Link>
      <h1 className="mt-3 text-3xl font-bold">{t("co.title")}</h1>
      <div className="mt-4 rounded-xl border border-accent/50 bg-accent/10 p-4 text-sm">⚠ {t("co.banner")}</div>

      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_20rem]">
        <section className="space-y-6">
          <div className="rounded-2xl border border-border bg-surface p-6">
            <h2 className="font-semibold">{t("co.step1")}</h2>
            <div className="mt-4 grid gap-3" role="radiogroup">
              {METHODS.map((m) => (
                <button key={m.id} type="button" role="radio" aria-checked={method === m.id} onClick={() => setMethod(m.id)}
                        className={`flex items-center gap-4 rounded-xl border p-4 text-left transition ${method === m.id ? "border-accent bg-accent/10" : "border-border hover:bg-surface-2"}`}>
                  <span className="text-3xl" aria-hidden>{m.icon}</span>
                  <span className="flex-1"><span className="block font-semibold">{t(m.title)}</span><span className="text-sm text-muted">{t(m.sub)}</span></span>
                  <span className={`h-5 w-5 rounded-full border-2 ${method === m.id ? "border-accent bg-accent" : "border-border"}`} aria-hidden />
                </button>
              ))}
            </div>
          </div>
          <div className="rounded-2xl border border-border bg-surface p-6">
            <h2 className="font-semibold">{t("co.step2")}</h2>
            {error && <div className="mt-4"><Alert>{error}</Alert></div>}
            <Button className="mt-4 w-full py-3 text-base" loading={busy} onClick={confirm}>
              {busy ? t("co.processing") : t("co.confirm")}
            </Button>
          </div>
        </section>

        <aside className="h-fit rounded-2xl border border-border bg-surface p-6">
          <h2 className="font-semibold">{t("co.summary")}</h2>
          <p className="mt-4 text-xl font-bold">{plan.name}</p>
          <p className="text-sm text-muted">{plan.audience}</p>
          <ul className="mt-4 space-y-1.5 text-sm">
            {plan.features.slice(0, 4).map((f) => <li key={f} className="flex gap-2"><span className="text-conf-high">✓</span>{f}</li>)}
          </ul>
          <div className="mt-6 flex items-baseline justify-between border-t border-border pt-4">
            <span className="text-sm text-muted">{t("co.today")}</span>
            <span className="text-2xl font-bold">${plan.price_usd}</span>
          </div>
          <p className="mt-1 text-right text-xs text-accent">{t("co.notCharged")}</p>
        </aside>
      </div>
    </>,
  );
}

export default function CheckoutPage() {
  return (
    <Suspense fallback={null}>
      <CheckoutView />
    </Suspense>
  );
}