"use client";

import Link from "next/link";
import { use, useState } from "react";
import { Copy, Trash2 } from "lucide-react";
import { Constellation } from "@/components/Constellation";
import { Loaded, WithToken, useLoad } from "@/components/Journey";
import { Button, ButtonLink, Card, Notice } from "@/components/ui";
import { call, fam, friendly, type Constellation as C, type State } from "@/lib/api";
import { forgetToken } from "@/lib/token";
import { NO_ESCALATION, PARENT_DISCLAIMER, URGENT } from "@/copy";

function nextHref(id: string, s: State): { href: string; label: string } | null {
  switch (s.phase) {
    case "story":
      return { href: "/start", label: "Tell us your story" };
    case "confirm":
      return { href: `/j/${id}/confirm`, label: "Check what we understood" };
    case "questions":
      return { href: `/j/${id}/round/${Math.max(1, s.round_no)}`, label: "Answer a few questions" };
    case "see_doctor":
    case "doctor_findings":
    case "specialist_step":
      return { href: `/j/${id}/doctor`, label: "See your doctor step" };
    default:
      return null;
  }
}

function Home({ id, token }: { id: string; token: string }) {
  const state = useLoad<State>(`${fam(id)}/state`, token);
  const stars = useLoad<C>(`${fam(id)}/constellation`, token);
  // Only example families have an open query log (the API answers 403 for everyone else).
  const inspector = useLoad<unknown[]>(`/debug/queries?family_id=${id}`, token);
  const [copied, setCopied] = useState(false);
  const [gone, setGone] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  if (gone)
    return (
      <Notice title="Everything has been deleted">
        <p>Your story, answers and pack are gone from our servers. You can start again any time.</p>
        <p className="mt-3">
          <Link href="/">Back to the home page</Link>
        </p>
      </Notice>
    );

  return (
    <div className="space-y-6">
      <h1 className="text-3xl">Your journey</h1>
      <Loaded load={state} what="your journey">
        {(s) => {
          const step = nextHref(id, s);
          const urgent = s.phase === "urgent";
          return (
            <>
              {urgent ? (
                <Notice tone="urgent" title="Please get urgent help now">
                  <p>{s.banner ?? URGENT}</p>
                </Notice>
              ) : s.banner ? (
                <Notice title="Please read">
                  <p>{s.banner}</p>
                </Notice>
              ) : null}
              {!urgent ? (
                <Card aria-labelledby="next">
                  <h2 id="next" className="text-xl">
                    What happens next
                  </h2>
                  <p className="mt-2">
                    {s.phase === "watching" ? NO_ESCALATION : s.next_step.label}
                  </p>
                  {step ? (
                    <div className="mt-4">
                      <ButtonLink href={step.href}>{step.label}</ButtonLink>
                    </div>
                  ) : null}
                  {s.round_no > 0 && s.phase !== "watching" ? (
                    <p className="mt-3 text-sm text-muted">Round {s.round_no}</p>
                  ) : null}
                </Card>
              ) : null}
            </>
          );
        }}
      </Loaded>

      <section aria-labelledby="stars">
        <h2 id="stars" className="mb-3 text-xl">
          Your constellation
        </h2>
        <Loaded load={stars} what="your constellation">
          {(c) => <Constellation data={c} />}
        </Loaded>
      </section>

      <Card aria-labelledby="keep">
        <h2 id="keep" className="text-xl">
          Save this link to come back
        </h2>
        <p className="mt-2 text-muted">
          This link has your private key in it. Anyone with it can see your answers.
        </p>
        <div className="mt-3 flex flex-wrap gap-3">
          <Button
            tone="secondary"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(
                  `${window.location.origin}/j/${id}#t=${encodeURIComponent(token)}`,
                );
                setCopied(true);
              } catch {
                setErr("We couldn't copy it. Save this page in your bookmarks instead.");
              }
            }}
          >
            <Copy aria-hidden="true" size={18} /> Copy link
          </Button>
          <ButtonLink href={`/j/${id}/timeline`} tone="secondary">
            Everything recorded
          </ButtonLink>
          {inspector.data ? (
            <ButtonLink href={`/j/${id}/inspector`} tone="secondary">
              FalkorDB inspector (live)
            </ButtonLink>
          ) : null}
        </div>
        <p role="status" className="mt-2 text-sm text-sage">
          {copied ? "Link copied." : ""}
        </p>
        {err ? <p className="text-sm">{err}</p> : null}
      </Card>

      <Card aria-labelledby="del">
        <h2 id="del" className="text-xl">
          Delete everything
        </h2>
        <p className="mt-2 text-muted">This removes your story, answers and pack. It can&apos;t be undone.</p>
        <Button
          tone="secondary"
          className="mt-3"
          onClick={async () => {
            if (!window.confirm("Delete everything for this child? This can't be undone.")) return;
            try {
              await call(fam(id), { token, method: "DELETE" });
              forgetToken(id);
              setGone(true);
            } catch (e) {
              setErr(friendly(e));
            }
          }}
        >
          <Trash2 aria-hidden="true" size={18} /> Delete everything
        </Button>
      </Card>
      <p className="text-sm text-muted">{PARENT_DISCLAIMER}</p>
    </div>
  );
}

export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <WithToken id={id}>{(token) => <Home id={id} token={token} />}</WithToken>;
}
