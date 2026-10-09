import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { asSampleLandlord } from "./mockApi";

const SAMPLE = "../scripts/samples/oak-road-statement.csv";

async function checkPage(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBe(0);
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.help} (${v.nodes.length})`)).toEqual([]);
}

test("importing a statement, step by step, at every size", async ({ page }) => {
  await asSampleLandlord(page);
  const uploads: string[] = [];
  page.on("request", (r) => {
    if (r.url().endsWith("/imports/preview")) uploads.push(r.postData() ?? "");
  });

  await page.goto("/transactions/import");
  await checkPage(page);
  await page.getByLabel("Property").selectOption({ label: "Oak Road" });
  await page.getByLabel("Statement file").setInputFiles(SAMPLE);
  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
  await expect(page.getByLabel("Amount", { exact: true })).toHaveValue("Amount");
  await checkPage(page);
  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page.getByText("3 of 5 rows selected")).toBeVisible();
  expect(uploads[0]).toContain('name="date_column"\r\n\r\nDate');
  expect(uploads[0]).toContain('name="amount_column"\r\n\r\nAmount');
  expect(uploads[0]).toContain(`filename="oak-road-statement.csv"`);
  await checkPage(page);

  // Pressing Import too early explains why, beside the button, and goes to the row.
  await page.getByRole("button", { name: "Import 3 transactions" }).click();
  await expect(page.getByText("2 rows need a category.")).toBeInViewport();
  await expect(page.getByLabel(/Category for HOMESERVE PLC/)).toBeFocused();
  await expect(page.getByLabel(/Category for HOMESERVE PLC/)).toBeInViewport();
  await checkPage(page);

  await page.getByLabel(/Category for HOMESERVE PLC/).selectOption("premises_running_costs");
  await page.getByLabel(/Category for COUNCIL TAX REFUND/).selectOption("other_income");
  await page.getByRole("button", { name: "Import 3 transactions" }).click();

  await expect(page.getByRole("heading", { level: 1, name: "Statement imported" })).toBeVisible();
  await expect(page.getByText("3 transactions added to Oak Road.")).toBeVisible();
  await checkPage(page);
});
