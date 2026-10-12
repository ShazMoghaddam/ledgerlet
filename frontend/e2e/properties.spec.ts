import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { asSampleLandlord } from "./mockApi";

const SHOTS = process.env.SHOTS;

async function checkPage(page: Page, name: string, project: string) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBe(0);
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.help} (${v.nodes.length})`)).toEqual([]);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}-${project}.png`, fullPage: true });
}

test.beforeEach(async ({ page }) => {
  await asSampleLandlord(page);
});

test("the properties list, one property, and the forms", async ({ page }, { project }) => {
  await page.goto("/properties");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Properties");
  await expect(page.getByText("4,800.00").first()).toBeVisible();
  await checkPage(page, "properties", project.name);

  await page
    .getByRole("link", { name: /Oak Road/ })
    .first()
    .click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Oak Road");
  await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
  await expect(page.getByText("£4,800.00")).toBeVisible();
  await checkPage(page, "property", project.name);

  await page.getByRole("link", { name: "Edit Oak Road" }).click();
  await expect(page.getByLabel("Name")).toHaveValue("Oak Road");
  await page.getByRole("radio", { name: "All of it" }).check();
  await expect(page.getByText(/including quarters you’ve already sent/)).toBeVisible();
  await checkPage(page, "property-edit", project.name);

  await page.goto("/properties/new");
  await page.getByRole("button", { name: "Add property" }).click();
  await expect(page.getByRole("alert")).toBeFocused();
  await checkPage(page, "property-new-errors", project.name);
});
