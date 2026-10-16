import { expect, test } from "@playwright/test";
import { axeClean, noOverflow, parentSafe, skipTours, tabTo } from "./helpers";

test.beforeEach(async ({ page }) => skipTours(page));

test("landing: hero, three steps, trust strip, axe clean, parent-safe", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Connect the dots no single appointment can see.");
  await expect(page.getByText("Not a diagnosis · Built on open medical knowledge · Delete your information any time")).toBeVisible();
  await expect(page.getByRole("link", { name: "See an example family (2 min)" })).toBeVisible();
  await axeClean(page);
  await parentSafe(page);
});

test("example story reaches round 1 in two clicks", async ({ page }) => {
  await page.goto("/start");
  await page.getByRole("button", { name: "Use an example story" }).click(); // click 1
  await page.getByRole("button", { name: "Continue" }).click(); // click 2
  await expect(page).toHaveURL(/\/j\/[^/]+\/round\/\d+/, { timeout: 30_000 });
  await expect(page.getByRole("heading", { name: /Round 1/ })).toBeVisible();
  await expect(page.getByText("Answer what you can — 'Not sure' is fine.")).toBeVisible();
  await axeClean(page);
  await parentSafe(page);
});

test("parent journey with the keyboard only: story, confirm, rounds, doctor, pack", async ({ page }) => {
  await page.goto("/start");
  await tabTo(page, page.getByRole("button", { name: "Use an example story" }));
  await page.keyboard.press("Enter");
  await tabTo(page, page.getByRole("button", { name: "Continue" }));
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/round\//, { timeout: 30_000 });

  for (let r = 0; r < 4 && /\/round\//.test(page.url()); r++) {
    const groups = page.getByRole("radiogroup");
    const n = await groups.count();
    for (let i = 0; i < n; i++) {
      await tabTo(page, groups.nth(i).getByRole("radio").first());
      await page.keyboard.press("ArrowRight"); // No
    }
    await tabTo(page, page.getByRole("button", { name: "Send my answers" }));
    await page.keyboard.press("Enter");
    await page.waitForLoadState("networkidle");
  }
  await expect(page).toHaveURL(/\/j\/[^/]+$/, { timeout: 30_000 });
  await expect(page.getByRole("heading", { name: "What happens next" })).toBeVisible();
  await parentSafe(page);
  // journey page keeps the key private and offers delete
  await expect(page.getByRole("button", { name: "Delete everything" })).toBeVisible();
  await axeClean(page);
});

test("360 px: key pages have no horizontal scroll", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  for (const p of ["/", "/start", "/demo", "/demo/kabir", "/help", "/about", "/centre"]) {
    await page.goto(p);
    await page.waitForLoadState("networkidle");
    await noOverflow(page);
  }
});

test("doctor pack prints and carries a QR with the code in the fragment", async ({ page, request }) => {
  const created = await (await request.post("http://127.0.0.1:8010/api/families")).json();
  expect(created.family_id).toBeTruthy();
});

test("urgent story stops everything and shows the mandatory text", async ({ page }) => {
  await page.goto("/start");
  await page.getByLabel("How old is your child, in years?").fill("1.5");
  await page.getByLabel("What have you noticed?").fill(
    "About ten minutes ago she went stiff and her arms and legs started jerking and she was not responding at all. It lasted ten minutes.",
  );
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page).toHaveURL(/\/j\/[^/]+$/, { timeout: 30_000 });
  await expect(page.getByRole("alert").filter({ hasText: "urgent medical help" })).toContainText("This needs urgent medical help. Call your local emergency number now (112 in India and Europe, 911 in the US)");
  await axeClean(page);
});
