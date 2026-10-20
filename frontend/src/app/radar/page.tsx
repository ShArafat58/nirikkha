"use client";

import { useEffect, useState } from "react";

import { useApp } from "../../components/providers";
import { RadarView } from "../../components/radar/radar-view";
import { useSession } from "../../components/session";
import { Alert } from "../../components/ui";
import { getRadar, type RadarData } from "../../lib/radar";

export default function RadarPage() {
  const app = useApp();
  const { signedIn } = useSession();
  const lang = (app as unknown as { lang?: string }).lang === "bn" ? "bn" : "en";
  const [data, setData] = useState<RadarData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    getRadar()
      .then((d) => { if (alive) setData(d); })
      .catch((e: unknown) => { if (alive) setError(e instanceof Error ? e.message : "Could not load the Radar."); });
    return () => { alive = false; };
  }, []);

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:py-10">
      {error ? <Alert>{error}</Alert>
        : data ? <RadarView data={data} lang={lang} signedIn={Boolean(signedIn)} />
        : <p className="py-20 text-center opacity-70">{lang === "bn" ? "লোড হচ্ছে…" : "Loading the Radar…"}</p>}
    </main>
  );
}