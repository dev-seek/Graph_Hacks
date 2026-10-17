import { expect, test, type Page } from "@playwright/test";
import { axeClean, parentSafe, skipTours, tabTo } from "./helpers";

const API = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:8010"}/api`;

async function walk(page: Page, journey: string) {
  await page.goto(`/demo/${journey}`);
  await expect(page.getByText("Example family — all details are made up.")).toBeVisible();
  const total = Number(/of (\d+)/.exec(await page.getByText(/^Step 1 of \d+\./).innerText())?.[1]);
  for (let i = 0; i < total; i++) {
    await expect(page.getByText(new RegExp(`^Step ${i + 1} of ${total}\\.`))).toBeVisible();
    await parentSafe(page, '[data-view="parent"]');
    if (i < total - 1) await page.getByRole("button", { name: "Next" }).click();
  }
}

test.describe("demo", () => {
  test.beforeEach(async ({ page }) => skipTours(page));

  test("picker shows the three example families", async ({ page }) => {
    await page.goto("/demo");
    for (const n of ["Kabir", "Arjun", "Maya"]) await expect(page.getByRole("heading", { name: n })).toBeVisible();
    await axeClean(page);
  });

  for (const j of ["kabir", "arjun", "maya"]) {
    test(`${j}: every step is parent-safe`, async ({ page }) => walk(page, j));
  }

  test("kabir ends with the clinician view and a Phenopacket download", async ({ page }) => {
    await page.goto("/demo/kabir");
    const total = Number(/of (\d+)/.exec(await page.getByText(/^Step 1 of \d+\./).innerText())?.[1]);
    for (let i = 1; i < total; i++) await page.getByRole("button", { name: "Next" }).click();
    const clin = page.locator('[data-view="clinician"]');
    await expect(clin.getByText("Decision support for clinician review.")).toBeVisible();
    await expect(clin.getByRole("heading", { name: "Findings" })).toBeVisible();
    const [dl] = await Promise.all([
      page.waitForEvent("download"),
      clin.getByRole("button", { name: "Download Phenopacket (JSON)" }).click(),
    ]);
    expect(dl.suggestedFilename()).toMatch(/^phenopacket-.*\.json$/);
    await axeClean(page);
  });

  test("maya shows the urgent text and nothing else to do", async ({ page }) => {
    await page.goto("/demo/maya");
    await page.getByRole("button", { name: "Next" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "urgent medical help" })).toContainText(
      "Call your local emergency number now (112 in India and Europe, 911 in the US)",
    );
  });

  test("judge mode (recorded run) shows queries with Cypher, timings, gate numbers and the graph", async ({ page }) => {
    await page.goto("/demo/kabir?judge=1");
    const insp = page.getByRole("complementary", { name: "FalkorDB inspector, recorded run" });
    await expect(insp).toBeVisible();
    await expect(insp.getByRole("heading", { name: "Graph queries this step" })).toBeVisible();
    await insp.locator("summary").first().click();
    await expect(insp.locator("pre").first()).toContainText(/MATCH|MERGE/);
    // advance to the step with a gate decision
    const total = Number(/of (\d+)/.exec(await page.getByText(/^Step 1 of \d+\./).innerText())?.[1]);
    for (let i = 1; i < total; i++) await page.getByRole("button", { name: "Next" }).click();
    await expect(insp.getByRole("heading", { name: /Gate decision: REFERRAL_READY/ })).toBeVisible();
    await expect(insp.getByRole("img", { name: /Evidence graph: \d+ nodes/ })).toBeVisible();
    await expect(insp.locator("canvas").first()).toBeAttached();
    await axeClean(page);
  });

  test("steps work from the keyboard", async ({ page }) => {
    await page.goto("/demo/arjun");
    await tabTo(page, page.getByRole("button", { name: "Next" }));
    await page.keyboard.press("Enter");
    await expect(page.getByText(/^Step 2 of \d+\./)).toBeVisible();
    await tabTo(page, page.getByRole("button", { name: "Back" }));
    await page.keyboard.press("Enter");
    await expect(page.getByText(/^Step 1 of \d+\./)).toBeVisible();
  });

  test("arjun ends with no escalation wording", async ({ page }) => {
    await page.goto("/demo/arjun");
    const total = Number(/of (\d+)/.exec(await page.getByText(/^Step 1 of \d+\./).innerText())?.[1]);
    for (let i = 1; i < total; i++) await page.getByRole("button", { name: "Next" }).click();
    await expect(page.getByText("Nothing you've told us needs a special appointment right now. Mention it at your next routine visit. Here's what to keep an eye on.")).toBeVisible();
  });
});

test("recorded demo API is reachable (replay data)", async ({ request }) => {
  const r = await request.get(`${API}/demo/journeys`);
  expect(r.ok()).toBeTruthy();
  expect((await r.json()).length).toBe(3);
});
