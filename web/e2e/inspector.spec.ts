import { expect, test } from "@playwright/test";
import { axeClean, skipTours } from "./helpers";

test.beforeEach(async ({ page }) => skipTours(page));

test("example family has a live FalkorDB inspector with the queries it ran", async ({ page }) => {
  await page.goto("/start");
  await page.getByRole("button", { name: "Use an example story" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page).toHaveURL(/\/j\/([^/]+)\/round\/\d+/, { timeout: 30_000 });
  const id = page.url().match(/\/j\/([^/]+)\//)![1];
  await page.goto(`/j/${id}`);
  await page.getByRole("link", { name: "FalkorDB inspector (live)" }).click();
  await expect(page.getByRole("heading", { name: "Behind the scenes: FalkorDB inspector (live)" })).toBeVisible();
  await expect(page.getByText(/\d+ queries from the query registry/)).toBeVisible({ timeout: 15_000 });
  const first = page.locator("details summary").first();
  await first.click();
  await expect(page.locator("details[open] pre").first()).toContainText(/MATCH|CALL|RETURN/);
  await axeClean(page);
});

test("an ordinary family's query log stays closed (403)", async ({ page }) => {
  const res = await page.request.post("/api/families");
  const c = await res.json();
  const q = await page.request.get(`/api/debug/queries?family_id=${c.family_id}`, {
    headers: { Authorization: `Bearer ${c.family_token}` },
  });
  expect(q.status()).toBe(403);
});
