import { expect, test } from "@playwright/test";
import { axeClean } from "./helpers";

test("welcome tour: first visit, next/back/skip, reopen, keyboard only", async ({ page }) => {
  await page.goto("/");
  const dlg = page.getByRole("dialog");
  await expect(dlg).toBeVisible();
  await expect(dlg.getByRole("heading")).toHaveText("What Constellation is, and isn't");
  await axeClean(page);
  // focus is inside the dialog; Tab cycles within it
  await page.keyboard.press("Tab");
  expect(await dlg.evaluate((d) => d.contains(document.activeElement))).toBe(true);
  await dlg.getByRole("button", { name: "Next" }).focus();
  await page.keyboard.press("Enter");
  await expect(dlg.getByRole("heading")).toHaveText("How a round works");
  await dlg.getByRole("button", { name: "Back" }).focus();
  await page.keyboard.press("Enter");
  await expect(dlg.getByRole("heading")).toHaveText("What Constellation is, and isn't");
  await dlg.getByRole("button", { name: "Skip" }).focus();
  await page.keyboard.press("Enter");
  await expect(dlg).toBeHidden();
  // stays closed on reload (seen flag), reopens from the header
  await page.reload();
  await expect(page.getByRole("dialog")).toBeHidden();
  await page.getByRole("button", { name: "How it works" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  // Escape closes
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
});

test("tour: four steps for parents, Done on the last", async ({ page }) => {
  await page.goto("/");
  const dlg = page.getByRole("dialog");
  for (let i = 0; i < 3; i++) await dlg.getByRole("button", { name: "Next" }).click();
  await expect(dlg.getByText("Step 4 of 4")).toBeVisible();
  await dlg.getByRole("button", { name: "Done" }).click();
  await expect(dlg).toBeHidden();
});

test("tour works without storage", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "localStorage", {
      get() {
        throw new Error("blocked");
      },
    });
  });
  await page.goto("/");
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Skip" }).click();
  await expect(page.getByRole("dialog")).toBeHidden();
});

test("clinician tour has three steps", async ({ page }) => {
  await page.goto("/clinician/x");
  const dlg = page.getByRole("dialog");
  await expect(dlg.getByText("Step 1 of 3")).toBeVisible();
});

test("centre tour has three steps and the dashboard shows the illustrative-data label", async ({ page }) => {
  await page.goto("/centre");
  await expect(page.getByRole("dialog").getByText("Step 1 of 3")).toBeVisible();
  await page.getByRole("button", { name: "Skip" }).click();
  await expect(page.getByText("Illustrative clinic data").first()).toBeVisible();
  await axeClean(page);
});
