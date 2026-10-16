"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Button } from "./ui";
import { flag, setFlag } from "@/lib/token";

const noSubscribe = () => () => {};

export type Role = "parent" | "clinician" | "centre";

export const TOURS: Record<Role, { title: string; body: string }[]> = {
  parent: [
    {
      title: "What Constellation is, and isn't",
      body: "Constellation helps you gather details and decide when to see a doctor. It does not diagnose, and it doesn't tell you what's causing anything.",
    },
    {
      title: "How a round works",
      body: "Each round has 3 to 5 short questions. Answer what you can. 'Not sure' is always fine.",
    },
    {
      title: "The doctor pack",
      body: "When it's a good time to see a doctor, you get a one-page summary to print or show on your phone, plus questions you can ask.",
    },
    {
      title: "Privacy and deleting",
      body: "No name, no birth date, no location. You can delete everything from the journey page at any time.",
    },
  ],
  clinician: [
    {
      title: "Findings with sources",
      body: "Every finding shows its HPO term, whether it is present or absent, and where it came from.",
    },
    {
      title: "Candidates with graph paths",
      body: "Candidate patterns come with the findings that support and oppose them, and the path from finding to disease annotation in the graph.",
    },
    {
      title: "Referral and Phenopacket",
      body: "When the pattern fits strongly, a referral draft and a GA4GH Phenopacket v2 file are ready to download.",
    },
  ],
  centre: [
    {
      title: "Look-alikes and who solved them",
      body: "The centre keeps shared memory: similar cases, who solved them, and with which protocol.",
    },
    {
      title: "Bridge signs and clusters",
      body: "Bridge signs link different groups of cases. Clusters show families of cases that look alike.",
    },
    {
      title: "Knowledge-update re-check",
      body: "When the knowledge base updates, the centre shows which open cases would change.",
    },
  ],
};

export function Tour({
  role,
  open,
  onClose,
}: {
  role: Role;
  open: boolean;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [i, setI] = useState(0);
  const steps = TOURS[role];
  const last = i === steps.length - 1;

  const close = useCallback(() => {
    setFlag(`tour:${role}`);
    setI(0);
    onClose();
  }, [role, onClose]);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) {
      if (typeof d.showModal === "function") d.showModal();
      else d.setAttribute("open", "");
    }
    if (!open && d.open) d.close();
  }, [open]);

  const step = steps[i];
  if (!step) return null;
  return (
    <dialog
      ref={ref}
      aria-labelledby="tour-title"
      onCancel={(e) => {
        e.preventDefault();
        close();
      }}
      className="m-auto w-[min(92vw,34rem)] rounded-2xl border-2 border-night bg-card p-6 text-ink backdrop:bg-night/60"
    >
      <p className="text-sm text-muted">
        Step {i + 1} of {steps.length}
      </p>
      <h2 id="tour-title" className="mt-1 text-2xl">
        {step.title}
      </h2>
      <p className="mt-3" aria-live="polite">
        {step.body}
      </p>
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <Button tone="secondary" onClick={() => setI(i - 1)} disabled={i === 0}>
          Back
        </Button>
        {last ? (
          <Button onClick={close}>Done</Button>
        ) : (
          <Button onClick={() => setI(i + 1)}>Next</Button>
        )}
        {!last ? (
          <Button tone="secondary" onClick={close} className="ml-auto">
            Skip
          </Button>
        ) : null}
      </div>
    </dialog>
  );
}

/** Shows the tour on a first visit and when the header's "How it works" asks for it. */
export function useTour(role: Role) {
  const seen = useSyncExternalStore(
    noSubscribe,
    () => flag(`tour:${role}`),
    () => true,
  );
  const [forced, setForced] = useState(false);
  const [closed, setClosed] = useState(false);
  useEffect(() => {
    const h = () => {
      setForced(true);
      setClosed(false);
    };
    window.addEventListener("cx:open-tour", h);
    return () => window.removeEventListener("cx:open-tour", h);
  }, []);
  return { open: !closed && (forced || !seen), close: () => setClosed(true) };
}

export function TourHost({ role }: { role: Role }) {
  const { open, close } = useTour(role);
  return <Tour role={role} open={open} onClose={close} />;
}
