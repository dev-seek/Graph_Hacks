"use client";

import { useRouter } from "next/navigation";
import { use, useRef, useState } from "react";
import { Loaded, WithToken, useLoad } from "@/components/Journey";
import { Button, ButtonLink, Card, ErrorBox, Notice } from "@/components/ui";
import { call, fam, friendly, type Extraction, type Pack, type State } from "@/lib/api";
import { SEE_DOCTOR } from "@/copy";
import { stashExtraction } from "@/lib/token";

function toBase64(buf: ArrayBuffer): string {
  let s = "";
  const b = new Uint8Array(buf);
  for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode(...b.subarray(i, i + 0x8000));
  return btoa(s);
}

function Upload({ id, token }: { id: string; token: string }) {
  const router = useRouter();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const file = useRef<HTMLInputElement>(null);

  async function send(body: unknown) {
    setBusy(true);
    setErr(null);
    try {
      const ex = await call<Extraction>(`${fam(id)}/documents`, { token, body });
      stashExtraction(id, ex);
      router.push(`/j/${id}/confirm`);
    } catch (e) {
      setErr(friendly(e));
      setBusy(false);
    }
  }

  return (
    <Card aria-labelledby="letter">
      <h2 id="letter" className="text-xl">
        Add your doctor&apos;s letter
      </h2>
      <p className="mt-2 text-muted">
        After the visit, paste the text of the letter or upload it as a PDF (up to 5 MB). We&apos;ll show
        you what we picked up before anything is saved.
      </p>
      <label htmlFor="letter-text" className="mt-3 block font-bold">
        Letter text
      </label>
      <textarea
        id="letter-text"
        rows={6}
        value={text}
        onChange={(e) => setText(e.target.value)}
        className="mt-1 w-full rounded-lg border-2 border-border bg-card p-3"
      />
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <Button disabled={busy || !text.trim()} onClick={() => void send({ kind: "text", text })}>
          Use this text
        </Button>
        <label className="font-bold">
          <span className="block">Or upload a PDF letter</span>
          <input
            ref={file}
            type="file"
            accept="application/pdf"
            className="min-h-11 max-w-full"
            onChange={async (e) => {
              const f = e.target.files?.[0];
              if (!f) return;
              if (f.size > 5 * 1024 * 1024) {
                setErr("That file is over 5 MB. Try a smaller scan, or paste the text instead.");
                return;
              }
              await send({ kind: "pdf", filename: f.name, content_base64: toBase64(await f.arrayBuffer()) });
            }}
          />
        </label>
      </div>
      {err ? (
        <div className="mt-3">
          <ErrorBox message={err} />
        </div>
      ) : null}
    </Card>
  );
}

function Doctor({ id, token }: { id: string; token: string }) {
  const state = useLoad<State>(`${fam(id)}/state`, token);
  const pack = useLoad<Pack>(`${fam(id)}/pack`, token);
  return (
    <div className="max-w-[65ch] space-y-6">
      <h1 className="text-3xl">See a doctor</h1>
      <Loaded load={state} what="this step">
        {(s) =>
          s.phase === "see_doctor" || s.phase === "specialist_step" || s.phase === "doctor_findings" ? (
            <Notice title="What happens next">
              <p>{s.phase === "see_doctor" ? SEE_DOCTOR : s.next_step.label}</p>
            </Notice>
          ) : (
            <Notice title="Not needed right now">
              <p>{s.next_step.label}</p>
            </Notice>
          )
        }
      </Loaded>
      <Loaded load={pack} what="your doctor pack">
        {(p) => (
          <>
            <Card aria-labelledby="why">
              <h2 id="why" className="text-xl">
                Why now
              </h2>
              <p className="mt-2">{p.summary}</p>
              <p className="mt-2 text-muted">
                This doesn&apos;t tell us what&apos;s causing it. It helps you and your doctor decide
                what to check.
              </p>
            </Card>
            {p.questions_for_doctor.length > 0 ? (
              <Card aria-labelledby="ask">
                <h2 id="ask" className="text-xl">
                  Questions to ask your doctor
                </h2>
                <ul className="mt-2 list-disc space-y-1 pl-5">
                  {p.questions_for_doctor.map((q) => (
                    <li key={q}>{q}</li>
                  ))}
                </ul>
              </Card>
            ) : null}
            <Card aria-labelledby="bring">
              <h2 id="bring" className="text-xl">
                What to bring
              </h2>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                <li>The one-page summary (print it or show it on your phone).</li>
                <li>Any earlier letters, test results and growth charts.</li>
                <li>A list of medicines and anything you&apos;ve tried.</li>
              </ul>
              <div className="mt-4">
                <ButtonLink href={`/j/${id}/pack`}>Open the doctor pack</ButtonLink>
              </div>
              <details className="mt-3">
                <summary className="min-h-11 cursor-pointer py-2 underline underline-offset-4">
                  What is a doctor pack?
                </summary>
                <p>
                  A single page that lists what you&apos;ve noticed in plain words, the checks worth
                  asking about, and a code that lets your doctor see a clinical version with sources.
                </p>
              </details>
            </Card>
          </>
        )}
      </Loaded>
      <Upload id={id} token={token} />
    </div>
  );
}

export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <WithToken id={id}>{(token) => <Doctor id={id} token={token} />}</WithToken>;
}
