"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import { useApp } from "../../components/providers";
import { BandBadge, ScoreNumber } from "../../components/score";
import { useSession } from "../../components/session";
import { Alert, Button, Field, Select } from "../../components/ui";
import { ApiError, demoLogin, getCompanies, getStatus, startCrashTest, type Company } from "../../lib/api";

const SVB_CIK = "0000719739";
const EXAMPLES = [
  "Before we proceed with a deposit partnership with this bank, identify the governance risks and evidence gaps we should investigate.",
  "Before we extend a credit line to this company, check board oversight of liquidity risk and related-party exposure.",
  "Before we invest in this company, check board independence, related-party transactions and outside roles of executives.",
];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function CrashTestPage() {
  const { t } = useApp();
  const { signedIn, signIn } = useSession();
  const router = useRouter();
  const [companies, setCompanies] = useState<Company[] | null>(null);
  const [workerOnline, setWorkerOnline] = useState<boolean | null>(null);
  const [cik, setCik] = useState("");
  const [asOf, setAsOf] = useState("");
  const [decision, setDecision] = useState(EXAMPLES[0]);
  const [error, setError] = useState("");
  const [errorStatus, setErrorStatus] = useState(0);
  const [busy, setBusy] = useState(false);
  const [needLogin, setNeedLogin] = useState(false);

  useEffect(() => {
    getCompanies()
      .then((list) => {
        setCompanies(list);
        const first = list.find((c) => c.cik === SVB_CIK) ?? list[0];
        if (first) {
          setCik(first.cik);
          setAsOf(first.cik === SVB_CIK ? "2023-03-10" : today());
        }
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : t("auth.err.generic")));
    getStatus().then((s) => setWorkerOnline(s.worker_online)).catch(() => setWorkerOnline(null));
  }, [t]);

  const demos = useMemo(
    () => (companies ?? []).flatMap((c) => c.crash_tests.map((r) => ({ ...r, company: c.company }))),
    [companies],
  );

  function pickCompany(value: string) {
    setCik(value);
    setAsOf(value === SVB_CIK ? "2023-03-10" : today());
  }

  async function run() {
    setError("");
    setErrorStatus(0);
    setBusy(true);
    try {
      const started = await startCrashTest(cik, asOf, decision);
      router.push(started.cached ? `/report/${started.id}` : `/crash-test/${started.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setNeedLogin(true);
      } else {
        setError(err instanceof ApiError ? err.message : t("auth.err.generic"));
        setErrorStatus(err instanceof ApiError ? err.status : 0);
      }
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!signedIn) {
      setNeedLogin(true);
      return;
    }
    await run();
  }

  async function continueAsDemo() {
    setBusy(true);
    try {
      await signIn(await demoLogin());
      setNeedLogin(false);
      await run();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("auth.err.generic"));
      setBusy(false);
    }
  }

  return (
    <main className="bg-app min-h-[calc(100vh-4rem)] text-text">
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <h1 className="text-3xl font-bold">{t("ct.title")}</h1>
        <p className="mt-2 max-w-2xl text-muted">{t("ct.subtitle")}</p>

        <section className="mt-10">
          <div className="flex flex-wrap items-baseline gap-x-3">
            <h2 className="text-xl font-semibold">{t("ct.demos")}</h2>
            <p className="text-sm text-muted">{t("ct.demosNote")}</p>
          </div>
          {companies === null && !error && <p className="mt-4 text-sm text-muted">{t("dash.loading")}</p>}
          <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {demos.map((d) => (
              <Link key={d.id} href={`/report/${d.id}`}
                    className="group flex flex-col rounded-xl border border-border bg-surface p-5 transition hover:border-accent/60">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold">{d.company}</span>
                  <ScoreNumber score={d.score} />
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted">
                  <BandBadge band={d.band} />
                  <span className="font-mono">as of {d.as_of}</span>
                </div>
                <p className="mt-3 line-clamp-3 text-sm text-text/85">{d.decision}</p>
                <span className="mt-4 text-sm font-semibold text-accent group-hover:underline">{t("ct.open")} →</span>
              </Link>
            ))}
          </div>
        </section>

        <section className="mt-12 rounded-2xl border border-border bg-surface p-6 sm:p-8">
          <h2 className="text-xl font-semibold">{t("ct.new")}</h2>
          {workerOnline === false && <div className="mt-4"><Alert kind="info">{t("ct.workerOff")}</Alert></div>}
          <form onSubmit={onSubmit} className="mt-6 space-y-5" noValidate>
            <div className="grid gap-5 sm:grid-cols-2">
              <Field label={t("ct.company")} htmlFor="company">
                <Select id="company" value={cik} onChange={(e) => pickCompany(e.target.value)} disabled={!companies?.length}>
                  {!companies?.length && <option value="">{t("ct.noCompanies")}</option>}
                  {companies?.map((c) => (
                    <option key={c.cik} value={c.cik}>{c.company} ({c.filing_count} {t("ct.filings")})</option>
                  ))}
                </Select>
              </Field>
              <Field label={t("ct.asOf")} htmlFor="asof" hint={t("ct.asOfHint")}>
                <input id="asof" type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)}
                       className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2.5 text-sm text-text focus:border-accent focus:outline-none" />
              </Field>
            </div>
            <Field label={t("ct.decision")} htmlFor="decision" hint={t("ct.decisionHint")}>
              <textarea id="decision" rows={4} maxLength={1500} value={decision} onChange={(e) => setDecision(e.target.value)}
                        className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2.5 text-sm text-text focus:border-accent focus:outline-none" />
            </Field>
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted">{t("ct.examples")}</p>
              <div className="flex flex-wrap gap-2">
                {EXAMPLES.map((ex) => (
                  <button key={ex} type="button" onClick={() => setDecision(ex)}
                          className={`rounded-full border px-3 py-1.5 text-left text-xs transition ${decision === ex ? "border-accent bg-accent/10 text-accent" : "border-border text-muted hover:text-text"}`}>
                    {ex.length > 70 ? `${ex.slice(0, 70)}...` : ex}
                  </button>
                ))}
              </div>
            </div>

            {needLogin && (
              <div className="rounded-lg border border-accent/50 bg-accent/10 p-4">
                <p className="text-sm">{t("ct.needLogin")}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button onClick={continueAsDemo} loading={busy}>{t("auth.demo")}</Button>
                  <Link href="/login?next=/crash-test" className="inline-flex items-center rounded-lg border border-border px-4 py-2.5 text-sm font-semibold hover:bg-surface-2">
                    {t("nav.login")}
                  </Link>
                </div>
              </div>
            )}
            {error && (
              <Alert>
                {error}{" "}
                {errorStatus === 403 && <Link href="/pricing" className="font-semibold text-accent underline">{t("ct.limit")}</Link>}
              </Alert>
            )}
            <Button type="submit" className="w-full sm:w-auto" loading={busy && !needLogin}
                    disabled={!cik || !asOf || decision.trim().length < 10}>
              {t("ct.start")}
            </Button>
          </form>
        </section>
      </div>
    </main>
  );
}