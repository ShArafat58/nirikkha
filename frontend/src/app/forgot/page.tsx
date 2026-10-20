"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { AuthShell } from "../../components/auth-shell";
import { useApp } from "../../components/providers";
import { useSession } from "../../components/session";
import { Alert, Button, Field, Input, PasswordChecklist } from "../../components/ui";
import { ApiError, forgotPassword, resetPassword } from "../../lib/api";
import { passwordOk } from "../../lib/validation";

export default function ForgotPage() {
  const { t } = useApp();
  const { signIn, user, loading } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [loading, user, router]);
  const [email, setEmail] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const fail = (err: unknown) => setError(err instanceof ApiError ? err.message : t("auth.err.generic"));

  async function findQuestion(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      setQuestion((await forgotPassword(email)).question);
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function reset(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!passwordOk(password)) return setError(t("auth.err.password"));
    if (password !== confirm) return setError(t("auth.err.match"));
    setBusy(true);
    try {
      await signIn(await resetPassword(email, answer, password));
      router.replace("/dashboard");
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title={t("auth.forgot.title")} subtitle={t("auth.forgot.subtitle")}>
      {!question ? (
        <form onSubmit={findQuestion} className="space-y-4" noValidate>
          <Field label={t("auth.email")} htmlFor="email">
            <Input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          {error && <Alert>{error}</Alert>}
          <Button type="submit" className="w-full" loading={busy} disabled={!email}>{t("auth.forgot.next")}</Button>
        </form>
      ) : (
        <form onSubmit={reset} className="space-y-4" noValidate>
          <div className="rounded-lg border border-border bg-surface-2 px-3 py-2.5 text-sm">
            <span className="block text-xs text-muted">{t("auth.question")}</span>
            {question}
          </div>
          <Field label={t("auth.answer")} htmlFor="answer">
            <Input id="answer" autoComplete="off" value={answer} onChange={(e) => setAnswer(e.target.value)} />
          </Field>
          <Field label={t("auth.newPassword")} htmlFor="password">
            <Input id="password" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <PasswordChecklist password={password} />
          </Field>
          <Field label={t("auth.confirm")} htmlFor="confirm">
            <Input id="confirm" type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          </Field>
          {error && <Alert>{error}</Alert>}
          <Button type="submit" className="w-full" loading={busy} disabled={!answer || !password}>{t("auth.forgot.submit")}</Button>
        </form>
      )}
      <p className="mt-6 text-center text-sm">
        <Link href="/login" className="font-semibold text-accent hover:underline">← {t("auth.forgot.back")}</Link>
      </p>
    </AuthShell>
  );
}