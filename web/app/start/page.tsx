"use client";

import { useRouter } from "next/navigation";
import { useId, useState } from "react";
import { Button, Card, ErrorBox } from "@/components/ui";
import { call, fam, friendly, type Extraction, type State } from "@/lib/api";
import { rememberLast, saveToken, stashExtraction } from "@/lib/token";
import { EXAMPLE_STORY } from "@/exampleStory";

const MAX = 4000;
type Created = { family_id: string; family_token: string };

export default function Start() {
  const router = useRouter();
  const [years, setYears] = useState("");
  const [text, setText] = useState("");
  const [example, setExample] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const ids = { years: useId(), story: useId() };

  async function go(storyText: string, ageMonths: number, autoConfirm: boolean) {
    setBusy(true);
    setErr(null);
    try {
      // The made-up example is an example family: its graph queries can be shown in the live inspector.
      const c = await call<Created>(autoConfirm ? "/demo/families" : "/families", { method: "POST" });
      saveToken(c.family_id, c.family_token);
      rememberLast(c.family_id);
      const t = c.family_token;
      const ex = await call<Extraction>(`${fam(c.family_id)}/story`, {
        token: t,
        body: { text: storyText, child_age_months: ageMonths },
      });
      stashExtraction(c.family_id, ex);
      if (ex.safety.level !== "none") {
        router.push(`/j/${c.family_id}`);
        return;
      }
      // The made-up example skips the "check what we understood" step so a first-time visitor
      // reaches round 1 in two clicks (spec §4.7). A real story always goes through it.
      if (autoConfirm) {
        const st = await call<State>(`${fam(c.family_id)}/confirm`, {
          token: t,
          body: { accept: ex.extraction_to_confirm.map((x) => x.id), reject: [], edits: [] },
        });
        router.push(st.phase === "questions" ? `/j/${c.family_id}/round/1` : `/j/${c.family_id}`);
        return;
      }
      router.push(`/j/${c.family_id}/confirm`);
    } catch (e) {
      setErr(friendly(e));
      setBusy(false);
    }
  }

  const age = Math.round(parseFloat(years) * 12);
  const ageOk = Number.isFinite(age) && age >= 0 && age <= 240;

  return (
    <div className="max-w-[65ch]">
      <h1 className="text-3xl">Start with your story</h1>
      <Card className="mt-5" aria-labelledby="what-we-store">
        <h2 id="what-we-store" className="text-xl">
          Before you start
        </h2>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>
            We keep your child&apos;s age in months and what you tell us. No name, birth date or
            location.
          </li>
          <li>
            This is not a diagnosis. It helps you and your doctor decide what to check.
          </li>
          <li>
            You can delete everything at any time. On this demo, everything is deleted after 7
            days.
          </li>
        </ul>
        <p className="mt-3 text-muted">By pressing Continue you agree to this.</p>
      </Card>

      <form
        className="mt-6 space-y-5"
        onSubmit={(e) => {
          e.preventDefault();
          if (ageOk && text.trim()) void go(text.trim(), age, example);
        }}
      >
        <div>
          <label htmlFor={ids.years} className="block font-bold">
            How old is your child, in years?
          </label>
          <p id={`${ids.years}-hint`} className="text-sm text-muted">
            A rough age is fine. For a baby, use 0.5 for six months.
          </p>
          <input
            id={ids.years}
            inputMode="decimal"
            value={years}
            onChange={(e) => setYears(e.target.value)}
            className="mt-1 min-h-11 w-32 rounded-lg border-2 border-border bg-card px-3"
            required
            aria-describedby={`${ids.years}-hint`}
          />
          {years && !ageOk ? (
            <p role="alert" className="text-sm text-urgent">
              Please enter an age from 0 to 20.
            </p>
          ) : null}
        </div>
        <div>
          <label htmlFor={ids.story} className="block font-bold">
            What have you noticed?
          </label>
          <p className="text-sm text-muted">
            In your own words: what worries you, since when, and what doctors have said.
          </p>
          {example ? (
            <p className="mt-1 text-sm font-bold text-night">
              Example story — made up. Change it or send it as it is.
            </p>
          ) : null}
          <textarea
            id={ids.story}
            value={text}
            onChange={(e) => {
              setText(e.target.value.slice(0, MAX));
              setExample(false);
            }}
            rows={9}
            className="mt-1 w-full rounded-lg border-2 border-border bg-card p-3"
            required
          />
          <p className="text-sm text-muted">
            {text.length} of {MAX} characters
          </p>
        </div>
        {err ? <ErrorBox message={err} /> : null}
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={busy || !ageOk || !text.trim()}>
            {busy ? "Reading your story…" : "Continue"}
          </Button>
          <Button
            type="button"
            tone="secondary"
            disabled={busy}
            onClick={() => {
              setYears(String(EXAMPLE_STORY.ageMonths / 12));
              setText(EXAMPLE_STORY.text);
              setExample(true);
            }}
          >
            Use an example story
          </Button>
        </div>
        {!ageOk || !text.trim() ? (
          <p className="text-sm text-muted">
            Add your child&apos;s age and a few words about what you&apos;ve noticed to go on.
          </p>
        ) : null}
      </form>
    </div>
  );
}
