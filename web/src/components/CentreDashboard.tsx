"use client";

import { useState } from "react";
import { Button, Card, ErrorBox, Loading, Notice } from "./ui";
import { useLoad } from "@/lib/hooks";
import { call, friendly, type Schemas } from "@/lib/api";
import { CENTRE_DATA_LABEL, CENTRE_DISCLAIMER, CENTRE_QUESTIONS } from "@/copy";

type Overview = Schemas["CentreOverview"];
type CaseRow = Schemas["CentreCaseRow"];
type Routing = Schemas["CentreRouting"];
type CaseDetail = Schemas["CentreCase"];
type Bridge = Schemas["CentreBridge"];
type Cluster = Schemas["CentreCluster"];
type Protocol = Schemas["CentreProtocolStat"];
type Clinician = Schemas["CentreClinicianStat"];
type Note = Schemas["CentreNote"];
type WhatIf = Schemas["CentreWhatIfOut"];
type Ask = Schemas["CentreAskOut"];
type Query = Schemas["QueryLogEntry"];

const th = "py-2 pr-3 text-left font-bold";
const td = "py-2 pr-3 align-top";

export function CentreDashboard({ overview }: { overview: Overview }) {
  const open = useLoad<CaseRow[]>("/centre/cases?limit=500", null);
  const [caseId, setCaseId] = useState("");
  const openCases = (open.data ?? []).filter((c) => c.status !== "resolved");
  const chosen = caseId || openCases[0]?.case_id || "";

  return (
    <div className="space-y-8">
      <Notice title={CENTRE_DATA_LABEL}>
        <p>{CENTRE_DISCLAIMER}</p>
        <p className="mt-2 text-muted">
          {overview.cases} cases · {overview.resolved} solved · {overview.clinicians} clinicians ·{" "}
          {overview.protocols} protocols · knowledge base {overview.kb_version}
        </p>
      </Notice>

      <Routing caseId={chosen} setCaseId={setCaseId} openCases={openCases} loading={open.loading} />
      <AskCentre />
      <div className="grid gap-8 md:grid-cols-2">
        <Bridges />
        <Clusters setCaseId={setCaseId} />
      </div>
      <Protocols />
      <WhatIfPanel kb={overview.kb_version} setCaseId={setCaseId} />
      {chosen ? <Notes caseId={chosen} /> : null}
      <QueryLog />
    </div>
  );
}

function Routing({
  caseId,
  setCaseId,
  openCases,
  loading,
}: {
  caseId: string;
  setCaseId: (id: string) => void;
  openCases: CaseRow[];
  loading: boolean;
}) {
  const route = useLoad<Routing>(caseId ? `/centre/routing/${caseId}` : null, null);
  const detail = useLoad<CaseDetail>(caseId ? `/centre/cases/${caseId}` : null, null);
  return (
    <Card aria-labelledby="cx-route">
      <h2 id="cx-route" className="text-xl">
        Who should take this case?
      </h2>
      <p className="text-muted">
        Pick an open case. We look for solved cases with the same signs, then show who solved them and which tests
        they used.
      </p>
      {loading ? <Loading what="open cases" /> : null}
      <label className="mt-3 block font-bold" htmlFor="cx-case">
        Open case
      </label>
      <select
        id="cx-case"
        className="mt-1 min-h-11 rounded-lg border-2 border-border bg-card px-3"
        value={caseId}
        onChange={(e) => setCaseId(e.target.value)}
      >
        {openCases.map((c) => (
          <option key={c.case_id} value={c.case_id}>
            {c.case_id} · {c.status} · age {c.age_band}
          </option>
        ))}
      </select>
      {detail.data ? (
        <p className="mt-3">
          <strong>Signs recorded:</strong> {detail.data.terms.join(", ") || "none"}
        </p>
      ) : null}
      {route.error ? <ErrorBox message={route.error} onRetry={route.reload} /> : null}
      {route.data ? (
        <div className="mt-4 space-y-4">
          <div className="rounded-xl border-2 border-sage p-4" aria-live="polite">
            <p className="font-bold">
              Suggested: {route.data.suggested_clinician ?? "no clinician"}
              {route.data.suggested_specialty ? ` (${route.data.suggested_specialty})` : ""}
            </p>
            <p>
              Protocol: {route.data.suggested_protocol ?? "none"}
              {route.data.suggested_tests?.length ? ` — ${route.data.suggested_tests.join(", ")}` : ""}
              {route.data.expected_days ? ` — usually about ${route.data.expected_days} days` : ""}
            </p>
          </div>
          <div className="overflow-x-auto" tabIndex={0}>
            <table className="w-full min-w-[40rem] border-collapse">
              <caption className="sr-only">Closest solved look-alike cases</caption>
              <thead>
                <tr className="border-b border-border">
                  <th scope="col" className={th}>Case</th>
                  <th scope="col" className={th}>Solved as</th>
                  <th scope="col" className={th}>Shared signs</th>
                  <th scope="col" className={th}>Clinician</th>
                  <th scope="col" className={th}>Protocol</th>
                  <th scope="col" className={th}>Days</th>
                </tr>
              </thead>
              <tbody>
                {route.data.lookalikes.map((l) => (
                  <tr key={l.case_id} className="border-b border-line">
                    <th scope="row" className={td}>{l.case_id}</th>
                    <td className={td}>{l.diagnosis ?? "—"}</td>
                    <td className={td}>
                      {l.shared_terms.slice(0, 4).join(", ")}
                      {l.shared_terms.length > 4 ? ` +${l.shared_terms.length - 4} more` : ""}
                    </td>
                    <td className={td}>
                      {l.clinician}
                      <br />
                      <span className="text-muted">{l.specialty}</span>
                    </td>
                    <td className={td}>{l.protocol}</td>
                    <td className={td}>{l.turnaround_days}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-sm text-muted">{route.data.disclaimer}</p>
        </div>
      ) : route.loading && caseId ? (
        <Loading what="look-alikes" />
      ) : null}
    </Card>
  );
}

function AskCentre() {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState<Ask | null>(null);
  const [err, setErr] = useState<string | null>(null);
  async function ask(text: string) {
    if (!text.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      setAnswer(await call<Ask>("/centre/ask", { body: { question: text } }));
    } catch (e) {
      setErr(friendly(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Card aria-labelledby="cx-ask">
      <h2 id="cx-ask" className="text-xl">
        Ask the centre
      </h2>
      <p className="text-muted">
        Questions are matched to a fixed set of checks on the case memory. Nothing is typed into the database.
      </p>
      <form
        className="mt-3 flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          void ask(q);
        }}
      >
        <div className="grow">
          <label htmlFor="cx-q" className="block font-bold">
            Your question
          </label>
          <input
            id="cx-q"
            className="mt-1 min-h-11 w-full rounded-lg border-2 border-border bg-card px-3"
            value={q}
            maxLength={500}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <Button type="submit" disabled={busy}>
          {busy ? "Asking…" : "Ask"}
        </Button>
      </form>
      <ul className="mt-3 flex flex-wrap gap-2" aria-label="Example questions">
        {CENTRE_QUESTIONS.map((x) => (
          <li key={x}>
            <Button
              tone="secondary"
              type="button"
              onClick={() => {
                setQ(x);
                void ask(x);
              }}
            >
              {x}
            </Button>
          </li>
        ))}
      </ul>
      <div aria-live="polite" className="mt-3">
        {err ? <p>{err}</p> : null}
        {answer ? (
          <div className="rounded-xl border-2 border-sage p-4">
            <p>{answer.answer}</p>
            <p className="mt-1 text-sm text-muted">Checks used: {answer.query_ids.join(", ")}</p>
          </div>
        ) : null}
      </div>
    </Card>
  );
}

function Bridges() {
  const load = useLoad<Bridge[]>("/centre/bridges", null);
  return (
    <Card aria-labelledby="cx-bridge">
      <h2 id="cx-bridge" className="text-xl">
        Signs that link groups of cases
      </h2>
      <p className="text-muted">The signs that sit between the most pairs of cases (betweenness, sampled).</p>
      {load.error ? <ErrorBox message={load.error} onRetry={load.reload} /> : null}
      {load.data ? (
        <ol className="mt-2 space-y-1">
          {load.data.map((b) => (
            <li key={b.term_id}>
              {b.name} <span className="text-sm text-muted">({b.term_id} · score {Math.round(b.score)})</span>
            </li>
          ))}
        </ol>
      ) : (
        <Loading what="bridge signs" />
      )}
    </Card>
  );
}

function Clusters({ setCaseId }: { setCaseId: (id: string) => void }) {
  const [method, setMethod] = useState<"lp" | "wcc">("lp");
  const load = useLoad<Cluster[]>(`/centre/clusters?method=${method}`, null);
  return (
    <Card aria-labelledby="cx-clu">
      <h2 id="cx-clu" className="text-xl">
        Groups of similar cases
      </h2>
      <div className="mt-2 flex gap-2" role="group" aria-label="Grouping method">
        <Button tone={method === "lp" ? "primary" : "secondary"} aria-pressed={method === "lp"} onClick={() => setMethod("lp")}>
          Communities
        </Button>
        <Button tone={method === "wcc" ? "primary" : "secondary"} aria-pressed={method === "wcc"} onClick={() => setMethod("wcc")}>
          Tight groups
        </Button>
      </div>
      <p className="mt-2 text-sm text-muted">
        {method === "lp"
          ? "Label propagation over each case's five closest cases."
          : "Connected groups of cases with a strong overlap (score 0.30 or more)."}
      </p>
      {load.error ? <ErrorBox message={load.error} onRetry={load.reload} /> : null}
      {load.data ? (
        <ul className="mt-2 max-h-72 space-y-2 overflow-y-auto" tabIndex={0} aria-label="Groups">
          {load.data.slice(0, 12).map((c) => (
            <li key={c.cluster_id}>
              <strong>{c.size} cases:</strong>{" "}
              {c.cases.slice(0, 8).map((id) => (
                <button key={id} type="button" className="mr-2 min-h-11 underline" onClick={() => setCaseId(id)}>
                  {id}
                </button>
              ))}
              {c.cases.length > 8 ? `+${c.cases.length - 8} more` : ""}
            </li>
          ))}
          {load.data.length === 0 ? <li>No groups at this setting.</li> : null}
        </ul>
      ) : (
        <Loading what="groups" />
      )}
    </Card>
  );
}

function Protocols() {
  const protos = useLoad<Protocol[]>("/centre/protocols", null);
  const work = useLoad<Clinician[]>("/centre/workload", null);
  return (
    <Card aria-labelledby="cx-proto">
      <h2 id="cx-proto" className="text-xl">
        Protocols and clinicians
      </h2>
      <div className="mt-2 grid gap-6 md:grid-cols-2">
        <div className="overflow-x-auto" tabIndex={0}>
          <table className="w-full min-w-[20rem] border-collapse">
            <caption className="sr-only">Protocols by speed</caption>
            <thead>
              <tr className="border-b border-border">
                <th scope="col" className={th}>Protocol</th>
                <th scope="col" className={th}>Cases</th>
                <th scope="col" className={th}>Avg days</th>
              </tr>
            </thead>
            <tbody>
              {(protos.data ?? []).map((p) => (
                <tr key={p.protocol} className="border-b border-line">
                  <th scope="row" className={td}>{p.protocol}</th>
                  <td className={td}>{p.cases}</td>
                  <td className={td}>{Math.round(p.avg_days)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="overflow-x-auto" tabIndex={0}>
          <table className="w-full min-w-[20rem] border-collapse">
            <caption className="sr-only">Cases per clinician</caption>
            <thead>
              <tr className="border-b border-border">
                <th scope="col" className={th}>Clinician</th>
                <th scope="col" className={th}>Cases</th>
                <th scope="col" className={th}>Solved</th>
              </tr>
            </thead>
            <tbody>
              {(work.data ?? []).map((c) => (
                <tr key={c.clinician} className="border-b border-line">
                  <th scope="row" className={td}>
                    {c.clinician}
                    <br />
                    <span className="font-normal text-muted">{c.specialty}</span>
                  </th>
                  <td className={td}>{c.cases}</td>
                  <td className={td}>{c.resolved}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  );
}

function WhatIfPanel({ kb, setCaseId }: { kb: string; setCaseId: (id: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<WhatIf | null>(null);
  const [err, setErr] = useState<string | null>(null);
  async function run() {
    setBusy(true);
    setErr(null);
    try {
      setRes(await call<WhatIf>("/centre/whatif", { body: { new_kb_version: kb } }));
    } catch (e) {
      setErr(friendly(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Card aria-labelledby="cx-what">
      <h2 id="cx-what" className="text-xl">
        When the knowledge base updates
      </h2>
      <p className="text-muted">
        Open cases were last checked against an older release. This copies the centre, re-scores every open case on{" "}
        {kb} and lists the ones that now show a much stronger rare-disease pattern.
      </p>
      <div className="mt-3">
        <Button onClick={() => void run()} disabled={busy}>
          {busy ? "Re-checking…" : `Re-check open cases on ${kb}`}
        </Button>
        <p className="mt-2 text-sm text-muted">The first run can take up to a minute.</p>
      </div>
      <div aria-live="polite" className="mt-3">
        {err ? <p>{err}</p> : null}
        {res ? (
          <div className="space-y-3">
            <p className="font-bold">{res.summary}</p>
            <p className="text-sm text-muted">
              Done in {Math.round(res.ms)} ms on a copy of the graph ({res.graph}); the live centre is unchanged.
            </p>
            {(res.details ?? []).length > 0 ? (
              <div className="overflow-x-auto" tabIndex={0}>
                <table className="w-full min-w-[24rem] border-collapse">
                  <caption className="sr-only">Open cases whose picture changed</caption>
                  <thead>
                    <tr className="border-b border-border">
                      <th scope="col" className={th}>Case</th>
                      <th scope="col" className={th}>Before</th>
                      <th scope="col" className={th}>After</th>
                      <th scope="col" className={th}>Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(res.details ?? []).map((d) => (
                      <tr key={d.case_id} className="border-b border-line">
                        <th scope="row" className={td}>
                          <button type="button" className="min-h-11 underline" onClick={() => setCaseId(d.case_id)}>
                            {d.case_id}
                          </button>
                        </th>
                        <td className={td}>{d.before.toFixed(2)}</td>
                        <td className={td}>{d.after.toFixed(2)}</td>
                        <td className={td}>{d.direction === "crosses_up" ? "now above the line" : "now below the line"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </Card>
  );
}

function Notes({ caseId }: { caseId: string }) {
  const load = useLoad<Note[]>(`/centre/notes?target=${caseId}`, null);
  const [text, setText] = useState("");
  const [err, setErr] = useState<string | null>(null);
  async function add() {
    setErr(null);
    try {
      await call<Note>("/centre/notes", { body: { kind: "case", target: caseId, text } });
      setText("");
      load.reload();
    } catch (e) {
      setErr(friendly(e));
    }
  }
  return (
    <Card aria-labelledby="cx-notes">
      <h2 id="cx-notes" className="text-xl">
        Notes on {caseId}
      </h2>
      <ul className="mt-2 space-y-2">
        {(load.data ?? []).map((n) => (
          <li key={n.id}>
            {n.text} <span className="text-sm text-muted">({n.role}, {n.at.slice(0, 10)})</span>
          </li>
        ))}
        {load.data?.length === 0 ? <li className="text-muted">No notes yet.</li> : null}
      </ul>
      <form
        className="mt-3 flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          void add();
        }}
      >
        <div className="grow">
          <label htmlFor="cx-note" className="block font-bold">
            Add a note
          </label>
          <input
            id="cx-note"
            className="mt-1 min-h-11 w-full rounded-lg border-2 border-border bg-card px-3"
            value={text}
            maxLength={500}
            aria-describedby="cx-note-hint"
            onChange={(e) => setText(e.target.value)}
          />
          <p id="cx-note-hint" className="text-sm text-muted">
            Do not type names or other identifying details.
          </p>
        </div>
        <Button type="submit" disabled={!text.trim()}>
          Save note
        </Button>
      </form>
      {err ? <p role="alert">{err}</p> : null}
    </Card>
  );
}

function QueryLog() {
  const [show, setShow] = useState(false);
  const load = useLoad<Query[]>(show ? "/centre/inspector" : null, null);
  return (
    <Card aria-labelledby="cx-log">
      <h2 id="cx-log" className="text-xl">
        Graph queries behind this page
      </h2>
      <p className="text-muted">Every number here is a registered query on the FalkorDB centre graph.</p>
      <Button tone="secondary" className="mt-2" aria-expanded={show} onClick={() => setShow(!show)}>
        {show ? "Hide recent queries" : "Show recent queries"}
      </Button>
      {show && load.data ? (
        <ul className="mt-3 space-y-2">
          {load.data.slice(-12).map((q, i) => (
            <li key={`${q.name}-${i}`}>
              <details>
                <summary className="min-h-11 cursor-pointer py-2">
                  <span className="font-mono text-sm font-bold">{q.name}</span>{" "}
                  <span className="text-sm text-muted">
                    {q.rows} rows · {q.ms.toFixed(1)} ms
                  </span>
                </summary>
                <pre className="overflow-x-auto rounded-lg bg-night p-3 text-xs text-card">{q.cypher}</pre>
              </details>
            </li>
          ))}
          {load.data.length === 0 ? <li className="text-muted">No queries recorded yet. Use a panel above first.</li> : null}
        </ul>
      ) : null}
    </Card>
  );
}
