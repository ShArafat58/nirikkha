"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { AuthShell } from "../../components/auth-shell";
import { useApp } from "../../components/providers";
import { useSession } from "../../components/session";
import { Alert, Button, Field, Input } from "../../components/ui";
import { ApiError, demoLogin, login } from "../../lib/api";
import { safeNext } from "../../lib/validation";

function LoginForm() {
  const { t } = useApp();
  const { signIn, user, loading } = useSession();
  const router = useRouter();
  const params = useSearchParams();
  const next = safeNext(params.get("next"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [demoBusy, setDemoBusy] = useState(false);
  const autoDemo = useRef(false);

  useEffect(() => {
    if (!loading && user) router.replace(next);
  }, [loading, user, router, next]);

  const message = useCallback((err: unknown) => (err instanceof ApiError ? err.message : t("auth.err.generic")), [t]);

  const runDemo = useCallback(async () => {
    setError("");
    setDemoBusy(true);
    try {
      await signIn(await demoLogin());
      router.replace(next);
    } catch (err) {
      setError(message(err));
    } finally {
      setDemoBusy(false);
    }
  }, [signIn, router, next, message]);

  useEffect(() => {
    if (params.get("demo") === "1" && !autoDemo.current) {
      autoDemo.current = true;
      void runDemo();
    }
  }, [params, runDemo]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await signIn(await login(email, password));
      router.replace(next);
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title={t("auth.login.title")} subtitle={t("auth.login.subtitle")}>
      <Button variant="secondary" className="w-full" loading={demoBusy} onClick={runDemo}>{t("auth.demo")}</Button>
      <p className="mt-2 text-center text-xs text-muted">{t("auth.demoNote")}</p>

      <div className="my-6 flex items-center gap-3 text-xs uppercase tracking-wider text-muted">
        <span className="h-px flex-1 bg-border" />{t("auth.or")}<span className="h-px flex-1 bg-border" />
      </div>

      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field label={t("auth.email")} htmlFor="email">
          <Input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </Field>
        <Field label={t("auth.password")} htmlFor="password"
               action={<Link href="/forgot" className="text-xs font-medium text-accent hover:underline">{t("auth.forgot")}</Link>}>
          <Input id="password" type="password" autoComplete="current-password" value={password}
                 onChange={(e) => setPassword(e.target.value)} required />
        </Field>
        {error && <Alert>{error}</Alert>}
        <Button type="submit" className="w-full" loading={busy} disabled={!email || !password}>{t("auth.login.submit")}</Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted">
        {t("auth.noAccount")}{" "}
        <Link href="/signup" className="font-semibold text-accent hover:underline">{t("auth.createAccount")}</Link>
      </p>
    </AuthShell>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}