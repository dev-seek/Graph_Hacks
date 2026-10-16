"use client";

import { useMemo } from "react";
import { EvidenceGraph } from "./EvidenceGraph";
import { Card } from "./ui";
import type { DemoStep } from "@/lib/api";
import { engineView, evidenceGraph } from "@/lib/demo";

const FALKORDB_BROWSER = "http://localhost:3000";

export function Inspector({ steps, index }: { steps: DemoStep[]; index: number }) {
  const step = steps[index];
  const graph = useMemo(() => evidenceGraph(steps, index), [steps, index]);
  if (!step) return null;
  const e = engineView(step);
  const total = e.queries.reduce((a, q) => a + q.ms, 0);
  return (
    <aside aria-label="FalkorDB inspector, recorded run" className="space-y-4">
      <p className="rounded-xl border border-border bg-card p-3 text-sm">
        Recorded run: these are the graph queries FalkorDB actually ran when this example family was recorded,
        replayed here without a model or network. Open a real journey to see new queries.
      </p>
      <Card aria-labelledby="insp-q">
        <h2 id="insp-q" className="text-lg">
          Graph queries this step
        </h2>
        <p className="text-sm text-muted">
          {e.queries.length} queries from the query registry · {total.toFixed(1)} ms total ·{" "}
          {e.queries.reduce((a, q) => a + q.rows, 0)} rows returned
        </p>
        <ul className="mt-2 space-y-2">
          {e.queries.map((q, i) => (
            <li key={`${q.name}-${i}`}>
              <details>
                <summary className="min-h-11 cursor-pointer py-2">
                  <span className="font-mono text-sm font-bold">{q.name}</span>{" "}
                  <span className="text-sm text-muted">
                    {q.rows} rows · {q.ms} ms
                  </span>
                </summary>
                <pre className="overflow-x-auto rounded-lg bg-night p-3 text-xs text-card">{q.cypher}</pre>
                <p className="mt-1 text-xs text-muted">
                  Parameters: <code>{JSON.stringify(q.params)}</code>
                </p>
              </details>
            </li>
          ))}
          {e.queries.length === 0 ? <li className="text-muted">No graph queries in this step.</li> : null}
        </ul>
      </Card>
      {e.gate ? (
        <Card aria-labelledby="insp-g">
          <h2 id="insp-g" className="text-lg">
            Gate decision: {e.gate.state}
          </h2>
          <p className="text-sm">{e.gate.rule}</p>
          <dl className="mt-2 grid grid-cols-[1fr_auto] gap-x-4 text-sm">
            {Object.entries(e.gate.inputs).map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="text-muted">{k}</dt>
                <dd className="font-mono">{typeof v === "number" ? Number(v.toFixed(3)) : String(v)}</dd>
              </div>
            ))}
          </dl>
        </Card>
      ) : null}
      <Card aria-labelledby="insp-e">
        <h2 id="insp-e" className="text-lg">
          Evidence graph
        </h2>
        <EvidenceGraph nodes={graph.nodes} edges={graph.edges} />
        <p className="mt-2 text-sm">
          <a href={FALKORDB_BROWSER} target="_blank" rel="noreferrer">
            Open FalkorDB Browser (local setup, port 3000)
          </a>
        </p>
      </Card>
    </aside>
  );
}
