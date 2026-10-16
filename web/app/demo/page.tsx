"use client";

import Link from "next/link";
import { Loaded, useLoad } from "@/components/Journey";
import { Card, Notice } from "@/components/ui";
import type { DemoJourney } from "@/lib/api";
import { DEMO_BANNER } from "@/copy";

export default function Demo() {
  const load = useLoad<DemoJourney[]>("/demo/journeys", null);
  return (
    <div className="space-y-6">
      <Notice title={DEMO_BANNER}>
        <p>Three made-up families. Pick one and step through what happens, about two minutes each.</p>
      </Notice>
      <h1 className="text-3xl">Example families</h1>
      <Loaded load={load} what="the example families">
        {(js) => (
          <ul className="grid gap-4 sm:grid-cols-3">
            {js.map((j) => (
              <li key={j.id}>
                <Card className="h-full">
                  <h2 className="text-xl">
                    <Link href={`/demo/${j.id}`}>{j.title.split(":")[0]}</Link>
                  </h2>
                  <p className="mt-2">{j.blurb}</p>
                  <p className="mt-3">
                    <Link href={`/demo/${j.id}`} className="font-bold">
                      Step through {j.title.split(":")[0]}&apos;s journey
                    </Link>
                  </p>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </Loaded>
      <p className="text-muted">
        Judges: add <code>?judge=1</code> to a journey to see the live FalkorDB inspector beside it.
      </p>
    </div>
  );
}
