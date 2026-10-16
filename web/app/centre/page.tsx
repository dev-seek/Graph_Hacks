"use client";

import { ButtonLink, Notice } from "@/components/ui";
import { useLoad } from "@/components/Journey";

type Overview = { cases: number; resolved: number; clinicians: number; protocols: number; kb_version: string };

export default function Centre() {
  const load = useLoad<Overview>("/centre/overview", null);
  return (
    <div className="max-w-[65ch] space-y-6">
      <h1 className="text-3xl">Centre brain</h1>
      {load.data ? (
        <Notice title="Centre overview">
          <p>
            {load.data.cases} cases · {load.data.resolved} resolved · {load.data.clinicians} clinicians ·{" "}
            {load.data.protocols} protocols (knowledge base {load.data.kb_version}).
          </p>
        </Notice>
      ) : (
        <Notice title={load.loading ? "Loading the centre" : "The centre dashboard isn't switched on yet"}>
          <p>
            {load.loading
              ? "One moment."
              : "The shared case memory is still being set up in this build, so there's nothing to show here yet. You can open the example families or the help page in the meantime."}
          </p>
          <div className="mt-3 flex flex-wrap gap-3">
            <ButtonLink href="/demo">Example families</ButtonLink>
            <ButtonLink href="/help" tone="secondary">
              Help
            </ButtonLink>
          </div>
        </Notice>
      )}
    </div>
  );
}
