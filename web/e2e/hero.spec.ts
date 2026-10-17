import { test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { skipTours } from "./helpers";

// `HERO=<dir> E2E_BASE_URL=http://127.0.0.1:8080 pnpm e2e hero` writes raw frames for scripts/make_hero_gif.py.
// It drives the recorded Kabir journey (replay mode: no model, no network).
const out = process.env.HERO;
test.skip(!out, "set HERO=<output dir> to capture the README hero frames");

test("hero frames", async ({ page }) => {
  test.setTimeout(120_000);
  fs.mkdirSync(out!, { recursive: true });
  await skipTours(page);
  await page.setViewportSize({ width: 1100, height: 900 });
  const next = async (n: number) => {
    for (let i = 0; i < n; i++) await page.getByRole("button", { name: "Next" }).click();
  };
  await page.goto("/demo/kabir");
  await next(2); // step 3: round 1, what the parent sees
  await page.waitForTimeout(500);
  await page.locator("main").screenshot({ path: path.join(out!, "parent.png") });
  await page.goto("/demo/kabir?judge=1");
  await next(2);
  const aside = page.locator('aside[aria-label^="FalkorDB inspector"]');
  const card = aside.locator('[aria-labelledby="insp-q"]');
  const box = (await card.boundingBox())!;
  const top = box.y + (await page.evaluate(() => window.scrollY));
  await page.screenshot({ path: path.join(out!, "inspector-head.png"), fullPage: true, clip: { x: box.x, y: top, width: box.width, height: 110 } });
  const q = aside.locator("details", { hasText: /^q2a/ }).first();
  await q.locator("summary").click();
  await page.waitForTimeout(400);
  await q.screenshot({ path: path.join(out!, "inspector-q.png") });
  await page.goto("/demo/kabir");
  await next(10); // step 11: the clinician view of the same family
  await page.waitForTimeout(500);
  await page.getByRole("heading", { name: /Candidate patterns/ }).locator("xpath=..").screenshot({ path: path.join(out!, "clinician.png") });
});
