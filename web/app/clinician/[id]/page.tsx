"use client";

import { use, useState } from "react";
import { ClinicianBody } from "@/components/ClinicianBody";
import { Loaded, useLoad } from "@/components/Journey";
import { Button, Card } from "@/components/ui";
import { type ClinicianView } from "@/lib/api";
import { useMounted } from "@/lib/hooks";


function View({ id, code }: { id: string; code: string }) {
  const load = useLoad<ClinicianView>(`/clinician/${id}`, null, code);
  return <Loaded load={load} what="the clinician view">{(v) => <ClinicianBody view={v} id={id} code={code} />}</Loaded>;
}

export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const mounted = useMounted();
  const fromHash = mounted ? (/[#&]code=([^&]+)/.exec(window.location.hash)?.[1] ?? "") : "";
  const [typed, setTyped] = useState("");
  const [sent, setSent] = useState("");
  const code = sent || (fromHash ? decodeURIComponent(fromHash) : "");
  return (
    <>
      {code ? (
        <View id={id} code={code} />
      ) : (
        <Card className="max-w-[40ch]">
          <h1 className="text-2xl">Clinician view</h1>
          <form
            className="mt-3 space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              setSent(typed.trim());
            }}
          >
            <label htmlFor="code" className="block font-bold">
              Clinician code
            </label>
            <p className="text-sm text-muted">It is printed on the family&apos;s doctor pack.</p>
            <input
              id="code"
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              className="min-h-11 w-full rounded-lg border-2 border-border bg-card px-3 font-mono"
              autoComplete="off"
            />
            <Button type="submit" disabled={!typed.trim()}>
              Open
            </Button>
          </form>
        </Card>
      )}
    </>
  );
}
