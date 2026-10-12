import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { notConnected } from "../../test/fixtures/hmrc";
import summaryQ2 from "../../test/fixtures/summary-q2.json";
import { renderApp } from "../../test/renderApp";
import { server } from "../../test/server";

// The sample data is written for 9 October 2026: quarter 1 sent, quarter 2 ready.
beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-09T10:00:00Z"));
});
afterEach(() => vi.useRealTimers());

const PHONE = 390;
const LAPTOP = 1440;

describe("Tax year", () => {
  it("lists the four cumulative updates with what each needs", async () => {
    renderApp("/tax", { width: LAPTOP });
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("Tax year 2026-27");
    const table = await screen.findByRole("table", { name: /four quarterly updates/ });
    const rows = within(table)
      .getAllByRole("row")
      .slice(1)
      .map((r) => r.textContent);
    expect(rows).toEqual([
      "Quarter 16 Apr to 5 Jul7 AugSent 4 AugView quarter 1",
      "Quarter 26 Apr to 5 Oct7 NovReady to sendReview quarter 2",
      "Quarter 36 Apr to 5 Jan7 FebIn progressView quarter 3",
      "Quarter 46 Apr to 5 Apr 20277 MayNot started",
    ]);
    expect(within(table).getByRole("link", { name: "Review quarter 2" })).toHaveAttribute(
      "href",
      "/tax/2026/q2",
    );
  });

  it("shows the year so far and when the final declaration is due", async () => {
    renderApp("/tax");
    const ytd = await screen.findByRole("region", { name: "Year so far" });
    expect(within(ytd).getByText("6 April to today")).toBeInTheDocument();
    expect(await within(ytd).findByText("£10,183.60")).toBeInTheDocument();
    expect(screen.getByText(/final declaration, by 31 January 2028/)).toBeInTheDocument();
  });

  it("makes each quarter one tappable row on a phone", async () => {
    renderApp("/tax", { width: PHONE });
    const link = await screen.findByRole("link", { name: /Quarter 2/ });
    expect(link).toHaveAttribute("href", "/tax/2026/q2");
    expect(link).toHaveTextContent("Quarter 26 Apr to 5 Oct, due 7 NovReady to send");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    // Nothing to open yet for a quarter that hasn't started.
    expect(screen.queryByRole("link", { name: /Quarter 4/ })).not.toBeInTheDocument();
  });

  it("never calls a quarter overdue on a guess when HMRC can't be asked", async () => {
    server.use(
      http.get("/api/v1/hmrc/submissions", () =>
        HttpResponse.json({ detail: "The HMRC connection is not configured" }, { status: 503 }),
      ),
    );
    renderApp("/tax", { width: LAPTOP });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Couldn’t load what you’ve sent to HMRC",
    );
    const table = screen.getByRole("table");
    expect(within(table).getByText("Ended 5 Jul")).toBeInTheDocument();
    expect(within(table).queryByText(/Overdue|Sent/)).not.toBeInTheDocument();
  });

  it("explains a year before quarterly updates began", async () => {
    renderApp("/tax/2025");
    expect(await screen.findByText(/started with the 2026-27 tax year/)).toBeInTheDocument();
  });
});

describe("Quarter", () => {
  it("shows what HMRC will receive, by property, with the total that's sent", async () => {
    renderApp("/tax/2026/q2", { width: LAPTOP });
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("Quarter 2");
    expect(
      await screen.findByText(
        "6 April to 5 October 2026: the tax year so far. Due by 7 November 2026.",
      ),
    ).toBeInTheDocument();
    const table = await screen.findByRole("table", { name: /by property/ });
    const row = (name: RegExp) =>
      within(table).getByRole("row", { name }).textContent?.replace(/\s+/g, " ");
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((c) => c.textContent),
    ).toEqual(["HMRC category", "Elm Court", "Oak Road 50%", "Total"]);
    expect(row(/^Rental income/)).toBe("Rental income7,200.004,800.0012,000.00");
    expect(row(/^Repairs and maintenance/)).toBe("Repairs and maintenance592.0048.00640.00");
    expect(row(/^Total expenses/)).toBe("Total expenses1,336.40480.001,816.40");
    expect(row(/^Residential property finance costs/)).toBe(
      "Residential property finance costs2,940.000.002,940.00",
    );
    // Only what has something in it.
    expect(within(table).queryByText("Travel costs")).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "See the 29 transactions behind these figures" }),
    ).toHaveAttribute("href", "/transactions?period=2026-to-q2");
  });

  it("checks it can be sent, then offers to review and submit", async () => {
    renderApp("/tax/2026/q2");
    const panel = await screen.findByRole("complementary", { name: "Ready to send" });
    expect(await within(panel).findByText(/National Insurance number/)).toBeInTheDocument();
    const checks = within(panel).getAllByRole("listitem");
    expect(checks.map((c) => c.textContent)).toEqual([
      "Quarter ended 5 Oct",
      "Connected to HMRC",
      "National Insurance number and property business found",
      "Quarter 1 already sent",
    ]);
    expect(within(panel).getByRole("link", { name: "Review and submit" })).toHaveAttribute(
      "href",
      "/tax/2026/q2/submit",
    );
  });

  it("asks to connect to HMRC first when it isn't connected", async () => {
    server.use(http.get("/api/v1/hmrc/connection", () => HttpResponse.json(notConnected)));
    renderApp("/tax/2026/q2");
    const panel = await screen.findByRole("complementary", { name: "Ready to send" });
    expect(await within(panel).findByText("Not connected to HMRC")).toBeInTheDocument();
    expect(within(panel).getByRole("link", { name: "Connect to HMRC" })).toHaveAttribute(
      "href",
      "/settings/hmrc",
    );
    expect(within(panel).queryByRole("link", { name: "Review and submit" })).toBeNull();
  });

  it("shows when a sent quarter went, with HMRC's reference", async () => {
    renderApp("/tax/2026/q1");
    const panel = await screen.findByRole("complementary", { name: "Sent to HMRC" });
    expect(within(panel).getByText("4 August 2026")).toBeInTheDocument();
    expect(within(panel).getByText("c5a1f1e2-7b7e-4b8a-9d3e-2f1a0c9b8e71")).toBeInTheDocument();
    expect(
      await within(panel).findByRole("link", { name: "Send again with updated figures" }),
    ).toHaveAttribute("href", "/tax/2026/q1/submit");
    expect(screen.getByRole("heading", { level: 2, name: "Figures as they are now" }));
  });

  it("an unsent earlier quarter is covered by this update, and an overdue one says so", async () => {
    server.use(http.get("/api/v1/hmrc/submissions", () => HttpResponse.json([])));
    renderApp("/tax/2026/q2");
    const panel = await screen.findByRole("complementary", { name: "Ready to send" });
    expect(
      within(panel).getByText("Quarter 1 wasn’t sent. This update covers it too."),
    ).toBeInTheDocument();
  });

  it("calls an unsent past quarter overdue", async () => {
    server.use(http.get("/api/v1/hmrc/submissions", () => HttpResponse.json([])));
    renderApp("/tax/2026/q1");
    const panel = await screen.findByRole("complementary", { name: "Overdue" });
    expect(within(panel).getByText(/It was due on 7 August 2026/)).toBeInTheDocument();
  });

  it("a quarter still in progress can't be sent yet", async () => {
    renderApp("/tax/2026/q3");
    const panel = await screen.findByRole("complementary", { name: "In progress" });
    expect(panel).toHaveTextContent(/once the quarter ends on 5 January 2027/);
    expect(within(panel).getByRole("link", { name: "Add transaction" })).toBeInTheDocument();
    expect(within(panel).queryByRole("link", { name: "Review and submit" })).toBeNull();
  });

  it("on a phone, lists the figures and folds the properties away", async () => {
    renderApp("/tax/2026/q2", { width: PHONE });
    const figures = await screen.findByRole("region", { name: "What HMRC will receive" });
    expect(await within(figures).findByText("1,816.40")).toBeInTheDocument();
    expect(within(figures).queryByRole("table")).toBeNull();
    expect(within(figures).getByText("By property")).toBeInTheDocument();
    expect(within(figures).getByRole("region", { name: "Oak Road" })).toHaveTextContent(
      "Income4,800.00",
    );
  });

  it("says so when nothing's been recorded for the period", async () => {
    const empty = {
      ...summaryQ2,
      categories: summaryQ2.categories.map((c) => ({ ...c, amount: "0.00" })),
      properties: [],
    };
    server.use(http.get("/api/v1/tax/summary", () => HttpResponse.json(empty)));
    renderApp("/tax/2026/q2");
    expect(
      await screen.findByText(/Nothing recorded between 6 April 2026 and 5 October 2026 yet/),
    ).toBeInTheDocument();
  });

  it("treats a malformed address as not found", async () => {
    renderApp("/tax/2026/q7");
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("Page not found");
  });
});
