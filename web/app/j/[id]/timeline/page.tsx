"use client";

import { use } from "react";
import { Loaded, WithToken, useLoad } from "@/components/Journey";
import { ButtonLink, Card } from "@/components/ui";
import { fam, type Timeline } from "@/lib/api";

const SOURCE: Record<string, string> = {
  parent_story: "Your story",
  parent_answer: "Your answer",
  doctor_exam: "Doctor's exam",
  lab_or_test: "Test result",
};

function View({ id, token }: { id: string; token: string }) {
  const load = useLoad<Timeline>(`${fam(id)}/timeline`, token);
  return (
    <div className="max-w-[65ch] space-y-6">
      <h1 className="text-3xl">Everything recorded</h1>
      <Loaded load={load} what="your timeline">
        {(t) => (
          <>
            <Card aria-labelledby="t-find">
              <h2 id="t-find" className="text-xl">
                What you&apos;ve confirmed
              </h2>
              {t.findings.length === 0 ? (
                <p className="mt-2 text-muted">Nothing yet. Your confirmed items will appear here.</p>
              ) : (
                <ul className="mt-2 space-y-2">
                  {t.findings.map((f) => (
                    <li key={f.id} className="flex flex-wrap items-center gap-2">
                      <span>
                        {f.status === "absent" ? "Not seen: " : ""}
                        {f.plain_label}
                      </span>
                      <span className="rounded-full border border-border px-2 text-sm text-muted">
                        {SOURCE[f.source] ?? f.source}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <Card aria-labelledby="t-ev">
              <h2 id="t-ev" className="text-xl">
                By date
              </h2>
              {t.events.length === 0 ? (
                <p className="mt-2 text-muted">Nothing has happened yet. Dates will appear here.</p>
              ) : null}
              <ol className="mt-2 space-y-2">
                {t.events.map((e, i) => (
                  <li key={`${e.at}-${i}`}>
                    <time dateTime={e.at} className="text-muted">
                      {new Date(e.at).toLocaleDateString()}
                    </time>{" "}
                    {e.label}
                  </li>
                ))}
              </ol>
            </Card>
          </>
        )}
      </Loaded>
      <ButtonLink href={`/j/${id}`} tone="secondary">
        Back to your journey
      </ButtonLink>
    </div>
  );
}

export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <WithToken id={id}>{(token) => <View id={id} token={token} />}</WithToken>;
}
