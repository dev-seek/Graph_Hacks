"use client";

import { useState } from "react";
import { Download, Printer } from "lucide-react";
import { Button, Card, Notice } from "./ui";
import { call, friendly, type ClinicianView } from "@/lib/api";
import { CLINICIAN_DISCLAIMER } from "@/copy";

const STATE_TEXT: Record<string, string> = {
  URGENT: "Urgent: safety rule fired",
  REFERRAL_READY: "Referral ready",
  SEE_DOCTOR: "See a doctor",
  WATCH: "Watch",
  CONTINUE: "Continue gathering evidence",
};

export function ClinicianBody({
  view,
  id,
  code,
  phenopacket,
}: {
  view: ClinicianView;
  id: string;
  code: string;
  /** Recorded Phenopacket for demo steps (no server call). */
  phenopacket?: Record<string, unknown> | null;
}) {
  const [draft, setDraft] = useState(view.referral_draft ?? "");
  const [err, setErr] = useState<string | null>(null);
  const top = view.candidates[0]?.posterior || 1;

  async function download() {
    setErr(null);
    try {
      const out = {
        phenopacket:
          phenopacket ??
          (
            await call<{ phenopacket: unknown }>(`/clinician/${id}/phenopacket`, {
              clinicianCode: code,
            })
          ).phenopacket,
      };
      const blob = new Blob([JSON.stringify(out.phenopacket, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `phenopacket-${id}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      setErr(
        e instanceof Error && "status" in e && (e as { status: number }).status === 409
          ? "The Phenopacket is available once the pattern fits strongly enough for a referral. Keep gathering findings first."
          : friendly(e),
      );
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl">Clinician view</h1>
      <Notice title="Disclaimer">
        <p>{CLINICIAN_DISCLAIMER}</p>
      </Notice>
      <p className="text-muted">
        Child aged {view.child_age_months} months · KB {view.kb_version} · Gate:{" "}
        <strong>{STATE_TEXT[view.gate.state] ?? view.gate.state}</strong> ({view.gate.rule})
      </p>

      <Card aria-labelledby="c-find" className="overflow-x-auto" tabIndex={0}>
        <h2 id="c-find" className="text-xl">
          Findings
        </h2>
        <table className="mt-3 w-full min-w-[34rem] border-collapse text-left">
          <caption className="sr-only">Recorded findings with source</caption>
          <thead>
            <tr className="border-b border-border">
              <th scope="col" className="py-2 pr-3">Term</th>
              <th scope="col" className="py-2 pr-3">HPO ID</th>
              <th scope="col" className="py-2 pr-3">Status</th>
              <th scope="col" className="py-2">Source</th>
            </tr>
          </thead>
          <tbody>
            {view.findings.map((f) => (
              <tr key={f.term_id} className="border-b border-line align-top">
                <td className="py-2 pr-3">
                  {f.label}
                  {f.quote ? <span className="block text-sm text-muted">&ldquo;{f.quote}&rdquo;</span> : null}
                </td>
                <td className="py-2 pr-3 font-mono text-sm">{f.term_id}</td>
                <td className="py-2 pr-3">{f.status}</td>
                <td className="py-2">{f.source.replace("_", " ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <section aria-labelledby="c-cand">
        <h2 id="c-cand" className="text-xl">
          Candidate patterns (top {view.candidates.length})
        </h2>
        <details className="mt-1">
          <summary className="min-h-11 cursor-pointer py-2 underline underline-offset-4">
            How this ranking works
          </summary>
          <p className="max-w-[65ch]">
            Each recorded finding multiplies a pattern&apos;s support by a likelihood ratio: how much more
            often that finding appears in the pattern than in the others. Absent findings count
            against patterns that usually have them. Bars show support relative to the first
            candidate; they are not probabilities.
          </p>
        </details>
        <ol className="mt-3 space-y-4">
          {view.candidates.map((c) => (
            <li key={c.disease_id}>
              <Card>
                <h3 className="text-lg">
                  {c.rank}. {c.name}{" "}
                  <span className="font-mono text-sm font-normal text-muted">{c.disease_id}</span>
                </h3>
                <div
                  role="img"
                  aria-label={`Relative support: ${Math.round((c.posterior / top) * 100)} per cent of the first candidate`}
                  className="my-2 h-3 rounded-full bg-line"
                >
                  <div className="h-3 rounded-full bg-night" style={{ width: `${Math.max(4, (c.posterior / top) * 100)}%` }} />
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <h4 className="font-bold">Supports</h4>
                    <ul className="mt-1 space-y-2">
                      {c.supporting.slice(0, 3).map((s) => (
                        <li key={s.term_id}>
                          {s.label}
                          {(s.path ?? []).length > 0 ? (
                            <span className="block text-sm text-muted">
                              Path: {(s.path ?? []).join(" → ")} → {c.name}
                            </span>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-bold">Argues against</h4>
                    {c.opposing.length === 0 ? (
                      <p className="text-muted">Nothing recorded.</p>
                    ) : (
                      <ul className="mt-1 space-y-2">
                        {c.opposing.map((s) => (
                          <li key={s.term_id}>{s.label}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </Card>
            </li>
          ))}
        </ol>
      </section>

      <Card aria-labelledby="c-checks">
        <h2 id="c-checks" className="text-xl">
          Suggested checks
        </h2>
        {view.suggested_checks.length === 0 ? (
          <p className="mt-2 text-muted">No further checks stand out yet.</p>
        ) : (
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {view.suggested_checks.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        )}
      </Card>

      <Card aria-labelledby="c-ref">
        <h2 id="c-ref" className="text-xl">
          Referral letter draft
        </h2>
        {view.referral_draft ? (
          <>
            <label htmlFor="ref" className="sr-only">
              Referral letter, editable
            </label>
            <textarea
              id="ref"
              rows={12}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="mt-2 w-full rounded-lg border-2 border-border bg-card p-3"
            />
            <div className="no-print mt-2 flex flex-wrap gap-3">
              <Button tone="secondary" onClick={() => void navigator.clipboard.writeText(draft)}>
                Copy
              </Button>
              <Button tone="secondary" onClick={() => window.print()}>
                <Printer aria-hidden="true" size={18} /> Print
              </Button>
            </div>
          </>
        ) : (
          <p className="mt-2 text-muted">
            No referral draft yet. It appears when the pattern fits strongly and doctor or test
            findings are recorded.
          </p>
        )}
      </Card>

      <Card aria-labelledby="c-pheno" className="no-print">
        <h2 id="c-pheno" className="text-xl">
          Phenopacket
        </h2>
        <details>
          <summary className="min-h-11 cursor-pointer py-2 underline underline-offset-4">
            What is a Phenopacket?
          </summary>
          <p className="max-w-[65ch]">
            A GA4GH Phenopacket v2 is a standard file of a patient&apos;s phenotype: present and excluded
            HPO terms with onset, plus a metadata block naming the HPO version.
          </p>
        </details>
        <Button className="mt-2" onClick={() => void download()}>
          <Download aria-hidden="true" size={18} /> Download Phenopacket (JSON)
        </Button>
        {err ? (
          <p role="alert" className="mt-2">
            {err}
          </p>
        ) : null}
      </Card>
    </div>
  );
}
