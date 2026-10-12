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

test("sending quarter 2, from the overview to HMRC's receipt", async ({ page }, { project }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Review and submit" }).click();

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Check your figures");
  await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
  await checkPage(page, "submit-1-check", project.name);
  await page.getByRole("button", { name: "These figures are right" }).click();

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("How should expenses be sent?");
  await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
  await checkPage(page, "submit-2-expenses", project.name);
  // The whole card is the target, not just the radio.
  const card = page.getByRole("radio", { name: "One total" }).locator("..");
  await card.click({ position: { x: 300, y: 30 } });
  await expect(page.getByRole("radio", { name: "One total" })).toBeChecked();
  await page.getByRole("radio", { name: "By category" }).check();
  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Confirm and send to HMRC");
  await expect(page.getByText("UK property, XDIS…6364")).toBeVisible();
  await page.getByRole("button", { name: "Send to HMRC" }).click();
  await expect(page.getByRole("checkbox")).toBeFocused();
  await checkPage(page, "submit-3-confirm", project.name);
  await page.getByText("I confirm these figures are correct").click();
  await page.getByRole("button", { name: "Send to HMRC" }).click();

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("HMRC has accepted your update");
  await expect(page.getByText("914a411c-ed26-4089-84cd-4bc7737d13ba")).toBeVisible();
  await checkPage(page, "submit-4-receipt", project.name);

  // Back can't land on the send step again.
  await page.goBack();
  await expect(page.getByRole("heading", { level: 1 })).not.toHaveText("Confirm and send to HMRC");

  // The quarter now shows as sent.
  await page.goto("/tax/2026/q2");
  await expect(page.getByRole("heading", { name: "Sent to HMRC" })).toBeVisible();
});

test("the HMRC connection page", async ({ page }, { project }) => {
  await page.goto("/settings/hmrc?hmrc=connected");
  await expect(page.getByText("Connected to HMRC.")).toBeVisible();
  await expect(page.getByText("OE****77A")).toBeVisible();
  await expect(page).toHaveURL(/\/settings\/hmrc$/);
  await checkPage(page, "hmrc-settings", project.name);
});

test("the settings page", async ({ page }, { project }) => {
  await page.goto("/settings");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Settings");
  await expect(page.getByText(/already sent HMRC an update for 2026-27/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Shaz Moghaddam" })).toBeVisible();
  await checkPage(page, "settings", project.name);
});
