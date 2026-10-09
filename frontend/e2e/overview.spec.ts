import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { asSampleLandlord } from "./mockApi";

test.beforeEach(async ({ page }) => {
  await asSampleLandlord(page);
});

test("overview leads with the next step and the year's figures", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Quarter 2 is ready to send");
  await expect(page.getByRole("link", { name: "Review and submit" })).toBeVisible();
  await expect(page.getByText("£10,183.60")).toBeVisible();
  await expect(page.getByText("Ready to send", { exact: true })).toBeVisible();
});

test("navigation fits the screen: tab bar, rail or sidebar", async ({ page }, { project }) => {
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "Main" });
  await expect(nav.getByRole("link", { name: "Transactions" })).toBeVisible();
  const box = (await nav.boundingBox())!;
  const viewport = page.viewportSize()!;
  if (project.name === "phone") {
    expect(Math.round(box.y + box.height)).toBe(viewport.height); // along the bottom
    expect(box.width).toBe(viewport.width);
  } else {
    expect(box.x).toBe(0); // down the left
    expect(box.width).toBe(project.name === "tablet" ? 88 : 240);
  }
});

test("no horizontal scrolling at any size", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("£10,183.60")).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBe(0);
});

test("every tap target is at least 44px tall", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("£10,183.60")).toBeVisible();
  const small = await page.locator("nav a, main button, a[class*='button']").evaluateAll((els) =>
    els
      .filter((el) => (el as HTMLElement).offsetParent !== null)
      .map((el) => ({ text: el.textContent?.trim(), height: el.getBoundingClientRect().height }))
      .filter((t) => t.height < 44),
  );
  expect(small).toEqual([]);
});

test("keyboard: skip link first, then the main navigation", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("£10,183.60")).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main")).toBeFocused();
});

test("moving between sections announces the new page", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Tax" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Tax" })).toBeFocused();
  await expect(page).toHaveTitle("Tax | LedgerLet");
});

test("no automatically detectable accessibility problems", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("£10,183.60")).toBeVisible();
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.help} (${v.nodes.length})`)).toEqual([]);
});

test("sign-in page is accessible too", async ({ page, context }) => {
  await context.clearCookies();
  await page.addInitScript(() => sessionStorage.clear());
  await page.goto("/sign-in");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(results.violations.map((v) => v.id)).toEqual([]);
});
