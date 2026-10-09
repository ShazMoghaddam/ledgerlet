import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { asSampleLandlord } from "./mockApi";

const BOILER = "00000003-0000-0000-0000-00000000001d";

test.beforeEach(async ({ page }) => {
  await asSampleLandlord(page);
});

async function noSidewaysScroll(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBe(0);
}

async function accessible(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.help} (${v.nodes.length})`)).toEqual([]);
}

test("the list fits and has no accessibility problems", async ({ page }) => {
  await page.goto("/transactions");
  await expect(page.getByText("29 transactions")).toBeVisible();
  await noSidewaysScroll(page);
  await accessible(page);
});

test("opening a transaction: panel on a laptop, its own page otherwise", async ({ page }, {
  project,
}) => {
  await page.goto("/transactions");
  await page
    .getByRole("link", { name: /Boiler service/ })
    .first()
    .click();
  await expect(page).toHaveURL(new RegExp(`/transactions/${BOILER}$`));
  await expect(page.getByText("£96.00 out")).toBeVisible();
  if (project.name === "laptop") {
    await expect(page.getByRole("heading", { name: "Transactions", level: 1 })).toBeVisible();
  } else {
    await expect(page.getByRole("heading", { name: "Boiler service", level: 1 })).toBeVisible();
  }
  await noSidewaysScroll(page);
  await accessible(page);
});

test("filters on smaller screens open in a sheet and show as chips", async ({ page }, {
  project,
}) => {
  test.skip(project.name === "laptop", "inline filters on a laptop");
  await page.goto("/transactions");
  await page.getByRole("button", { name: "Filters" }).click();
  const sheet = page.getByRole("dialog", { name: "Filter transactions" });
  await expect(sheet).toBeVisible();
  await accessible(page);
  await sheet.getByLabel("Property").selectOption({ label: "Oak Road" });
  await sheet.getByRole("button", { name: "Show transactions" }).click();
  await expect(sheet).toBeHidden();
  await expect(page.getByRole("button", { name: "Remove filter: Oak Road" })).toBeVisible();
  await expect(page).toHaveURL(/property=/);
});

test("the add form explains problems accessibly, and fits", async ({ page }) => {
  await page.goto("/transactions/new");
  await page.getByRole("button", { name: "Add transaction" }).click();
  await expect(page.getByRole("alert")).toBeFocused();
  await noSidewaysScroll(page);
  await accessible(page);
  await page.getByRole("link", { name: "Enter a description, like “October rent”" }).click();
  await expect(page.getByLabel("Description")).toBeFocused();
});

test("delete asks first, and Escape backs out", async ({ page }) => {
  await page.goto(`/transactions/${BOILER}`);
  await page.getByRole("button", { name: "Delete" }).click();
  const dialog = page.getByRole("dialog", { name: "Delete this transaction?" });
  await expect(dialog).toBeVisible();
  await accessible(page);
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(page.getByRole("button", { name: "Delete" })).toBeFocused();
});
