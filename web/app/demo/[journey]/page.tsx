"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, use, useState } from "react";
import { ClinicianBody } from "@/components/ClinicianBody";
import { Inspector } from "@/components/Inspector";
import { Loaded, useLoad } from "@/components/Journey";
import { Button, ButtonLink, Card, Notice } from "@/components/ui";
import type { DemoStep } from "@/lib/api";
import { engineView, parentView } from "@/lib/demo";
import { DEMO_BANNER, NO_ESCALATION, PARENT_DISCLAIMER, URGENT } from "@/copy";

function StepBody({ step }: { step: DemoStep }) {
  const v = parentView(step);
  const label = v.state?.next_step?.label;
  const urgent = v.state?.phase === "urgent";
  return (
    <div className="space-y-4" data-view="parent">
      {urgent ? (
        <Notice tone="urgent" title="Please get urgent help now">
          <p>{v.state?.banner ?? URGENT}</p>
        </Notice>
      ) : null}
      {v.items.length > 0 ? (
        <Card aria-labelledby="d-items">
          <h2 id="d-items" className="text-lg">
            What we picked up
          </h2>
          <ul className="mt-2 space-y-2">
            {v.items.map((i) => (
              <li key={i.id}>
                <span className="font-bold">{i.plain_label}</span>
                <span className="block text-sm text-muted">From the story: &ldquo;{i.quote}&rdquo;</span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
      {v.questions.length > 0 ? (
        <Card aria-labelledby="d-q">
          <h2 id="d-q" className="text-lg">
            Round {v.roundNo}
          </h2>
          <ol className="mt-2 list-decimal space-y-3 pl-5">
            {v.questions.map((q) => (
              <li key={q.qid}>
                <span className="font-bold">{q.text}</span>
                <span className="block text-sm text-muted">Why we ask: {q.why}</span>
              </li>
            ))}
          </ol>
        </Card>
      ) : null}
      {v.answers.length > 0 ? (
        <Card aria-labelledby="d-a">
          <h2 id="d-a" className="text-lg">
            Their answers
          </h2>
          <p className="mt-2">
            {v.answers.filter((a) => a.value === "yes").length} yes ·{" "}
            {v.answers.filter((a) => a.value === "no").length} no ·{" "}
            {v.answers.filter((a) => a.value === "unsure").length} not sure
          </p>
        </Card>
      ) : null}
      {v.pack ? (
        <Card aria-labelledby="d-p">
          <h2 id="d-p" className="text-lg">
            The one-page summary
          </h2>
          <p className="mt-2">{v.pack.summary}</p>
        </Card>
      ) : null}
      {!urgent && label ? (
        <Notice title="What happens next">
          <p>{step.screen === "no_escalation" ? NO_ESCALATION : label}</p>
        </Notice>
      ) : null}
    </div>
  );
}

function Player({ journey }: { journey: string }) {
  const router = useRouter();
  const params = useSearchParams();
  const judge = params.get("judge") === "1";
  const load = useLoad<DemoStep[]>(`/demo/${journey}/steps`, null);
  const [i, setI] = useState(0);

  function toggleJudge() {
    router.replace(`/demo/${journey}${judge ? "" : "?judge=1"}`);
  }

  return (
    <Loaded load={load} what="this example">
      {(steps) => {
        const step = steps[Math.min(i, steps.length - 1)];
        if (!step) return null;
        const e = engineView(step);
        return (
          <div className="space-y-4">
            <Notice title={DEMO_BANNER}>
              <p>
                Step {i + 1} of {steps.length}.
              </p>
            </Notice>
            <div className="flex flex-wrap items-center gap-3">
              <Link href="/demo" className="min-h-11 content-center">
                All example families
              </Link>
              <Button tone="secondary" className="ml-auto" aria-pressed={judge} onClick={toggleJudge}>
                {judge ? "Hide" : "Show"} the FalkorDB inspector
              </Button>
            </div>
            <div className={judge ? "grid gap-6 lg:grid-cols-2" : ""}>
              <div className="space-y-4">
                <div aria-live="polite">
                  <h1 className="text-2xl">{step.caption}</h1>
                </div>
                <StepBody step={step} />
                {e.clinician ? (
                  <section aria-labelledby="demo-clin" className="rounded-2xl border-2 border-night p-4" data-view="clinician">
                    <h2 id="demo-clin" className="text-lg">
                      What the doctor sees (clinician view)
                    </h2>
                    <ClinicianBody view={e.clinician} id="demo" code="" phenopacket={e.phenopacket} />
                  </section>
                ) : null}
                <div className="flex flex-wrap gap-3">
                  <Button tone="secondary" onClick={() => setI(Math.max(0, i - 1))} disabled={i === 0}>
                    Back
                  </Button>
                  <Button onClick={() => setI(Math.min(steps.length - 1, i + 1))} disabled={i >= steps.length - 1}>
                    Next
                  </Button>
                  {i >= steps.length - 1 ? (
                    <ButtonLink href="/start" tone="secondary">
                      Start with your own story
                    </ButtonLink>
                  ) : null}
                </div>
                <p className="text-sm text-muted">{PARENT_DISCLAIMER}</p>
              </div>
              {judge ? <Inspector steps={steps} index={i} /> : null}
            </div>
          </div>
        );
      }}
    </Loaded>
  );
}

export default function Page({ params }: { params: Promise<{ journey: string }> }) {
  const { journey } = use(params);
  return (
    <Suspense fallback={<p role="status">Loading…</p>}>
      <Player journey={journey} />
    </Suspense>
  );
}
