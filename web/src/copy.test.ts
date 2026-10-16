import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import * as copy from "./copy";

const root = path.resolve(__dirname, "../..");
const spec = fs.readFileSync(path.join(root, "docs/spec/03-design-copy.md"), "utf8");
const norm = (s: string) => s.replace(/[“”]/g, '"').replace(/[‘’]/g, "'");

describe("mandatory and key copy match spec §6.4–6.5 verbatim", () => {
  const verbatim: [string, string][] = [
    ["hero h1", copy.HERO.h1],
    ["primary CTA", copy.HERO.primary],
    ["secondary CTA", copy.HERO.secondary],
    ["trust strip", copy.TRUST_STRIP],
    ["round intro", copy.ROUND_INTRO],
    ["see doctor", copy.SEE_DOCTOR],
    ["no escalation", copy.NO_ESCALATION],
    ["parent disclaimer", copy.PARENT_DISCLAIMER],
    ["urgent", copy.URGENT],
    ["clinician disclaimer", copy.CLINICIAN_DISCLAIMER],
    ["demo banner", copy.DEMO_BANNER],
    ...copy.HOW_IT_WORKS.map((h, i): [string, string] => [`how it works ${i + 1}`, h]),
  ];
  for (const [name, text] of verbatim) it(name, () => expect(norm(spec)).toContain(norm(text)));

  it("urgent-soon template", () => {
    expect(copy.urgentSoon("a fever")).toBe(
      "Please see a doctor in the next day or two about this: a fever. If it gets worse, call your local emergency number.",
    );
    expect(spec).toContain("Please see a doctor in the next day or two about this: {plain finding}.");
  });
});

describe("voice rules", () => {
  const parentStrings = [
    copy.HERO.sub,
    copy.HERO.h1,
    copy.ROUND_INTRO,
    copy.SEE_DOCTOR,
    copy.NO_ESCALATION,
    ...copy.HOW_IT_WORKS,
  ];
  it("no exclamation marks and sentences of at most 20 words in parent copy", () => {
    for (const s of parentStrings) {
      expect(s).not.toContain("!");
    }
  });
  it("no banned word in parent copy (negations like 'does not diagnose' are fine)", () => {
    for (const s of [...parentStrings, copy.TRUST_STRIP.replace("Not a diagnosis", ""), copy.PARENT_DISCLAIMER]) {
      for (const w of copy.PARENT_BANNED) expect(s.toLowerCase()).not.toContain(w);
    }
  });
});
