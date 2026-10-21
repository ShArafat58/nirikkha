// Relationship graph: types and API call.
import { API_URL, USE_MOCK } from "./api";

export type GraphKind = "company" | "person" | "committee" | "organization" | "party";
export type GraphNode = { id: string; label: string; kind: GraphKind; roles: string[]; title?: string | null; shared?: number };
export type GraphEdge = { source: string; target: string; type: string; page?: number | null; quote: string; amount?: string | null };
export type GraphData = {
  cik: string; company: string; accession: string; accessions: string[];
  nodes: GraphNode[]; edges: GraphEdge[]; counts: Record<string, number>; mock?: boolean;
};

export async function getGraph(cik: string, accession?: string): Promise<GraphData> {
  if (USE_MOCK) return { ...MOCK_GRAPH, mock: true };
  const q = accession ? `?accession=${encodeURIComponent(accession)}` : "";
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/graph/${encodeURIComponent(cik)}${q}`, { cache: "no-store" });
  } catch {
    return { ...MOCK_GRAPH, mock: true };
  }
  if (!res.ok) {
    let message = `The server returned an error (${res.status}).`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") message = body.detail;
    } catch { /* keep generic */ }
    throw new Error(message);
  }
  return (await res.json()) as GraphData;
}

export const MOCK_GRAPH: GraphData = {
  cik: "0000000001", company: "Example Co", accession: "mock", accessions: ["mock"],
  counts: { company: 1, person: 3, committee: 1, organization: 1, interlocks: 1 },
  nodes: [
    { id: "c:1", label: "Example Co", kind: "company", roles: [] },
    { id: "p:a", label: "Director A", kind: "person", roles: ["director"] },
    { id: "p:b", label: "Officer B", kind: "person", roles: ["officer", "director"], title: "Chief Executive Officer" },
    { id: "p:c", label: "Director C", kind: "person", roles: ["director"] },
    { id: "k:1", label: "Audit Committee", kind: "committee", roles: [] },
    { id: "o:1", label: "Shared Org", kind: "organization", roles: [], shared: 2 },
  ],
  edges: [
    { source: "p:a", target: "c:1", type: "director", quote: "Sample" },
    { source: "p:b", target: "c:1", type: "officer", quote: "Sample" },
    { source: "p:c", target: "c:1", type: "director", quote: "Sample" },
    { source: "k:1", target: "c:1", type: "committee_of", quote: "" },
    { source: "p:a", target: "k:1", type: "chair", quote: "Sample" },
    { source: "p:a", target: "o:1", type: "board_seat", quote: "Sample" },
    { source: "p:b", target: "o:1", type: "employed_by", quote: "Sample" },
  ],
};