"use client";

import { useRouter } from "next/navigation";
import { use, useState } from "react";
import { useMounted } from "@/lib/hooks";
import { WithToken } from "@/components/Journey";
import { Button, ButtonLink, Card, ErrorBox, Notice } from "@/components/ui";
import { call, fam, friendly, type Extraction, type State } from "@/lib/api";
import { clearExtraction, readExtraction } from "@/lib/token";

type Choice = "accept" | "reject";

function Confirm({ id, token }: { id: string; token: string }) {
  const router = useRouter();
  const mounted = useMounted();
  const ex = mounted ? readExtraction<Extraction>(id) : undefined;
  const [rejected, setRejected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const choice = (i: string): Choice => (rejected.has(i) ? "reject" : "accept");

  if (ex === undefined) return <p role="status">Loading…</p>;
  if (ex === null)
    return (
      <Notice title="We no longer have this list on this device">
        <p>Your story is saved. Go back to your journey to see what comes next.</p>
        <p className="mt-3">
          <ButtonLink href={`/j/${id}`}>Back to your journey</ButtonLink>
        </p>
      </Notice>
    );

  const items = ex.extraction_to_confirm;
  async function submit() {
    setBusy(true);
    setErr(null);
    try {
      const st = await call<State>(`${fam(id)}/confirm`, {
        token,
        body: {
          accept: items.filter((i) => choice(i.id) === "accept").map((i) => i.id),
          reject: items.filter((i) => choice(i.id) === "reject").map((i) => i.id),
          edits: [],
        },
      });
      clearExtraction(id);
      router.push(st.phase === "questions" ? `/j/${id}/round/${Math.max(1, st.round_no)}` : `/j/${id}`);
    } catch (e) {
      setErr(friendly(e));
      setBusy(false);
    }
  }

  return (
    <div className="max-w-[65ch] space-y-5">
      <h1 className="text-3xl">Here&apos;s what we understood</h1>
      <p>
        Each item is in plain words, with the part of your story it came from. Untick anything
        that isn&apos;t right.
      </p>
      {items.length === 0 ? (
        <Notice title="We didn't pick out anything specific">
          <p>That&apos;s okay. You can add more detail, or carry on.</p>
        </Notice>
      ) : (
        <ul className="space-y-3">
          {items.map((i) => (
            <li key={i.id}>
              <Card>
                <label className="flex min-h-11 items-start gap-3">
                  <input
                    type="checkbox"
                    className="mt-1 size-6 shrink-0 accent-[var(--night)]"
                    checked={choice(i.id) === "accept"}
                    onChange={(e) => {
                      const r = new Set(rejected);
                      if (e.target.checked) r.delete(i.id);
                      else r.add(i.id);
                      setRejected(r);
                    }}
                  />
                  <span>
                    <span className="block font-bold">
                      {i.status === "absent" ? "Not seen: " : ""}
                      {i.plain_label}
                    </span>
                    <span className="block text-muted">
                      From your story: &ldquo;{i.quote}&rdquo;
                    </span>
                  </span>
                </label>
              </Card>
            </li>
          ))}
        </ul>
      )}
      {err ? <ErrorBox message={err} /> : null}
      <Button onClick={submit} disabled={busy}>
        {busy ? "Saving…" : "This looks right — continue"}
      </Button>
    </div>
  );
}

export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <WithToken id={id}>{(token) => <Confirm id={id} token={token} />}</WithToken>;
}
