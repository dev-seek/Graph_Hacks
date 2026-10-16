import { expect, test } from "@playwright/test";
import { axeClean, noOverflow, parentSafe, skipTours, tabTo } from "./helpers";

const API = "http://127.0.0.1:8010/api";
const STORY =
  "Kabir has low muscle tone, delayed walking, delayed speech, a squint, a small head, a heart murmur and feeding problems.";

async function family(request: import("@playwright/test").APIRequestContext) {
  const c = await (await request.post(`${API}/families`)).json();
  const h = { Authorization: `Bearer ${c.family_token}`, "Content-Type": "application/json" };
  const ex = await (await request.post(`${API}/families/${c.family_id}/story`, { headers: h, data: { text: STORY, child_age_months: 30 } })).json();
  return { id: c.family_id as string, token: c.family_token as string, h, ex };
}

test.describe("with tours skipped", () => {
  test.beforeEach(async ({ page }) => skipTours(page));

  test("typed story: confirm page lists items with quotes, an item can be unticked, then round 1", async ({ page }) => {
    await page.goto("/start");
    await page.getByLabel("How old is your child, in years?").fill("2.5");
    await page.getByLabel("What have you noticed?").fill(STORY);
    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page).toHaveURL(/\/confirm$/, { timeout: 30_000 });
    await expect(page.getByRole("heading", { name: "Here's what we understood" })).toBeVisible();
    const boxes = page.getByRole("checkbox");
    expect(await boxes.count()).toBeGreaterThan(0);
    await expect(page.getByText(/From your story:/).first()).toBeVisible();
    await axeClean(page);
    await boxes.first().uncheck();
    await page.getByRole("button", { name: "This looks right — continue" }).click();
    await expect(page).toHaveURL(/\/(round\/\d+|j\/[^/]+)$/, { timeout: 30_000 });
  });

  test("axe on every parent page of a real family", async ({ page, request }) => {
    const f = await family(request);
    await page.goto(`/j/${f.id}/confirm#t=${encodeURIComponent(f.token)}`);
    // extraction is not in this tab's storage: the page must say so and offer the way back
    await expect(page.getByText("We no longer have this list on this device")).toBeVisible();
    await axeClean(page);
    await request.post(`${API}/families/${f.id}/confirm`, { headers: f.h, data: { accept: f.ex.extraction_to_confirm.map((i: { id: string }) => i.id), reject: [], edits: [] } });
    for (const p of ["", "/round/1", "/timeline", "/doctor"]) {
      await page.goto(`/j/${f.id}${p}`);
      await page.waitForLoadState("networkidle");
      await axeClean(page);
      await parentSafe(page);
    }
    for (const p of ["/start", "/help", "/about", "/clinician/x"]) {
      await page.goto(p);
      await page.waitForLoadState("networkidle");
      await axeClean(page);
    }
  });

  test("pack: QR points at the clinician page with the code in the fragment; print hides controls", async ({ page, request }) => {
    const f = await family(request);
    const steps = await (await request.get(`${API}/demo/kabir/steps`)).json();
    const pack = steps.find((s: { screen: string }) => s.screen === "see_doctor").payload.pack;
    await page.route("**/api/families/*/pack", (r) => r.fulfill({ json: pack }));
    await page.goto(`/j/${f.id}/pack#t=${encodeURIComponent(f.token)}`);
    await expect(page.getByRole("heading", { name: "Summary for your doctor" })).toBeVisible();
    const qr = page.getByRole("img", { name: /QR code for the clinician view/ });
    await expect(qr).toBeVisible();
    const alt = (await qr.getAttribute("alt")) ?? "";
    expect(alt).toContain(`/clinician/${f.id}#code=`);
    await expect(page.getByText(pack.clinician_code)).toBeVisible();
    await page.emulateMedia({ media: "print" });
    await expect(page.getByRole("button", { name: /Print or save as PDF/ })).toBeHidden();
    await expect(page.getByRole("heading", { name: "Summary for your doctor" })).toBeVisible();
    await page.emulateMedia({ media: "screen" });
    await page.setViewportSize({ width: 360, height: 740 });
    await noOverflow(page);
  });

  test("keyboard only: Kabir demo to the last step and the Phenopacket download", async ({ page }) => {
    await page.goto("/demo/kabir");
    const total = Number(/of (\d+)/.exec(await page.getByText(/^Step 1 of \d+\./).innerText())?.[1]);
    for (let i = 1; i < total; i++) {
      await tabTo(page, page.getByRole("button", { name: "Next" }));
      await page.keyboard.press("Enter");
    }
    await expect(page.getByText(new RegExp(`^Step ${total} of ${total}\\.`))).toBeVisible();
    const dl = page.waitForEvent("download");
    await tabTo(page, page.getByRole("button", { name: "Download Phenopacket (JSON)" }));
    await page.keyboard.press("Enter");
    expect((await dl).suggestedFilename()).toMatch(/^phenopacket-.*\.json$/);
  });
});

test.describe("tours", () => {
  test("header 'How it works' reopens the tour on /help, /about and a journey page", async ({ page, request }) => {
    const f = await family(request);
    for (const url of ["/help", "/about", `/j/${f.id}#t=${encodeURIComponent(f.token)}`, "/demo"]) {
      await skipToursOnce(page);
      await page.goto(url);
      await expect(page.getByRole("dialog")).toBeHidden();
      await page.getByRole("button", { name: "How it works" }).click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(page.getByRole("dialog")).toBeHidden();
    }
  });

  test("/help 'Take the short tour' opens it", async ({ page }) => {
    await skipToursOnce(page);
    await page.goto("/help");
    await page.getByRole("button", { name: "Take the short tour" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
  });
});

async function skipToursOnce(page: import("@playwright/test").Page) {
  await page.addInitScript(() => {
    for (const r of ["parent", "clinician", "centre"]) window.localStorage.setItem(`cx:flag:tour:${r}`, "1");
  });
}
