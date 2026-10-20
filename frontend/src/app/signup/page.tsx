"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { AuthShell } from "../../components/auth-shell";
import { useApp } from "../../components/providers";
import { useSession } from "../../components/session";
import { Alert, Button, Field, Input, PasswordChecklist, Select } from "../../components/ui";
import { ApiError, getQuestions, signup } from "../../lib/api";
import { isAdult, maxBirthDate, passwordOk } from "../../lib/validation";

type Errors = Partial<Record<"name" | "email" | "dob" | "password" | "confirm" | "question" | "answer", string>>;

export default function SignupPage() {
  const { t } = useApp();
  const { signIn, user, loading } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [loading, user, router]);
  const [questions, setQuestions] = useState<string[]>([]);
  const [maxDob, setMaxDob] = useState<string>();
  const [form, setForm] = useState({ name: "", email: "", dob: "", password: "", confirm: "", question: "", answer: "",
                                     organization: "", job_role: "" });
  const [errors, setErrors] = useState<Errors>({});
  const [serverError, setServerError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setMaxDob(maxBirthDate());
    getQuestions().then(setQuestions).catch(() => setServerError(t("auth.err.generic")));
  }, [t]);

  const set = (key: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [key]: e.target.value }));

  function validate(): Errors {
    const e: Errors = {};
    if (!form.name.trim()) e.name = t("auth.err.required");
    if (!form.email.trim()) e.email = t("auth.err.required");
    if (!form.dob) e.dob = t("auth.err.required");
    else if (!isAdult(form.dob)) e.dob = t("auth.err.age");
    if (!passwordOk(form.password)) e.password = t("auth.err.password");
    if (form.confirm !== form.password) e.confirm = t("auth.err.match");
    if (!form.question) e.question = t("auth.err.required");
    if (form.answer.trim().length < 2) e.answer = t("auth.err.required");
    return e;
  }

  async function onSubmit(ev: FormEvent) {
    ev.preventDefault();
    setServerError("");
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length) return;
    setBusy(true);
    try {
      const session = await signup({ name: form.name, email: form.email, password: form.password, date_of_birth: form.dob,
        security_question: form.question, security_answer: form.answer,
        organization: form.organization || undefined, job_role: form.job_role || undefined });
      await signIn(session);
      router.replace("/dashboard");
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : t("auth.err.generic"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title={t("auth.signup.title")} subtitle={t("auth.signup.subtitle")}>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field label={t("auth.name")} htmlFor="name" error={errors.name}>
          <Input id="name" autoComplete="name" value={form.name} onChange={set("name")} invalid={!!errors.name} />
        </Field>
        <Field label={t("auth.email")} htmlFor="email" error={errors.email}>
          <Input id="email" type="email" autoComplete="email" value={form.email} onChange={set("email")} invalid={!!errors.email} />
        </Field>
        <Field label={t("auth.dob")} htmlFor="dob" hint={t("auth.dobHint")} error={errors.dob}>
          <Input id="dob" type="date" max={maxDob} value={form.dob} onChange={set("dob")} invalid={!!errors.dob} />
        </Field>
        <Field label={t("auth.password")} htmlFor="password" error={errors.password}>
          <Input id="password" type="password" autoComplete="new-password" value={form.password} onChange={set("password")}
                 invalid={!!errors.password} />
          <PasswordChecklist password={form.password} />
        </Field>
        <Field label={t("auth.confirm")} htmlFor="confirm" error={errors.confirm}>
          <Input id="confirm" type="password" autoComplete="new-password" value={form.confirm} onChange={set("confirm")}
                 invalid={!!errors.confirm} />
        </Field>
        <Field label={t("auth.question")} htmlFor="question" hint={t("auth.questionHint")} error={errors.question}>
          <Select id="question" value={form.question} onChange={set("question")} invalid={!!errors.question}>
            <option value="">{t("auth.chooseQuestion")}</option>
            {questions.map((q) => <option key={q} value={q}>{q}</option>)}
          </Select>
        </Field>
        <Field label={t("auth.answer")} htmlFor="answer" error={errors.answer}>
          <Input id="answer" autoComplete="off" value={form.answer} onChange={set("answer")} invalid={!!errors.answer} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("auth.org")} htmlFor="organization">
            <Input id="organization" autoComplete="organization" value={form.organization} onChange={set("organization")} />
          </Field>
          <Field label={t("auth.role")} htmlFor="job_role">
            <Input id="job_role" autoComplete="organization-title" value={form.job_role} onChange={set("job_role")} />
          </Field>
        </div>
        {serverError && <Alert>{serverError}</Alert>}
        <Button type="submit" className="w-full" loading={busy}>{t("auth.signup.submit")}</Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted">
        {t("auth.haveAccount")}{" "}
        <Link href="/login" className="font-semibold text-accent hover:underline">{t("auth.login.submit")}</Link>
      </p>
    </AuthShell>
  );
}