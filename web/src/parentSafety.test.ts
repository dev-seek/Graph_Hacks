import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { PARENT_BANNED } from "./copy";

// Parent-facing text must have no banned words and no disease names (spec §6.3, AGENTS.md rule 1).
// The lexicon is generated from the knowledge graph by `make lexicon`; without it only the word
// list is checked (CI has no FalkorDB) and the e2e suite repeats the check on the rendered DOM.
const root = path.resolve(__dirname, "../..");
const lexPath = path.join(root, "data/derived/disease_lexicon.json");
const lexicon: string[] = fs.existsSync(lexPath) ? JSON.parse(fs.readFileSync(lexPath, "utf8")) : [];
const NEGATIONS = ["not a diagnosis", "does not diagnose", "no diagnosis", "is this a diagnosis"];

function clean(s: string): string {
  let t = s.toLowerCase();
  for (const n of NEGATIONS) t = t.split(n).join(" ");
  return t;
}
const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

function parentStrings(file: string): string[] {
  const doc = JSON.parse(fs.readFileSync(file, "utf8")) as { steps: { caption: string; payload: Record<string, unknown> }[] };
  const out: string[] = [];
  const skip = new Set(["queries", "gate", "clinician", "phenopacket"]);
  const walk = (x: unknown) => {
    if (typeof x === "string") out.push(x);
    else if (Array.isArray(x)) x.forEach(walk);
    else if (x && typeof x === "object")
      for (const [k, v] of Object.entries(x)) if (!skip.has(k)) walk(v);
  };
  for (const s of doc.steps) {
    out.push(s.caption);
    walk(s.payload);
  }
  return out;
}

describe("recorded demo parent text", () => {
  for (const j of ["kabir", "arjun", "maya"]) {
    const strings = parentStrings(path.join(root, "data/demo", `${j}.json`));
    it(`${j}: no banned words`, () => {
      for (const s of strings)
        for (const w of PARENT_BANNED) expect(clean(s), `${w} in "${s}"`).not.toContain(w);
    });
    it.skipIf(lexicon.length === 0)(`${j}: no disease names (${lexicon.length} in lexicon)`, () => {
      const text = strings.map(clean).join("\n");
      const hits = lexicon.filter((n) => new RegExp(`\\b${esc(n.toLowerCase())}\\b`).test(text));
      expect(hits.slice(0, 3)).toEqual([]);
    });
  }
});

describe("parent route source text", () => {
  const files = [
    "app/page.tsx",
    "app/start/page.tsx",
    "app/help/page.tsx",
    "app/j/[id]/page.tsx",
    "app/j/[id]/confirm/page.tsx",
    "app/j/[id]/round/[n]/page.tsx",
    "app/j/[id]/doctor/page.tsx",
    "app/j/[id]/pack/page.tsx",
    "app/j/[id]/timeline/page.tsx",
    "src/components/Constellation.tsx",
  ].map((f) => path.join(__dirname, "..", f));
  for (const f of files)
    it(path.relative(path.join(__dirname, ".."), f), () => {
      const text = clean(fs.readFileSync(f, "utf8"));
      for (const w of PARENT_BANNED) expect(text, w).not.toContain(w);
    });
});
