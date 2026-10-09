import type { Page } from "@playwright/test";

import categories from "../src/test/fixtures/categories.json" with { type: "json" };
import me from "../src/test/fixtures/me.json" with { type: "json" };
import obligations from "../src/test/fixtures/obligations.json" with { type: "json" };
import properties from "../src/test/fixtures/properties.json" with { type: "json" };
import summaryQ1 from "../src/test/fixtures/summary-q1.json" with { type: "json" };
import summaryQ2 from "../src/test/fixtures/summary-q2.json" with { type: "json" };
import summaryQ3 from "../src/test/fixtures/summary-q3.json" with { type: "json" };
import recent from "../src/test/fixtures/transactions-recent.json" with { type: "json" };
import page1 from "../src/test/fixtures/transactions-page-1.json" with { type: "json" };
import boiler from "../src/test/fixtures/transaction-boiler.json" with { type: "json" };

const connection = {
  connected: true,
  connected_at: "2026-08-04T09:12:00Z",
  access_token_expires_at: "2026-10-09T13:00:00Z",
  scope: "read:self-assessment write:self-assessment",
};
const taxpayer = { nino: "OE****77A", uk_property_business_id: "XDIS36257256364" };
const submissions = [
  {
    id: "00000004-0000-0000-0000-000000000001",
    business_id: "XDIS36257256364",
    tax_year: 2026,
    quarter: 1,
    period_start: "2026-04-06",
    period_end: "2026-07-05",
    consolidated_expenses: false,
    succeeded: true,
    status_code: 204,
    hmrc_correlation_id: "c5a1f1e2-7b7e-4b8a-9d3e-2f1a0c9b8e71",
    submitted_at: "2026-08-04T10:42:00Z",
    request_body: {},
    response_body: {},
  },
];

const summaries: Record<string, unknown> = { "1": summaryQ1, "2": summaryQ2, "3": summaryQ3 };

/** Sign in, fix the date at 9 October 2026, and answer the API as the sample landlord. */
export async function asSampleLandlord(page: Page) {
  await page.clock.setFixedTime(new Date("2026-10-09T10:00:00Z"));
  await page.addInitScript(() => sessionStorage.setItem("ledgerlet.token", "aaa.bbb.ccc"));
  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace("/api/v1", "");
    const json = (body: unknown) => route.fulfill({ json: body });
    switch (path) {
      case "/me":
        return json(me);
      case "/properties":
        return json(properties);
      case "/tax/obligations":
        return json(obligations);
      case "/tax/summary":
        return json(summaries[url.searchParams.get("quarter") ?? ""]);
      case "/transactions":
        return json(Number(url.searchParams.get("limit")) <= 5 ? recent : page1);
      case "/transactions/categories":
        return json(categories);
      case "/hmrc/connection":
        return json(connection);
      case "/hmrc/taxpayer":
        return json(taxpayer);
      case "/hmrc/submissions":
        return json(submissions);
      default:
        if (path === `/transactions/${boiler.id}`) return json(boiler);
        return route.fulfill({ status: 404, json: { detail: `No mock for ${path}` } });
    }
  });
}
