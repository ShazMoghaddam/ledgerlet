import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "../../test/server";
import { renderApp } from "../../test/renderApp";

// The design boards are drawn for 9 October 2026; fix the clock there (Date only).
beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-09T10:00:00Z"));
});
afterEach(() => vi.useRealTimers());

const PHONE = 390;
const LAPTOP = 1440;

describe("Overview, with the sample landlord", () => {
  it("leads with the next step: quarter 2 is ready to send", async () => {
    renderApp("/", { width: LAPTOP });
    const heading = await screen.findByRole("heading", { level: 1 });
    expect(heading).toHaveTextContent("Quarter 2 is ready to send");
    expect(
      screen.getByText(
        /figures to 5 October are complete\. HMRC needs them by 7 November, in 29 days/,
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review and submit" })).toHaveAttribute(
      "href",
      "/tax/2026/q2/submit",
    );
  });

  it("states every quarter in words, not just on the ruler", async () => {
    renderApp("/", { width: LAPTOP });
    const year = await screen.findByRole("figure", { name: "Tax year 2026-27" });
    // What a screen reader hears: leave out the parts hidden from it (the phone's "Q").
    const spoken = (el: HTMLElement) => {
      const copy = el.cloneNode(true) as HTMLElement;
      copy.querySelectorAll("[aria-hidden='true']").forEach((n) => n.remove());
      return copy.textContent;
    };
    const items = within(year).getAllByRole("listitem").map(spoken);
    expect(items).toEqual([
      "Quarter 1Sent 4 Aug",
      "Quarter 2Ready to send, due 7 Nov",
      "Quarter 3In progress, ends 5 Jan",
      "Quarter 4Not started",
    ]);
  });

  it("shows the year-to-date statement with the design's figures", async () => {
    renderApp("/", { width: LAPTOP });
    const ytd = await screen.findByRole("region", { name: "Year to date" });
    expect(await within(ytd).findByText("£12,000.00")).toBeInTheDocument();
    expect(within(ytd).getByText("£1,816.40")).toBeInTheDocument();
    expect(within(ytd).getByText("£10,183.60")).toBeInTheDocument();
    expect(within(ytd).getByText(/Your share across both properties/)).toBeInTheDocument();
    expect(within(ytd).getByText("£2,940.00")).toBeInTheDocument();
  });

  it("lists recent transactions with separate In and Out columns on wide screens", async () => {
    renderApp("/", { width: LAPTOP });
    const table = await screen.findByRole("table", { name: /five most recent/ });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(5);
    const [boiler, rent] = rows.map((r) =>
      within(r)
        .getAllByRole("cell")
        .map((c) => c.textContent),
    );
    expect(boiler).toEqual(["3 Oct", "Boiler service Oak Road", "", "96.00"]);
    expect(rent).toEqual(["2 Oct", "October rent Elm Court", "1,200.00", ""]);
    expect(within(table).getByText("28 Sep")).toBeInTheDocument();
  });

  it("uses a signed list on a phone, with the landlord's share", async () => {
    renderApp("/", { width: PHONE });
    const recent = await screen.findByRole("region", { name: "Recent transactions" });
    expect(await within(recent).findByText("−96.00")).toBeInTheDocument();
    expect(within(recent).getByText("+1,200.00")).toBeInTheDocument();
    const [boiler] = within(recent).getAllByRole("listitem");
    expect(boiler).toHaveTextContent("Boiler service3 Oct, Oak Road. Your share £48.00\u221296.00");
    expect(within(recent).queryByRole("table")).not.toBeInTheDocument();
  });

  it("shows HMRC and property context", async () => {
    renderApp("/", { width: LAPTOP });
    const account = await screen.findByRole("complementary", { name: "Your account" });
    expect(await within(account).findByText("Connected")).toBeInTheDocument();
    expect(await within(account).findByText("OE****77A")).toBeInTheDocument();
    expect(within(account).getByText("You own all")).toBeInTheDocument();
    expect(within(account).getByText("You own half")).toBeInTheDocument();
  });
});

describe("Overview, other situations", () => {
  it("calls an unsent quarter past its deadline overdue", async () => {
    server.use(http.get("/api/v1/hmrc/submissions", () => HttpResponse.json([])));
    renderApp("/");
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent(
      "Quarter 1 is overdue",
    );
    expect(screen.getByText(/It was due on 7 August 2026/)).toBeInTheDocument();
  });

  it("still shows the figures when HMRC can't be reached; only what's sent is missing", async () => {
    server.use(
      http.get("/api/v1/hmrc/submissions", () =>
        HttpResponse.json({ detail: "The HMRC connection is not configured" }, { status: 503 }),
      ),
    );
    renderApp("/");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Couldn’t load what you’ve sent to HMRC. The HMRC connection is not configured",
    );
    const ytd = screen.getByRole("region", { name: "Year to date" });
    expect(await within(ytd).findByText("£10,183.60")).toBeInTheDocument();
    expect(await screen.findByRole("table", { name: /five most recent/ })).toBeInTheDocument();
  });

  it("asks a new landlord to add a property first", async () => {
    server.use(http.get("/api/v1/properties", () => HttpResponse.json([])));
    renderApp("/");
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent(
      "Add your first property",
    );
    expect(screen.getByRole("link", { name: "Add a property" })).toHaveAttribute(
      "href",
      "/properties/new",
    );
  });

  it("explains a failure and offers to try again, without losing the rest of the page", async () => {
    server.use(
      http.get("/api/v1/tax/obligations", () =>
        HttpResponse.json({ detail: "Something went wrong" }, { status: 500 }),
      ),
    );
    renderApp("/");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Couldn’t load the tax year. Something went wrong");
    expect(within(alert).getByRole("button", { name: "Try again" })).toBeInTheDocument();
    expect(await screen.findByText("You own half")).toBeInTheDocument();
  });
});

describe("Signing in", () => {
  it("sends a signed-out visitor to sign in, then back where they were going", async () => {
    vi.useRealTimers(); // user-event relies on real timers
    const user = userEvent.setup();
    const { router } = renderApp("/transactions", { signedIn: false });
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();

    await user.type(screen.getByLabelText("Development token"), "not a token");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(screen.getByText(/Paste the whole token/)).toBeInTheDocument();
    expect(screen.getByLabelText("Development token")).toHaveAttribute("aria-invalid", "true");

    await user.clear(screen.getByLabelText("Development token"));
    await user.type(screen.getByLabelText("Development token"), "aaa.bbb.ccc");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "Transactions" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/transactions");
  });

  it("signs out when the API says the sign-in has expired", async () => {
    server.use(
      http.get("/api/v1/properties", () => HttpResponse.json({ detail: "x" }, { status: 401 })),
    );
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("never follows a next link off the site", async () => {
    renderApp("/sign-in?next=//evil.example");
    // Already signed in, so it moves straight on: to the overview, not the other site.
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent(
      "Quarter 2 is ready to send",
    );
  });
});
