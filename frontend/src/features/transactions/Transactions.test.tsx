import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import boiler from "../../test/fixtures/transaction-boiler.json";
import page1 from "../../test/fixtures/transactions-page-1.json";
import properties from "../../test/fixtures/properties.json";
import { server } from "../../test/server";
import { renderApp } from "../../test/renderApp";

const PHONE = 390;
const TABLET = 834;
const LAPTOP = 1440;
const OAK = properties.find((p) => p.nickname === "Oak Road")!.id;

/** Record the query of every list request, to check filters reach the API. */
function captureListRequests() {
  const seen: URLSearchParams[] = [];
  server.use(
    http.get("/api/v1/transactions", ({ request }) => {
      seen.push(new URL(request.url).searchParams);
      return HttpResponse.json(page1);
    }),
  );
  return seen;
}

describe("the transactions list", () => {
  it("is a statement with property and category columns on a laptop", async () => {
    renderApp("/transactions", { width: LAPTOP });
    const table = await screen.findByRole("table", { name: /newest first/ });
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((h) => h.textContent),
    ).toEqual(["Date", "Description", "Property", "Category", "In", "Out"]);
    expect(screen.getByText(/29 transactions\. At your share: money in/)).toHaveTextContent(
      "29 transactions. At your share: money in £12,000.00, money out £4,756.40.",
    );
    expect(within(table).getByRole("link", { name: "Boiler service" })).toHaveAttribute(
      "href",
      `/transactions/${boiler.id}`,
    );
  });

  it("asks the API for this tax year by default", async () => {
    const seen = captureListRequests();
    renderApp("/transactions");
    await screen.findByRole("table");
    expect(Object.fromEntries(seen.at(-1)!)).toMatchObject({
      date_from: "2026-04-06",
      date_to: "2027-04-05",
      limit: "50",
      offset: "0",
    });
  });

  it("puts filters in the URL and sends them to the API", async () => {
    const seen = captureListRequests();
    const user = userEvent.setup();
    const { router } = renderApp("/transactions", { width: LAPTOP });
    await screen.findByRole("table");

    await user.selectOptions(screen.getByLabelText("Property"), "Oak Road");
    await user.selectOptions(screen.getByLabelText("Period"), "2026-q2");

    await waitFor(() =>
      expect(router.state.location.search).toBe(`?property=${OAK}&period=2026-q2`),
    );
    expect(Object.fromEntries(seen.at(-1)!)).toMatchObject({
      property_id: OAK,
      date_from: "2026-07-06",
      date_to: "2026-10-05",
    });
  });

  it("searches as you type, after a pause", async () => {
    const seen = captureListRequests();
    const user = userEvent.setup();
    const { router } = renderApp("/transactions");
    await screen.findByRole("table");
    await user.type(screen.getByRole("searchbox", { name: "Search transactions" }), "boiler");
    await waitFor(() => expect(router.state.location.search).toBe("?q=boiler"));
    await waitFor(() => expect(seen.at(-1)?.get("q")).toBe("boiler"));
  });

  it("on a tablet, filters sit behind a button and show as removable chips", async () => {
    const user = userEvent.setup();
    const { router } = renderApp(`/transactions?property=${OAK}`, { width: TABLET });
    await screen.findByRole("table");
    expect(screen.getByRole("button", { name: "Filters (1)" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Remove filter: Oak Road" }));
    await waitFor(() => expect(router.state.location.search).toBe(""));
  });

  it("on a tablet, property and category sit under the description", async () => {
    renderApp("/transactions", { width: TABLET });
    const table = await screen.findByRole("table");
    expect(within(table).getAllByRole("columnheader")).toHaveLength(4);
    const [first] = within(table).getAllByRole("row").slice(1);
    expect(first).toHaveTextContent("Oak Road, repairs. Your share £48.00");
  });

  it("on a phone, it's a list grouped by month with signed amounts", async () => {
    renderApp("/transactions", { width: PHONE });
    const october = await screen.findByRole("region", { name: "October 2026" });
    expect(within(october).getAllByRole("link")[0]).toHaveTextContent(
      "Boiler service3 Oct, Oak Road. Your share £48.00−96.00",
    );
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("says when nothing matches, and how to clear the filters", async () => {
    server.use(
      http.get("/api/v1/transactions", () =>
        HttpResponse.json({ ...page1, items: [], total: 0, money_in: "0.00", money_out: "0.00" }),
      ),
    );
    renderApp("/transactions?q=zzz");
    expect(await screen.findByText("No transactions match these filters.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Clear filters" })).toHaveAttribute(
      "href",
      "/transactions",
    );
  });
});

describe("one transaction", () => {
  it("opens beside the list on a laptop, with the row marked", async () => {
    renderApp(`/transactions/${boiler.id}`, { width: LAPTOP });
    const panel = await screen.findByRole("complementary", { name: "Boiler service" });
    expect(within(panel).getByText("£96.00 out")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Boiler service" })).toHaveAttribute(
      "aria-current",
      "true",
    );
  });

  it("gets the whole screen on a phone, with what matters for tax", async () => {
    renderApp(`/transactions/${boiler.id}`, { width: PHONE });
    expect(
      await screen.findByRole("heading", { level: 1, name: "Boiler service" }),
    ).toBeInTheDocument();
    const facts = Object.fromEntries(
      screen.getAllByRole("term").map((dt) => [dt.textContent, dt.nextElementSibling?.textContent]),
    );
    expect(facts).toMatchObject({
      "Amount paid": "£96.00 out",
      "Your share (50%)": "£48.00",
      Category: "Repairs and maintenance",
      Source: "Added by hand",
    });
    await waitFor(() =>
      expect(screen.getByText("Quarter 2 2026-27, not sent yet")).toBeInTheDocument(),
    );
    expect(screen.getByRole("link", { name: "All transactions" })).toHaveAttribute(
      "href",
      "/transactions",
    );
  });

  it("asks before deleting, then goes back to the list and says so", async () => {
    let deleted = false;
    server.use(
      http.delete(`/api/v1/transactions/${boiler.id}`, () => {
        deleted = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = userEvent.setup();
    const { router } = renderApp(`/transactions/${boiler.id}`, { width: PHONE });
    await user.click(await screen.findByRole("button", { name: "Delete" }));
    const dialog = screen.getByRole("dialog", { name: "Delete this transaction?" });
    expect(dialog).toHaveTextContent(
      "Boiler service, £96.00 out on 3 October 2026. This can’t be undone.",
    );
    expect(deleted).toBe(false);

    await user.click(within(dialog).getByRole("button", { name: "Delete transaction" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/transactions"));
    expect(deleted).toBe(true);
    expect(await screen.findByRole("status")).toHaveTextContent("Transaction deleted.");
  });

  it("can't be changed once its tax year is finalised", async () => {
    server.use(
      http.get(`/api/v1/transactions/${boiler.id}`, () =>
        HttpResponse.json({ ...boiler, is_locked: true, locked_at: "2027-05-01T10:00:00Z" }),
      ),
    );
    renderApp(`/transactions/${boiler.id}`, { width: PHONE });
    expect(await screen.findByText(/already finalised with HMRC/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });
});

describe("adding and editing", () => {
  it("lists every problem at once, linked to its field", async () => {
    const user = userEvent.setup();
    renderApp("/transactions/new");
    await user.clear(await screen.findByLabelText("Date"));
    await user.click(screen.getByRole("button", { name: "Add transaction" }));

    const summary = screen.getByRole("alert");
    expect(
      within(summary)
        .getAllByRole("link")
        .map((a) => a.textContent),
    ).toEqual([
      "Choose the property this is for",
      "Choose money in or money out",
      "Enter the date",
      "Enter a description, like “October rent”",
      "Enter an amount, like 96.00",
    ]);
    expect(summary).toHaveFocus();
    expect(screen.getByLabelText("Description")).toHaveAttribute("aria-invalid", "true");
  });

  it("sends exactly what the API expects, then shows the new transaction", async () => {
    let body: unknown;
    let path = "";
    server.use(
      http.post("/api/v1/properties/:id/transactions", async ({ request, params }) => {
        body = await request.json();
        path = String(params.id);
        return HttpResponse.json(
          { ...boiler, id: "00000003-0000-0000-0000-0000000000ff" },
          { status: 201 },
        );
      }),
    );
    const user = userEvent.setup();
    const { router } = renderApp("/transactions/new");

    await user.selectOptions(await screen.findByLabelText("Property"), "Oak Road");
    await user.click(screen.getByLabelText("Money out"));
    await user.selectOptions(screen.getByLabelText("Category"), "repairs_and_maintenance");
    expect(screen.getByText(/keep the property as it was/)).toBeInTheDocument();
    await user.clear(screen.getByLabelText("Date"));
    await user.type(screen.getByLabelText("Date"), "2026-10-03");
    await user.type(screen.getByLabelText("Description"), "  Boiler service ");
    await user.type(screen.getByLabelText("Amount"), "£1,234.5");
    expect(screen.getByText(/Your 50% share is worked out for you/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Add transaction" }));

    await waitFor(() =>
      expect(router.state.location.pathname).toBe(
        "/transactions/00000003-0000-0000-0000-0000000000ff",
      ),
    );
    expect(path).toBe(OAK);
    expect(body).toEqual({
      transaction_date: "2026-10-03",
      category: "repairs_and_maintenance",
      description: "Boiler service",
      amount: "1234.50",
    });
  });

  it("only offers categories for the chosen direction", async () => {
    const user = userEvent.setup();
    renderApp("/transactions/new");
    await user.click(await screen.findByLabelText("Money in"));
    const options = within(screen.getByLabelText("Category"))
      .getAllByRole("option")
      .map((o) => o.textContent);
    expect(options).toContain("Rental income");
    expect(options).not.toContain("Repairs and maintenance");
  });

  it("shows the API's reason when saving fails", async () => {
    server.use(
      http.post("/api/v1/properties/:id/transactions", () =>
        HttpResponse.json(
          { detail: "Can't add transactions to an archived property. Restore it first." },
          { status: 409 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderApp("/transactions/new");
    await user.selectOptions(await screen.findByLabelText("Property"), "Elm Court");
    await user.click(screen.getByLabelText("Money in"));
    await user.selectOptions(screen.getByLabelText("Category"), "rental_income");
    await user.type(screen.getByLabelText("Description"), "Rent");
    await user.type(screen.getByLabelText("Amount"), "1200");
    await user.click(screen.getByRole("button", { name: "Add transaction" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Restore it first.");
  });

  it("edits in place, keeping the property", async () => {
    let body: unknown;
    server.use(
      http.patch(`/api/v1/transactions/${boiler.id}`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(boiler);
      }),
    );
    const user = userEvent.setup();
    const { router } = renderApp(`/transactions/${boiler.id}/edit`, { width: PHONE });
    const amount = await screen.findByLabelText("Amount");
    expect(amount).toHaveValue("96.00");
    expect(
      screen.getByText(/Oak Road\. A transaction stays with its property/),
    ).toBeInTheDocument();
    await user.clear(amount);
    await user.type(amount, "110");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => expect(router.state.location.pathname).toBe(`/transactions/${boiler.id}`));
    expect(body).toEqual({
      transaction_date: "2026-10-03",
      category: "repairs_and_maintenance",
      description: "Boiler service",
      amount: "110.00",
    });
    expect(await screen.findByRole("status")).toHaveTextContent("Changes saved.");
  });
});

it("the sign-in page credits who built it", async () => {
  renderApp("/sign-in", { signedIn: false });
  const link = await screen.findByRole("link", { name: "Shaz Moghaddam" });
  expect(link).toHaveAttribute("href", "https://shazmoghaddam.github.io/");
  expect(link.closest("footer")).toHaveTextContent(
    "© 2026 LedgerLet. Built in London by Shaz Moghaddam.",
  );
});
