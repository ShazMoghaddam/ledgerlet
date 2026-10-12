/**
 * A stand-in API for component tests. Each handler answers with a real response
 * exported from the backend (src/test/fixtures, see scripts/export_frontend_contract.py),
 * so tests see exactly what the app will see.
 */
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

import categories from "./fixtures/categories.json";
import { acceptedQ2, connection, submissions, taxpayer } from "./fixtures/hmrc";
import me from "./fixtures/me.json";
import obligations from "./fixtures/obligations.json";
import properties from "./fixtures/properties.json";
import summaryQ1 from "./fixtures/summary-q1.json";
import summaryQ2 from "./fixtures/summary-q2.json";
import summaryQ3 from "./fixtures/summary-q3.json";
import recent from "./fixtures/transactions-recent.json";
import page1 from "./fixtures/transactions-page-1.json";
import boiler from "./fixtures/transaction-boiler.json";
import previewQ2 from "./fixtures/submission-preview-q2.json";
import previewQ2Total from "./fixtures/submission-preview-q2-total.json";

const summaries: Record<string, unknown> = { "1": summaryQ1, "2": summaryQ2, "3": summaryQ3 };

export const handlers = [
  http.get("/api/v1/me", () => HttpResponse.json(me)),
  http.get("/api/v1/properties", () => HttpResponse.json(properties)),
  http.get("/api/v1/tax/obligations", () => HttpResponse.json(obligations)),
  http.get("/api/v1/tax/summary", ({ request }) => {
    const quarter = new URL(request.url).searchParams.get("quarter") ?? "";
    const summary = summaries[quarter];
    return summary ? HttpResponse.json(summary) : new HttpResponse(null, { status: 404 });
  }),
  http.get("/api/v1/transactions/categories", () => HttpResponse.json(categories)),
  http.get("/api/v1/transactions", ({ request }) => {
    const limit = Number(new URL(request.url).searchParams.get("limit") ?? 50);
    return HttpResponse.json(limit <= 5 ? recent : page1);
  }),
  http.get("/api/v1/transactions/:id", ({ params }) =>
    params.id === boiler.id
      ? HttpResponse.json(boiler)
      : HttpResponse.json({ detail: "Transaction not found" }, { status: 404 }),
  ),
  http.get("/api/v1/hmrc/connection", () => HttpResponse.json(connection)),
  http.get("/api/v1/hmrc/taxpayer", () => HttpResponse.json(taxpayer)),
  http.get("/api/v1/hmrc/submissions", () => HttpResponse.json(submissions)),
  http.post("/api/v1/hmrc/submissions/preview", async ({ request }) => {
    const body = (await request.json()) as { consolidated_expenses?: boolean };
    return HttpResponse.json(body.consolidated_expenses ? previewQ2Total : previewQ2);
  }),
  http.post("/api/v1/hmrc/submissions", () => HttpResponse.json(acceptedQ2, { status: 201 })),
  http.post("/api/v1/hmrc/connect", () =>
    HttpResponse.json({ authorize_url: "https://test-www.tax.service.gov.uk/oauth/authorize?x=1" }),
  ),
  http.delete("/api/v1/hmrc/connection", () => new HttpResponse(null, { status: 204 })),
  http.put("/api/v1/hmrc/taxpayer", () => HttpResponse.json(taxpayer)),
  http.put("/api/v1/hmrc/taxpayer/business", () => HttpResponse.json(taxpayer)),
  http.post("/api/v1/hmrc/businesses/discover", () =>
    HttpResponse.json({
      businesses: [
        {
          business_id: taxpayer.uk_property_business_id,
          type_of_business: "uk-property",
          trading_name: null,
        },
      ],
      selected_business_id: taxpayer.uk_property_business_id,
    }),
  ),
];

export const server = setupServer(...handlers);
