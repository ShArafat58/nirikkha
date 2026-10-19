"use client";

import { useEffect, useState } from "react";
import { API_URL, USE_MOCK, getHealth, type Health } from "@/lib/api";

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Unknown error"));
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-slate-100">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-8 shadow-xl">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/brand/logo.svg" alt="Nirikkha logo" width={232} height={77} className="h-auto w-56" />
        <p className="mt-3 text-slate-400">Trust less, Verify more.</p>

        <div className="mt-6 space-y-2 text-sm">
          <p className="text-slate-400">
            Backend: <code className="text-slate-200">{API_URL}</code>
            {USE_MOCK && <span className="ml-2 rounded bg-amber-500/20 px-2 py-0.5 text-amber-300">mock mode</span>}
          </p>

          {!health && !error && (
            <p className="text-amber-400">Checking backend... (first call can take ~50 s while the free server wakes up)</p>
          )}

          {error && <p className="text-red-400">Backend unreachable: {error}</p>}

          {health && (
            <div className="rounded-lg border border-slate-800 p-4">
              <p>
                Status: <span className="font-semibold text-emerald-400">{health.status}</span>
              </p>
              <p>Version: {health.version}</p>
              <p>Environment: {health.env}</p>
              <ul className="mt-2 space-y-1">
                {Object.entries(health.providers_configured).map(([name, ok]) => (
                  <li key={name}>
                    {ok ? "OK" : "MISSING"} - {name}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}