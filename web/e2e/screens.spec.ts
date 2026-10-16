import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { skipTours } from "./helpers";

// Gate evidence: `SCREENSHOTS=1 pnpm e2e screens` writes docs/explain/P4-screens/*.png (360 and 1280 px).
const out = path.resolve(__dirname, "../../docs/explain/P4-screens");
const API = "http://127.0.0.1:8010/api";
test.skip(!process.env.SCREENSHOTS, "set SCREENSHOTS=1 to refresh the gate screenshots");

const sizes = [
  { w: 360, h: 780 },
  { w: 1280, h: 900 },
];

async function shot(page: Page, name: string, w: number) {
  fs.mkdirSync(out, { recursive: true });
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: path.join(out, `${name}-${w}.png`), fullPage: true });
}

test("screenshots", async ({ page, request }) => {
  test.setTimeout(180_000);
  await skipTours(page);
  const steps = await (await request.get(`${API}/demo/kabir/steps`)).json();
  const pack = steps.find((s: { screen: string }) => s.screen === "see_doctor").payload.pack;
  const clin = steps.find((s: { screen: string }) => s.screen === "referral_ready").payload.clinician;

  const c = await (await request.post(`${API}/families`)).json();
  const auth = { Authorization: `Bearer ${c.family_token}`, "Content-Type": "application/json" };
  const story = "Kabir has low muscle tone, delayed walking, delayed speech, a squint, a small head, a heart murmur and feeding problems.";
  const ex = await (await request.post(`${API}/families/${c.family_id}/story`, { headers: auth, data: { text: story, child_age_months: 30 } })).json();
  await request.post(`${API}/families/${c.family_id}/confirm`, { headers: auth, data: { accept: ex.extraction_to_confirm.map((i: { id: string }) => i.id), reject: [], edits: [] } });
  await page.route("**/api/families/*/pack", (r) => r.fulfill({ json: pack }));
  await page.route("**/api/clinician/*", (r) => r.fulfill({ json: clin }));

  for (const { w, h } of sizes) {
    await page.setViewportSize({ width: w, height: h });
    await page.goto("/");
    await shot(page, "01-landing", w);
    await page.goto("/start");
    await page.getByRole("button", { name: "Use an example story" }).click();
    await shot(page, "02-start-example", w);
    await page.goto(`/j/${c.family_id}/round/1#t=${encodeURIComponent(c.family_token)}`);
    await expect(page.getByRole("heading", { name: /Round 1/ })).toBeVisible();
    await shot(page, "03-round", w);
    await page.goto(`/j/${c.family_id}`);
    await expect(page.getByRole("heading", { name: "Your journey" })).toBeVisible();
    await shot(page, "04-journey", w);
    await page.goto(`/j/${c.family_id}/doctor`);
    await expect(page.getByRole("heading", { name: "See a doctor" })).toBeVisible();
    await shot(page, "05-doctor", w);
    await page.goto(`/j/${c.family_id}/pack`);
    await expect(page.getByRole("heading", { name: "Summary for your doctor" })).toBeVisible();
    await page.waitForTimeout(400);
    await shot(page, "06-pack", w);
    await page.goto(`/clinician/${c.family_id}#code=demo`);
    await expect(page.getByRole("heading", { name: "Clinician view" })).toBeVisible();
    await shot(page, "07-clinician", w);
    await page.goto("/demo");
    await shot(page, "08-demo-picker", w);
    await page.goto("/demo/kabir?judge=1");
    const total = Number(/of (\d+)/.exec(await page.getByText(/^Step 1 of \d+/).innerText())?.[1]);
    for (let i = 1; i < total; i++) await page.getByRole("button", { name: "Next" }).click();
    await page.waitForTimeout(800);
    await shot(page, "09-demo-judge", w);
    await page.goto("/demo/maya");
    await page.getByRole("button", { name: "Next" }).click();
    await shot(page, "10-urgent", w);
    await page.goto("/about");
    await shot(page, "11-about", w);
  }
  // print preview of the pack on both paper sizes
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/j/${c.family_id}/pack`);
  await expect(page.getByRole("heading", { name: "Summary for your doctor" })).toBeVisible();
  await page.waitForTimeout(400);
  await page.emulateMedia({ media: "print" });
  for (const [name, width, height] of [["a4", "210mm", "297mm"], ["letter", "8.5in", "11in"]] as const) {
    await page.pdf({ path: path.join(out, `pack-print-${name}.pdf`), width, height });
  }
});
