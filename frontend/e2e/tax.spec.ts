import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { asSampleLandlord } from "./mockApi";

const SHOTS = process.env.SHOTS; // set to a folder to save screenshots for review

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

test("the tax year lists the four updates and the year so far", async ({ page }, { project }) => {
  await page.goto("/tax");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Tax year 2026-27");
  await expect(page.getByText("Sent 4 Aug")).toBeVisible();
  await expect(page.getByText("Ready to send")).toBeVisible();
  await expect(page.getByText("£10,183.60")).toBeVisible();
  await checkPage(page, "tax-year", project.name);

  await page
    .getByRole("link", { name: /quarter 2/i })
    .first()
    .click();
  await expect(page).toHaveURL(/\/tax\/2026\/q2$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Quarter 2");
});

test("a quarter shows what HMRC will receive and whether it can be sent", async ({ page }, {
  project,
}) => {
  await page.goto("/tax/2026/q2");
  await expect(page.getByRole("heading", { name: "Ready to send" })).toBeVisible();
  const panel = page.getByRole("complementary", { name: "Ready to send" });
  await expect(panel.getByText("Connected to HMRC")).toBeVisible();
  await expect(page.getByRole("link", { name: "Review and submit" })).toHaveAttribute(
    "href",
    "/tax/2026/q2/submit",
  );
  await expect(page.getByText("2,940.00").first()).toBeVisible();
  if (project.name === "phone") {
    await page.getByText("By property").click();
    await expect(page.getByRole("region", { name: "Oak Road" })).toContainText("4,800.00");
  } else {
    const table = page.getByRole("table");
    await expect(table.getByRole("columnheader", { name: "Oak Road 50%" })).toBeVisible();
    await expect(
      table.getByRole("row", { name: /Legal, management and other professional fees/ }),
    ).toContainText("432.00432.00864.00");
  }
  await checkPage(page, "quarter-2", project.name);

  await page.getByRole("link", { name: "Q1", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Sent to HMRC" })).toBeVisible();
  await expect(page.getByText("c5a1f1e2-7b7e-4b8a-9d3e-2f1a0c9b8e71")).toBeVisible();
  await checkPage(page, "quarter-1", project.name);

  await page.getByRole("link", { name: "Q3", exact: true }).click();
  await expect(page.getByRole("heading", { name: "In progress" })).toBeVisible();
  await checkPage(page, "quarter-3", project.name);
});
