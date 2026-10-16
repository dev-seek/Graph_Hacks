"use client";

import { CentreDashboard } from "@/components/CentreDashboard";
import { ButtonLink, Loading, Notice } from "@/components/ui";
import { useLoad } from "@/components/Journey";
import type { Schemas } from "@/lib/api";

export default function Centre() {
  const load = useLoad<Schemas["CentreOverview"]>("/centre/overview", null);
  return (
    <div className="max-w-4xl space-y-6">
      <h1 className="text-3xl">Centre brain</h1>
      <p className="text-muted">For clinic staff. Illustrative data.</p>
      {load.data ? (
        <CentreDashboard overview={load.data} />
      ) : load.loading ? (
        <Loading what="the centre" />
      ) : (
        <Notice title="The centre dashboard isn't switched on yet">
          <p>
            The shared case memory is not loaded in this setup, so there is nothing to show. Open the example families or the help page instead.
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
