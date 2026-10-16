import type { ClinicianView, DemoStep } from "./api";

export type QueryEntry = { name: string; cypher: string; params: Record<string, unknown>; rows: number; ms: number };
export type GateData = { state: string; rule: string; inputs: Record<string, number | boolean> };
type Item = { id: string; plain_label: string; quote: string; status: "present" | "absent" };
type Q = { qid: string; text: string; why: string; how_to_check: string };
type NextState = { phase?: string; banner?: string | null; next_step?: { label: string } };

const arr = <T>(v: unknown): T[] => (Array.isArray(v) ? (v as T[]) : []);
const obj = <T>(v: unknown): T | null => (v && typeof v === "object" ? (v as T) : null);

/** Everything below is read from the recorded payload; nothing is invented. */
export function parentView(step: DemoStep) {
  const p: Record<string, unknown> = step.payload ?? {};
  const state = obj<NextState>(p.state) ?? (p.next_step ? (p as NextState) : null) ?? obj<NextState>(p.next);
  return {
    items: arr<Item>(p.extraction_to_confirm),
    questions: arr<Q>(p.questions),
    roundNo: typeof p.round_no === "number" ? p.round_no : null,
    answers: arr<{ qid: string; value: string }>(p.answers),
    state,
    pack: obj<{ summary: string; findings: { plain_label: string; status: string }[] }>(p.pack),
    safetyLevel: obj<{ level: string }>(p.safety)?.level ?? null,
  };
}

/** Clinician-side and engine-side data: only ever shown in the clinician pane or the inspector. */
export function engineView(step: DemoStep) {
  const p: Record<string, unknown> = step.payload ?? {};
  const clin = obj<ClinicianView>(p.clinician);
  const gate = obj<GateData>(p.gate) ?? (clin ? (clin.gate as GateData) : null);
  return {
    queries: arr<QueryEntry>(p.queries),
    gate,
    clinician: clin,
    phenopacket: obj<Record<string, unknown>>(p.phenopacket),
  };
}

export type GNode = { id: string; label: string; kind: "family" | "finding" | "round" | "gate" };
export type GEdge = { source: string; target: string; label: string };

/** Evidence subgraph up to step n, built only from what the recording contains. */
export function evidenceGraph(steps: DemoStep[], upTo: number): { nodes: GNode[]; edges: GEdge[] } {
  const nodes: GNode[] = [{ id: "family", label: "Family", kind: "family" }];
  const edges: GEdge[] = [];
  const seen = new Set<string>(["family"]);
  const add = (n: GNode, e: GEdge) => {
    if (seen.has(n.id)) return;
    seen.add(n.id);
    nodes.push(n);
    edges.push(e);
  };
  for (const s of steps.slice(0, upTo + 1)) {
    const v = parentView(s);
    if (s.screen === "confirm" || s.screen === "letter")
      for (const i of v.items)
        add(
          { id: `f-${i.id}`, label: i.plain_label.slice(0, 28), kind: "finding" },
          { source: "family", target: `f-${i.id}`, label: i.status === "absent" ? "EXCLUDES" : "HAS_FINDING" },
        );
    if (s.screen === "round" && v.roundNo != null)
      add(
        { id: `r-${v.roundNo}`, label: `Round ${v.roundNo}`, kind: "round" },
        { source: "family", target: `r-${v.roundNo}`, label: "HAS_ROUND" },
      );
    const g = engineView(s).gate;
    if (g) add({ id: `g-${s.n}`, label: g.state, kind: "gate" }, { source: "family", target: `g-${s.n}`, label: "GATE" });
  }
  return { nodes, edges };
}
