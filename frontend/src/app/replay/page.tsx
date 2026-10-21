"use client";

import { useEffect, useState } from "react";

import { useApp } from "../../components/providers";
import { ReplayView } from "../../components/replay/replay-view";
import { Alert } from "../../components/ui";
import { getReplay, type ReplayData } from "../../lib/replay";
import { Loader } from "../../components/loader";

export default function ReplayPage() {
  const app = useApp();
  const lang = (app as unknown as { lang?: string }).lang === "bn" ? "bn" : "en";
  const [data, setData] = useState<ReplayData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    getReplay("svb")
      .then((d) => { if (alive) setData(d); })
      .catch((e: unknown) => { if (alive) setError(e instanceof Error ? e.message : "Could not load the replay."); });
    return () => { alive = false; };
  }, []);

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:py-10">
      {error ? (
        <Alert>{error}</Alert>
      ) : data ? (
        <ReplayView data={data} lang={lang} />
      ) : (
        <Loader label={lang === "bn" ? "লোড হচ্ছে…" : "Loading the replay…"} />
      )}
    </main>
  );
}