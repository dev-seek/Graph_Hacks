"use client";

import { use } from "react";
import { Loaded, WithToken, useLoad } from "@/components/Journey";
import { Button, ButtonLink, Card } from "@/components/ui";
import { type Schemas } from "@/lib/api";

type Entry = Schemas["QueryLogEntry"];

function View({ id, token }: { id: string; token: string }) {
  const load = useLoad<Entry[]>(`/debug/queries?family_id=${id}`, token);
  return (
    <div className="max-w-[80ch] space-y-6">
      <h1 className="text-3xl">Behind the scenes: FalkorDB inspector (live)</h1>
      <p className="rounded-xl border border-border bg-card p-3 text-sm">
        This page is for judges and developers. It shows the technical steps FalkorDB ran for this example family. It is not medical
        information and says nothing about a diagnosis. Anything that could identify a person is hidden and shown as
        &quot;&lt;redacted&gt;&quot;. Answer a round on your journey page, then press Refresh to see new steps.
      </p>
      <Loaded load={load} what="the query log">
        {(entries) => {
          const total = entries.reduce((a, q) => a + q.ms, 0);
          return (
            <Card aria-labelledby="li-q">
              <h2 id="li-q" className="text-lg">
                Queries so far
              </h2>
              <p className="text-sm text-muted">
                {entries.length} queries from the query registry · {total.toFixed(1)} ms total ·{" "}
                {entries.reduce((a, q) => a + q.rows, 0)} rows returned
              </p>
              <ul className="mt-2 space-y-2">
                {entries.map((q, i) => (
                  <li key={`${q.name}-${i}`}>
                    <details>
                      <summary className="min-h-11 cursor-pointer py-2">
                        <span className="font-mono text-sm font-bold">{q.name}</span>{" "}
                        <span className="text-sm text-muted">
                          {q.rows} rows · {q.ms} ms
                        </span>
                      </summary>
                      <pre tabIndex={0} aria-label={`Cypher for ${q.name}`} className="overflow-x-auto rounded-lg bg-night p-3 text-xs text-card">{q.cypher}</pre>
                      <p className="mt-1 text-xs text-muted">
                        Parameters: <code className="break-all">{JSON.stringify(q.params)}</code>
                      </p>
                    </details>
                  </li>
                ))}
                {entries.length === 0 ? <li className="text-muted">No queries yet. Answer a round, then refresh.</li> : null}
              </ul>
            </Card>
          );
        }}
      </Loaded>
      <div className="flex flex-wrap gap-3">
        <Button onClick={load.reload}>Refresh</Button>
        <ButtonLink href={`/j/${id}`} tone="secondary">
          Back to your journey
        </ButtonLink>
      </div>
    </div>
  );
}

export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <WithToken id={id}>{(token) => <View id={id} token={token} />}</WithToken>;
}
