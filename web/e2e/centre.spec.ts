import { expect, test } from "@playwright/test";
import { axeClean, noOverflow, skipTours } from "./helpers";

// Needs the seeded centre graph (`make centre`) and, for the what-if, `make kb-prev`.
test.beforeEach(async ({ page }) => {
  await skipTours(page);
});

test("centre dashboard: routing, ask, groups, bridges; no axe violations; 360 px", async ({ page }) => {
  await page.goto("/centre");
  await expect(page.getByRole("heading", { name: "Who should take this case?" })).toBeVisible();
  await expect(page.getByText("Illustrative clinic data").first()).toBeVisible();
  // routing shows five look-alikes, each with a clinician and a protocol
  const rows = page.getByRole("table", { name: "Closest solved look-alike cases" }).locator("tbody tr");
  await expect(rows).toHaveCount(5, { timeout: 15_000 });
  await expect(page.getByText(/^Suggested \(for staff to confirm\): Clinician/)).toBeVisible();
  // ask the centre (keyword path: the e2e API runs with LLM_MODE=off)
  await page.getByRole("button", { name: "Which protocol is fastest?" }).click();
  await expect(page.getByText(/Fastest on average/)).toBeVisible();
  await page.getByLabel("Your question").fill("which signs link groups?");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByText(/Signs that connect the most groups/)).toBeVisible();
  // bridges and clusters
  await expect(page.getByRole("heading", { name: "Signs that link groups of cases" })).toBeVisible();
  await expect(page.getByRole("list", { name: "Groups" })).toBeVisible();
  await page.getByRole("button", { name: "Tight groups" }).click();
  await expect(page.getByText("Connected groups of cases with a strong overlap")).toBeVisible();
  await axeClean(page);
  await page.setViewportSize({ width: 360, height: 740 });
  await noOverflow(page);
});

test("centre dashboard: notes and the query log", async ({ page }) => {
  await page.goto("/centre");
  await page.getByLabel("Add a note").fill("Reviewed at the clinic meeting");
  await page.getByRole("button", { name: "Save note" }).click();
  await expect(page.getByText("Reviewed at the clinic meeting").first()).toBeVisible();
  await page.getByRole("button", { name: "Show recent queries" }).click();
  await expect(page.getByText("q7_centre_routing").first()).toBeVisible();
  await axeClean(page);
});

test("centre dashboard: knowledge-update re-check", async ({ page }) => {
  test.setTimeout(180_000);
  await page.goto("/centre");
  await page.getByRole("button", { name: /Re-check open cases on kb_/ }).click();
  await expect(page.getByText(/open cases rescored on kb_/)).toBeVisible({ timeout: 150_000 });
  await expect(page.getByText(/The live centre is unchanged/)).toBeVisible();
  await axeClean(page);
});
