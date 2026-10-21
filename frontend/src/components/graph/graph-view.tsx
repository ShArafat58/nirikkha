"use client";

import { useMemo, useState } from "react";

import type { GraphData, GraphEdge, GraphNode } from "../../lib/graph";

export type GraphLang = "en" | "bn";

const TXT = {
  en: {
    people: "people", committees: "committees", orgs: "outside organizations", interlocks: "shared outside organizations",
    hint: "Click any dot in the graph. Its relationships and the exact passage from the filing appear here.",
    director: "Director", officer: "Officer", board_chair: "Board chair", member: "Committee member", chair: "Committee chair",
    board_seat: "Outside board seat", employed_by: "Outside employment", outside_member: "Outside membership",
    related_transaction: "Related-party transaction", committee_of: "Committee of",
    company: "Company", person: "Person", committee: "Committee", organization: "Organization", party: "Related party",
    sharedBy: "shared by {n} people", page: "p.", clear: "Clear selection",
    caution: "A relationship is a question to check, not evidence of misconduct.", mock: "Mock data: the backend is not reachable.",
    legend: ["Company", "Director", "Officer", "Director and officer", "Committee", "Outside organization", "Shared organization"],
  },
  bn: {
    people: "জন ব্যক্তি", committees: "টি কমিটি", orgs: "টি বাইরের প্রতিষ্ঠান", interlocks: "টি যৌথ বাইরের প্রতিষ্ঠান",
    hint: "গ্রাফের যেকোনো বিন্দুতে চাপ দিন। তার সব সম্পর্ক আর ফাইলিংয়ের মূল অনুচ্ছেদ এখানে দেখাবে।",
    director: "পরিচালক", officer: "কর্মকর্তা", board_chair: "বোর্ড চেয়ার", member: "কমিটির সদস্য", chair: "কমিটির চেয়ার",
    board_seat: "বাইরের বোর্ড পদ", employed_by: "বাইরের চাকরি", outside_member: "বাইরের সদস্যপদ",
    related_transaction: "সংশ্লিষ্ট পক্ষের লেনদেন", committee_of: "যে কোম্পানির কমিটি",
    company: "কোম্পানি", person: "ব্যক্তি", committee: "কমিটি", organization: "প্রতিষ্ঠান", party: "সংশ্লিষ্ট পক্ষ",
    sharedBy: "{n} জনের সাথে যুক্ত", page: "পৃ.", clear: "বাছাই মুছুন",
    caution: "সম্পর্ক মানে যাচাই করার প্রশ্ন, অসদাচরণের প্রমাণ নয়।", mock: "নমুনা ডেটা: ব্যাকএন্ড পাওয়া যাচ্ছে না।",
    legend: ["কোম্পানি", "পরিচালক", "কর্মকর্তা", "পরিচালক ও কর্মকর্তা", "কমিটি", "বাইরের প্রতিষ্ঠান", "যৌথ প্রতিষ্ঠান"],
  },
};
type T = (typeof TXT)["en"];

const W = 1500;
const H = 1000;
const CX = W / 2;
const CY = H / 2;
const RINGS = { committee: [210, 150], party: [290, 205], person: [470, 310], organization: [690, 445] } as const;
const COLOR = {
  company: "#f5b83d", director: "#38bdf8", officer: "#f59e0b", both: "#a78bfa",
  committee: "#10b981", organization: "#64748b", shared: "#f43f5e", party: "#fb7185",
};
const INK = {
  dark: { edge: "#94a3b8", edgeOpacity: 0.18, faded: 0.04, on: "#f1f5f9", ring: 0.06, selected: "#ffffff" },
  paper: { edge: "#334155", edgeOpacity: 0.3, faded: 0.06, on: "#0f172a", ring: 0.12, selected: "#0f172a" },
};

function personColor(n: GraphNode) {
  const d = n.roles.includes("director") || n.roles.includes("board_chair");
  const o = n.roles.includes("officer");
  return d && o ? COLOR.both : o ? COLOR.officer : COLOR.director;
}

function nodeColor(n: GraphNode) {
  if (n.kind === "company") return COLOR.company;
  if (n.kind === "person") return personColor(n);
  if (n.kind === "committee") return COLOR.committee;
  if (n.kind === "party") return COLOR.party;
  return (n.shared ?? 0) >= 2 ? COLOR.shared : COLOR.organization;
}

type P = { x: number; y: number; a: number };

function layout(data: GraphData) {
  const pos = new Map<string, P>();
  const ring = (ids: string[], [rx, ry]: readonly [number, number], offset = 0) =>
    ids.forEach((id, i) => {
      const a = (i / Math.max(ids.length, 1)) * Math.PI * 2 - Math.PI / 2 + offset;
      pos.set(id, { x: CX + rx * Math.cos(a), y: CY + ry * Math.sin(a), a });
    });
  const by = (k: string) => data.nodes.filter((n) => n.kind === k);
  const company = by("company")[0];
  if (company) pos.set(company.id, { x: CX, y: CY, a: 0 });
  const people = by("person").sort((a, b) => personColor(a).localeCompare(personColor(b)) || a.label.localeCompare(b.label));
  ring(people.map((n) => n.id), RINGS.person);
  ring(by("committee").map((n) => n.id), RINGS.committee, Math.PI / 8);
  ring(by("party").map((n) => n.id), RINGS.party, Math.PI / 5);
  const orgs = by("organization").map((n) => {
    const angles = data.edges.filter((e) => e.target === n.id).map((e) => pos.get(e.source)?.a ?? 0);
    const avg = angles.length
      ? Math.atan2(angles.reduce((s, a) => s + Math.sin(a), 0), angles.reduce((s, a) => s + Math.cos(a), 0)) : 0;
    return { id: n.id, avg };
  }).sort((a, b) => a.avg - b.avg);
  ring(orgs.map((o) => o.id), RINGS.organization, orgs.length ? orgs[0].avg + Math.PI / 2 : 0);
  return pos;
}

function RadialLabel({ p, r, text, size, opacity }: { p: P; r: number; text: string; size: number; opacity: number }) {
  // Text points away from the centre along the radius, so neighbours never overlap.
  const dx = Math.cos(p.a), dy = Math.sin(p.a);
  const x = p.x + dx * (r + 6), y = p.y + dy * (r + 6);
  let deg = (p.a * 180) / Math.PI;
  const flip = dx < 0;
  if (flip) deg += 180;
  return (
    <text x={x} y={y} dy={size * 0.35} fontSize={size} fill="currentColor" opacity={opacity}
          textAnchor={flip ? "end" : "start"} transform={`rotate(${deg.toFixed(1)} ${x.toFixed(1)} ${y.toFixed(1)})`}>
      {text}
    </text>
  );
}

export function GraphView({ data, lang, theme = "dark" }: { data: GraphData; lang: GraphLang; theme?: "dark" | "paper" }) {
  const t: T = TXT[lang];
  const ink = INK[theme];
  const pos = useMemo(() => layout(data), [data]);
  const byId = useMemo(() => new Map(data.nodes.map((n) => [n.id, n])), [data]);
  const [selected, setSelected] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const focus = hover ?? selected;
  const linked = useMemo(() => {
    const s = new Set<string>();
    if (focus) data.edges.forEach((e) => { if (e.source === focus) s.add(e.target); if (e.target === focus) s.add(e.source); });
    return s;
  }, [focus, data.edges]);
  const sel = selected ? byId.get(selected) : undefined;
  const selEdges: GraphEdge[] = selected
    ? data.edges.filter((e) => (e.source === selected || e.target === selected) && e.type !== "committee_of") : [];
  const num = (v: number) => (lang === "bn" ? String(v).replace(/\d/g, (d) => "০১২৩৪৫৬৭৮৯"[Number(d)]) : String(v));
  const label = (k: string) => (t as unknown as Record<string, string>)[k] ?? k;
  const short = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

  return (
    <div className="space-y-4">
      {data.mock && <div className="rounded-xl border border-amber-500/50 bg-amber-500/10 px-4 py-2.5 text-sm text-amber-500">{t.mock}</div>}
      <div className="flex flex-wrap gap-2 text-xs">
        {[["person", t.people], ["committee", t.committees], ["organization", t.orgs], ["interlocks", t.interlocks]].map(([k, l]) => (
          <span key={k} className={`rounded-full border px-3 py-1 ${k === "interlocks" && (data.counts.interlocks ?? 0) > 0 ? "border-rose-500/50 text-rose-500" : "border-slate-500/30"}`}>
            <b>{num(data.counts[k] ?? 0)}</b> {l}
          </span>
        ))}
      </div>

      <div className="rounded-2xl border border-slate-500/20 bg-slate-500/[0.04] p-2">
        <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Relationship graph"
             onClick={(e) => { if (e.target === e.currentTarget) setSelected(null); }}>
          {(Object.values(RINGS) as readonly (readonly [number, number])[]).map(([rx, ry]) => (
            <ellipse key={rx} cx={CX} cy={CY} rx={rx} ry={ry} fill="none" stroke={ink.edge} strokeOpacity={ink.ring} />
          ))}
          {data.edges.map((e, i) => {
            const a = pos.get(e.source); const b = pos.get(e.target);
            if (!a || !b) return null;
            const on = focus && (e.source === focus || e.target === focus);
            return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
              stroke={e.type === "chair" ? COLOR.committee : on ? ink.on : ink.edge}
              strokeOpacity={focus ? (on ? 0.9 : ink.faded) : ink.edgeOpacity} strokeWidth={on ? 2.2 : 1.1} />;
          })}
          {data.nodes.map((n) => {
            const p = pos.get(n.id);
            if (!p) return null;
            const dim = focus && n.id !== focus && !linked.has(n.id);
            const shared = (n.shared ?? 0) >= 2;
            const r = n.kind === "company" ? 40 : n.kind === "person" ? 12 : n.kind === "committee" ? 14 : shared ? 10 : 6;
            const right = Math.cos(p.a) >= 0;
            const showOrg = n.kind === "organization" && (shared || n.id === focus || linked.has(n.id));
            return (
              <g key={n.id} opacity={dim ? 0.12 : 1} className="cursor-pointer"
                 onClick={() => setSelected(n.id === selected ? null : n.id)}
                 onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)}>
                <title>{n.label}</title>
                {n.kind === "committee"
                  ? <rect x={p.x - r} y={p.y - r} width={r * 2} height={r * 2} rx={4} fill={nodeColor(n)}
                          stroke={n.id === selected ? ink.selected : "none"} strokeWidth={3} />
                  : <circle cx={p.x} cy={p.y} r={r} fill={nodeColor(n)} stroke={n.id === selected ? ink.selected : "none"} strokeWidth={3} />}
                {n.kind === "company" ? (
                  <text x={p.x} y={p.y + 70} textAnchor="middle" fontSize={26} fontWeight={700} fill="currentColor">{n.label}</text>
                ) : n.kind === "organization" ? (
                  showOrg ? <RadialLabel p={p} r={r} text={short(n.label, 38)} size={14} opacity={0.9} /> : null
                ) : (
                  <text x={p.x + (right ? r + 8 : -(r + 8))} y={p.y + 5} textAnchor={right ? "start" : "end"}
                        fontSize={n.kind === "person" ? 17 : 13} fill="currentColor" opacity={n.kind === "person" ? 0.95 : 0.8}>
                    {short(n.label, n.kind === "person" ? 30 : 34)}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
        <div className="flex flex-wrap gap-x-4 gap-y-2 px-3 pb-2 text-xs opacity-80">
          {[COLOR.company, COLOR.director, COLOR.officer, COLOR.both, COLOR.committee, COLOR.organization, COLOR.shared].map((c, i) => (
            <span key={c} className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full" style={{ background: c }} />{t.legend[i]}</span>
          ))}
        </div>
      </div>

      <section className="rounded-2xl border border-slate-500/20 bg-slate-500/[0.04] p-5 sm:p-6">
        {!sel ? <p className="text-sm opacity-70">{t.hint}</p> : (
          <div className="space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider opacity-60">{label(sel.kind)}</p>
                <h3 className="text-xl font-semibold">{sel.label}</h3>
                {sel.title && <p className="text-sm opacity-80">{sel.title}</p>}
                {sel.roles.length > 0 && <p className="text-sm opacity-80">{sel.roles.map(label).join(" · ")}</p>}
                {(sel.shared ?? 0) >= 2 && <p className="text-sm text-rose-500">{t.sharedBy.replace("{n}", num(sel.shared ?? 0))}</p>}
              </div>
              <button type="button" onClick={() => setSelected(null)} className="rounded-lg border border-slate-500/30 px-3 py-1.5 text-xs opacity-80 hover:opacity-100">
                {t.clear}
              </button>
            </div>
            <ul className="grid gap-2 md:grid-cols-2">
              {selEdges.map((e, i) => {
                const other = byId.get(e.source === sel.id ? e.target : e.source);
                return (
                  <li key={i} className="rounded-lg bg-slate-500/[0.07] p-3 text-sm">
                    <p className="font-medium">{label(e.type)} · {other?.label}</p>
                    {e.amount && <p className="text-xs opacity-80">{e.amount}</p>}
                    {e.quote && <p className="mt-1 text-xs italic opacity-75" lang="en">“{e.quote}”{e.page ? ` (${t.page}${num(e.page)})` : ""}</p>}
                  </li>
                );
              })}
            </ul>
          </div>
        )}
        <p className="mt-4 border-t border-slate-500/15 pt-3 text-xs opacity-60">{t.caution}</p>
      </section>
    </div>
  );
}