"use client";

import QRCode from "qrcode";
import { use, useEffect, useState } from "react";
import { Printer } from "lucide-react";
import { Loaded, WithToken, useLoad } from "@/components/Journey";
import { Button } from "@/components/ui";
import { fam, type Pack } from "@/lib/api";
import { useMounted } from "@/lib/hooks";
import { PARENT_DISCLAIMER } from "@/copy";

function ageText(m: number): string {
  if (m < 24) return `${m} months`;
  const y = Math.floor(m / 12);
  const r = m % 12;
  return r ? `${y} years ${r} months` : `${y} years`;
}

function Sheet({ id, pack }: { id: string; pack: Pack }) {
  const [qr, setQr] = useState<string | null>(null);
  const mounted = useMounted();
  // Code in the fragment: it is never sent to a server by the QR scan itself.
  const link = mounted
    ? `${window.location.origin}/clinician/${id}#code=${encodeURIComponent(pack.clinician_code)}`
    : "";
  useEffect(() => {
    if (!link) return;
    QRCode.toDataURL(link, { margin: 1, width: 220, errorCorrectionLevel: "M" })
      .then(setQr)
      .catch(() => setQr(null));
  }, [link]);

  const present = pack.findings.filter((f) => f.status === "present");
  const absent = pack.findings.filter((f) => f.status === "absent");
  return (
    <article className="print-page mx-auto max-w-[7.2in] rounded-2xl border border-line bg-card p-6" aria-label="Doctor pack">
      <header className="flex items-start justify-between gap-4 border-b border-line pb-3">
        <div>
          <h1 className="text-2xl">Summary for your doctor</h1>
          <p className="text-muted">
            Child&apos;s age: {ageText(pack.child_age_months)} · Prepared {new Date(pack.generated_at).toLocaleDateString()}
          </p>
        </div>
      </header>
      <p className="mt-3">{pack.summary}</p>

      <section aria-labelledby="p-seen" className="mt-4">
        <h2 id="p-seen" className="text-lg">
          What the family has noticed
        </h2>
        <ul className="mt-1 list-disc space-y-0.5 pl-5">
          {present.map((f) => (
            <li key={f.id}>
              {f.plain_label}
              {f.onset_months != null ? ` (from about ${ageText(Math.round(f.onset_months))})` : ""}
            </li>
          ))}
        </ul>
        {absent.length > 0 ? (
          <>
            <h3 className="mt-2 text-base">Not seen</h3>
            <ul className="list-disc space-y-0.5 pl-5">
              {absent.map((f) => (
                <li key={f.id}>{f.plain_label}</li>
              ))}
            </ul>
          </>
        ) : null}
      </section>

      {pack.checks_to_ask_about.length > 0 ? (
        <section aria-labelledby="p-checks" className="mt-4">
          <h2 id="p-checks" className="text-lg">
            Checks to ask about
          </h2>
          <ul className="mt-1 list-disc space-y-0.5 pl-5">
            {[...new Set(pack.checks_to_ask_about)].map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {pack.questions_for_doctor.length > 0 ? (
        <section aria-labelledby="p-q" className="mt-4">
          <h2 id="p-q" className="text-lg">
            Questions for the doctor
          </h2>
          <ul className="mt-1 list-disc space-y-0.5 pl-5">
            {pack.questions_for_doctor.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-labelledby="p-code" className="mt-5 flex items-center gap-4 border-t border-line pt-3">
        {qr ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={qr} width={110} height={110} alt={`QR code for the clinician view. Link: ${link}`} />
        ) : null}
        <div>
          <h2 id="p-code" className="text-lg">
            For the clinician
          </h2>
          <p>
            Clinician code: <strong className="font-mono">{pack.clinician_code}</strong>
          </p>
          <p className="text-sm text-muted">Scan the code, or open the clinician page and type this code.</p>
        </div>
      </section>
      <p className="mt-4 text-xs text-muted">{pack.disclaimer || PARENT_DISCLAIMER}</p>
    </article>
  );
}

function PackPage({ id, token }: { id: string; token: string }) {
  const load = useLoad<Pack>(`${fam(id)}/pack`, token);
  return (
    <div className="space-y-4">
      <div className="no-print flex flex-wrap items-center gap-3">
        <Button onClick={() => window.print()}>
          <Printer aria-hidden="true" size={18} /> Print or save as PDF
        </Button>
        <p className="text-muted">Works on A4 and Letter paper.</p>
      </div>
      <Loaded load={load} what="your doctor pack">
        {(p) => <Sheet id={id} pack={p} />}
      </Loaded>
    </div>
  );
}

export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <WithToken id={id}>{(token) => <PackPage id={id} token={token} />}</WithToken>;
}
