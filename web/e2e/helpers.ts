import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

// Mirror of web/src/copy.ts PARENT_BANNED (kept here so e2e has no app imports).
export const BANNED = ["probability", "likely", "chance", "risk score", "diagnosis", "you have", "rule out", "rare disease", "posterior"];
// The disclaimer says "does not diagnose" and the privacy copy mentions "diagnosis" only in negation.
const ALLOWED_PHRASES = ["not a diagnosis", "does not diagnose", "is this a diagnosis"];

const lexPath = path.resolve(__dirname, "../../data/derived/disease_lexicon.json");
export const LEXICON: string[] = fs.existsSync(lexPath) ? (JSON.parse(fs.readFileSync(lexPath, "utf8")) as string[]) : [];

export async function skipTours(page: Page) {
  await page.addInitScript(() => {
    for (const r of ["parent", "clinician", "centre"]) window.localStorage.setItem(`cx:flag:tour:${r}`, "1");
  });
}

export async function axeClean(page: Page) {
  const r = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  expect(r.violations.map((v) => `${v.id}: ${v.nodes[0]?.html.slice(0, 120)}`)).toEqual([]);
}

export async function parentSafe(page: Page, scope = "body") {
  let text = (await page.locator(scope).innerText()).toLowerCase();
  for (const a of ALLOWED_PHRASES) text = text.split(a).join(" ");
  for (const w of BANNED) expect(text, `banned word "${w}"`).not.toContain(w);
  const hits = LEXICON.filter((n) => new RegExp(`\\b${n.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`).test(text));
  expect(hits.slice(0, 3), "disease names on a parent page").toEqual([]);
}

export async function noOverflow(page: Page) {
  const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(over, "horizontal scroll").toBeLessThanOrEqual(0);
}

/** Press Tab until the locator is focused (keyboard-only navigation). */
export async function tabTo(page: Page, target: ReturnType<Page["locator"]>, max = 80) {
  for (let i = 0; i < max; i++) {
    if (await target.evaluate((el) => el === document.activeElement).catch(() => false)) return;
    await page.keyboard.press("Tab");
  }
  throw new Error("could not reach element by keyboard");
}
