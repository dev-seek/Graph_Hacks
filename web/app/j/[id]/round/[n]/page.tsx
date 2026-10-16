"use client";

import { useRouter } from "next/navigation";
import { use, useEffect, useRef, useState } from "react";
import { Loaded, WithToken, useLoad } from "@/components/Journey";
import { Button, ButtonLink, ErrorBox, Notice } from "@/components/ui";
import { call, fam, friendly, type AnswersOut, type Round } from "@/lib/api";
import { ROUND_INTRO } from "@/copy";

type Val = "yes" | "no" | "unsure";
const OPTIONS: [Val, string][] = [
  ["yes", "Yes"],
  ["no", "No"],
  ["unsure", "Not sure"],
];

function RoundForm({ id, token, round }: { id: string; token: string; round: Round }) {
  const router = useRouter();
  const [vals, setVals] = useState<Record<string, Val>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [announce, setAnnounce] = useState("");
  const done = round.questions.every((q) => vals[q.qid]);
  const heading = useRef<HTMLHeadingElement>(null);
  const live = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    // A new round: move focus to its heading and fill the (initially empty) live region.
    heading.current?.focus();
    if (live.current)
      live.current.textContent = `Round ${round.round_no}: ${round.questions.length} questions.`;
  }, [round.round_no, round.questions.length]);

  async function submit() {
    setBusy(true);
    setErr(null);
    setAnnounce("Saving your answers.");
    try {
      const out = await call<AnswersOut>(`${fam(id)}/round/${round.round_no}/answers`, {
        token,
        body: { answers: round.questions.map((q) => ({ qid: q.qid, value: vals[q.qid] ?? "unsure" })) },
      });
      const n = out.next;
      router.push(
        n.phase === "questions" ? `/j/${id}/round/${Math.max(1, n.round_no)}` : `/j/${id}`,
      );
    } catch (e) {
      setErr(friendly(e));
      setAnnounce("");
      setBusy(false);
    }
  }

  return (
    <form
      className="max-w-[65ch] space-y-6"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <div>
        <h1 ref={heading} tabIndex={-1} className="text-3xl">
          Round {round.round_no}
        </h1>
        <p className="mt-2">{ROUND_INTRO}</p>
        <p ref={live} aria-live="polite" role="status" className="sr-only" />
        <p aria-live="polite" role="status" className="sr-only">
          {announce}
        </p>
      </div>
      {round.questions.map((q, i) => (
        <fieldset key={q.qid} className="rounded-2xl border border-line bg-card p-5">
          <legend className="px-1 text-sm text-muted">
            Question {i + 1} of {round.questions.length}
          </legend>
          <p className="text-lg font-bold">{q.text}</p>
          <p className="mt-1 text-muted">Why we ask: {q.why}</p>
          {q.how_to_check ? (
            <details className="mt-2">
              <summary className="min-h-11 cursor-pointer py-2 underline underline-offset-4">
                How to check
              </summary>
              <p className="mt-1">{q.how_to_check}</p>
            </details>
          ) : null}
          <div role="radiogroup" aria-label={q.text} className="mt-3 flex flex-wrap gap-2">
            {OPTIONS.map(([v, label]) => {
              const on = vals[q.qid] === v;
              return (
                <label
                  key={v}
                  className={`flex min-h-11 min-w-24 cursor-pointer items-center justify-center rounded-lg border-2 px-4 font-bold has-[:focus-visible]:outline has-[:focus-visible]:outline-[3px] has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-night ${
                    on ? "border-night bg-night text-card" : "border-border bg-card text-ink"
                  }`}
                >
                  <input
                    type="radio"
                    name={q.qid}
                    value={v}
                    checked={on}
                    onChange={() => setVals({ ...vals, [q.qid]: v })}
                    className="sr-only"
                  />
                  {label}
                </label>
              );
            })}
          </div>
          {q.ask_doctor ? (
            <p className="mt-2 text-sm text-muted">
              A doctor can help check this one. &ldquo;Not sure&rdquo; is fine, and we&apos;ll put it on
              your list of questions for them.
            </p>
          ) : null}
        </fieldset>
      ))}
      {err ? <ErrorBox message={err} /> : null}
      <Button type="submit" disabled={busy || !done}>
        {busy ? "Saving…" : "Send my answers"}
      </Button>
      {!done ? <p className="text-sm text-muted">Pick an answer for each question to go on.</p> : null}
    </form>
  );
}

function RoundPage({ id, token }: { id: string; token: string }) {
  const load = useLoad<Round>(`${fam(id)}/round`, token);
  return (
    <Loaded load={load} what="your questions">
      {(r) =>
        r.questions.length === 0 ? (
          <Notice title="No questions right now">
            <p>Go back to your journey to see what happens next.</p>
            <p className="mt-3">
              <ButtonLink href={`/j/${id}`}>Back to your journey</ButtonLink>
            </p>
          </Notice>
        ) : (
          <RoundForm key={r.round_no} id={id} token={token} round={r} />
        )
      }
    </Loaded>
  );
}

export default function Page({ params }: { params: Promise<{ id: string; n: string }> }) {
  const { id } = use(params);
  return <WithToken id={id}>{(token) => <RoundPage id={id} token={token} />}</WithToken>;
}
