"use client";

import { useEffect, useState } from "react";

import { GraphView } from "../../components/graph/graph-view";
import { useApp } from "../../components/providers";
import { Alert } from "../../components/ui";
import { getCompanies, type Company } from "../../lib/api";
import { getGraph, type GraphData } from "../../lib/graph";
import { Loader } from "../../components/loader";

const DEFAULT_CIK = "0000719739";

export default function GraphPage() {
  const app = useApp();
  const lang = (app as unknown as { lang?: string }).lang === "bn" ? "bn" : "en";
  const theme = (app as unknown as { theme?: string }).theme === "paper" ? "paper" : "dark";
  const [companies, setCompanies] = useState<Company[]>([]);
  const [cik, setCik] = useState(DEFAULT_CIK);
  const [accession, setAccession] = useState<string | undefined>();
  const [data, setData] = useState<GraphData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => { getCompanies().then(setCompanies).catch(() => setCompanies([])); }, []);

  useEffect(() => {
    let alive = true;
    setLoading(true); setError("");
    getGraph(cik, accession)
      .then((d) => { if (alive) setData(d); })
      .catch((e: unknown) => { if (alive) { setData(null); setError(e instanceof Error ? e.message : "Could not load the graph."); } })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [cik, accession]);

  const bn = lang === "bn";
  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:py-10">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-500">{bn ? "সম্পর্কের জাল" : "Relationship graph"}</p>
      <h1 className="mt-2 text-2xl font-bold sm:text-3xl">
        {bn ? "কে কোথায় যুক্ত: পরিচালক, কর্মকর্তা, কমিটি আর বাইরের প্রতিষ্ঠান" : "Who is connected to what: directors, officers, committees and outside organizations"}
      </h1>
      <p className="mt-2 max-w-3xl text-sm opacity-70">
        {bn ? "প্রতিটি সম্পর্ক প্রক্সি স্টেটমেন্ট থেকে বের করে যাচাই করা হয়েছে; যাচাই না হওয়া সম্পর্ক দেখানো হয় না।"
            : "Every relationship is extracted from the proxy statement and verified against its quote; unverified ones are not shown."}
      </p>

      <div className="mt-6 flex flex-wrap gap-3">
        <select value={cik} onChange={(e) => { setCik(e.target.value); setAccession(undefined); }}
                className="rounded-lg border border-slate-500/30 bg-transparent px-3 py-2 text-sm">
          {(companies.length ? companies : [{ cik: DEFAULT_CIK, company: "SVB FINANCIAL GROUP" } as Company]).map((c) => (
            <option key={c.cik} value={c.cik}>{c.company}</option>
          ))}
        </select>
        {data && data.accessions.length > 1 && (
          <select value={data.accession} onChange={(e) => setAccession(e.target.value)}
                  className="rounded-lg border border-slate-500/30 bg-transparent px-3 py-2 text-sm">
            {data.accessions.map((a) => <option key={a} value={a}>{bn ? "প্রক্সি" : "Proxy"} {a}</option>)}
          </select>
        )}
      </div>

      <div className="mt-6">
        {error ? <Alert>{error}</Alert>
          : loading || !data ? <Loader label={bn ? "লোড হচ্ছে…" : "Loading the graph…"} />
          : <GraphView data={data} lang={lang} theme={theme} />}
      </div>
    </main>
  );
}