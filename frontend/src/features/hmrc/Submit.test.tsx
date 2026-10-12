import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { acceptedQ2, notConnected, refusedQ2, submissions } from "../../test/fixtures/hmrc";
import summaryQ2 from "../../test/fixtures/summary-q2.json";
import { renderApp } from "../../test/renderApp";
import { server } from "../../test/server";

// 9 October 2026: quarter 2 has ended and is ready to send. Only Date is faked, so
// user-event's timers still run.
beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-09T10:00:00Z"));
});
afterEach(() => vi.useRealTimers());

/** Record what's sent to HMRC, and let the history include it once it's accepted. */
function captureSend() {
  const sent: { body?: unknown; count: number } = { count: 0 };
  let history = submissions;
  server.use(
    http.post("/api/v1/hmrc/submissions", async ({ request }) => {
      sent.body = await request.json();
      sent.count += 1;
      history = [...submissions, acceptedQ2];
      return HttpResponse.json(acceptedQ2, { status: 201 });
    }),
    http.get("/api/v1/hmrc/submissions", () => HttpResponse.json(history)),
  );
  return sent;
}

it("checks, chooses, confirms and sends, then shows HMRC's receipt", async () => {
  const sent = captureSend();
  const user = userEvent.setup();
  const { router } = renderApp("/tax/2026/q2/submit");

  // Step 1: the figures.
  expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("Send quarter 2");
  expect(await screen.findByRole("heading", { name: "Check your figures" })).toBeInTheDocument();
  expect(screen.getByText("Step 1 of 3")).toBeInTheDocument();
  // The headline figures come first; the categories are folded away below them.
  expect(document.querySelector("main dl")).toHaveTextContent(
    "Income£12,000.00Expenses£1,816.40Residential finance costs£2,940.00",
  );
  expect(screen.getByRole("link", { name: "Review transactions" })).toHaveAttribute(
    "href",
    "/transactions?period=2026-to-q2",
  );
  await user.click(screen.getByRole("button", { name: "These figures are right" }));

  // Step 2: by category or one total. Income is under £90,000, so it's offered.
  expect(router.state.location.pathname).toBe("/tax/2026/q2/submit/expenses");
  expect(
    await screen.findByRole("group", { name: "How should expenses be sent?" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("radio", { name: "By category" })).toBeChecked();
  expect(screen.getByRole("radio", { name: "By category" })).toHaveAccessibleDescription(
    "3 categories, £1,816.40 in total. Matches your records exactly. Recommended.",
  );
  await user.click(screen.getByRole("button", { name: "Continue" }));

  // Step 3: exactly what HMRC will receive.
  expect(router.state.location.pathname).toBe("/tax/2026/q2/submit/confirm");
  expect(await screen.findByText("UK property, XDIS…6364")).toBeInTheDocument();
  expect(screen.getByText("by category")).toBeInTheDocument();
  expect(screen.getByLabelText("The data sent to HMRC")).toHaveTextContent('"periodAmount": 12000');

  // Sending without ticking the box is stopped, with the reason beside it.
  await user.click(screen.getByRole("button", { name: "Send to HMRC" }));
  expect(
    screen.getByText("Tick the box to confirm the figures before sending"),
  ).toBeInTheDocument();
  expect(screen.getByRole("checkbox")).toHaveFocus();
  expect(sent.count).toBe(0);

  await user.click(screen.getByRole("checkbox", { name: /I confirm these figures/ }));
  await user.click(screen.getByRole("button", { name: "Send to HMRC" }));

  expect(
    await screen.findByRole("heading", { name: "HMRC has accepted your update" }),
  ).toBeInTheDocument();
  expect(sent.body).toEqual({ tax_year: 2026, quarter: 2, consolidated_expenses: false });
  expect(sent.count).toBe(1);
  expect(router.state.location.pathname).toBe(`/tax/2026/q2/receipt/${acceptedQ2.id}`);
  expect(screen.getByText(/Sent 9 October 2026 at 10:42/)).toBeInTheDocument();
  expect(screen.getByText("914a411c-ed26-4089-84cd-4bc7737d13ba")).toBeInTheDocument();
  expect(screen.getByText(/Next: quarter 3 ends 5 Jan and is due 7 Feb/)).toBeInTheDocument();
});

it("can send expenses as one total, and the choice survives going back", async () => {
  const sent = captureSend();
  const user = userEvent.setup();
  const { router } = renderApp("/tax/2026/q2/submit/expenses");
  await user.click(await screen.findByRole("radio", { name: "One total" }));
  await user.click(screen.getByRole("button", { name: "Continue" }));
  expect(router.state.location.search).toBe("?expenses=total");
  expect(await screen.findByText("as one total")).toBeInTheDocument();
  expect(screen.getByLabelText("The data sent to HMRC")).toHaveTextContent(
    '"consolidatedExpenses": 1816.4',
  );

  await user.click(screen.getByRole("link", { name: "Back" }));
  expect(await screen.findByRole("radio", { name: "One total" })).toBeChecked();

  await user.click(screen.getByRole("button", { name: "Continue" }));
  await user.click(await screen.findByRole("checkbox", { name: /I confirm/ }));
  await user.click(screen.getByRole("button", { name: "Send to HMRC" }));
  await screen.findByRole("heading", { name: "HMRC has accepted your update" });
  expect(sent.body).toEqual({ tax_year: 2026, quarter: 2, consolidated_expenses: true });
});

it("skips the expenses choice when income is £90,000 or more", async () => {
  const user = userEvent.setup();
  server.use(
    http.get("/api/v1/tax/summary", () =>
      HttpResponse.json({
        ...summaryQ2,
        totals: { ...summaryQ2.totals, income: "90000.00" },
      }),
    ),
  );
  const { router } = renderApp("/tax/2026/q2/submit");
  expect(await screen.findByText("Step 1 of 2")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "These figures are right" }));
  expect(router.state.location.pathname).toBe("/tax/2026/q2/submit/confirm");
});

it("explains HMRC's refusal, and that the attempt is on record", async () => {
  const user = userEvent.setup();
  server.use(
    http.post("/api/v1/hmrc/submissions", () =>
      HttpResponse.json(
        {
          detail:
            "HMRC refused to accept this update: RULE_INCORRECT_OR_EMPTY_BODY_SUBMITTED: An empty or non-matching body was submitted",
        },
        { status: 502 },
      ),
    ),
  );
  renderApp("/tax/2026/q2/submit/confirm");
  await user.click(await screen.findByRole("checkbox", { name: /I confirm/ }));
  await user.click(screen.getByRole("button", { name: "Send to HMRC" }));
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("HMRC didn’t accept the update.");
  expect(alert).toHaveTextContent("RULE_INCORRECT_OR_EMPTY_BODY_SUBMITTED");
  expect(alert).toHaveTextContent("This attempt is kept in your submission history.");
  expect(screen.getByRole("button", { name: "Send to HMRC" })).toBeEnabled();
});

it("doesn't claim either way when the answer never arrived", async () => {
  const user = userEvent.setup();
  server.use(http.post("/api/v1/hmrc/submissions", () => HttpResponse.error()));
  renderApp("/tax/2026/q2/submit/confirm");
  await user.click(await screen.findByRole("checkbox", { name: /I confirm/ }));
  await user.click(screen.getByRole("button", { name: "Send to HMRC" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "LedgerLet couldn’t confirm whether it was sent.",
  );
});

it("won't start until it can be sent, and says what's missing", async () => {
  server.use(http.get("/api/v1/hmrc/connection", () => HttpResponse.json(notConnected)));
  renderApp("/tax/2026/q2/submit");
  expect(
    await screen.findByRole("heading", { name: "Quarter 2 can’t be sent yet" }),
  ).toBeInTheDocument();
  expect(await screen.findByText("Not connected to HMRC")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Connect to HMRC" })).toHaveAttribute(
    "href",
    "/settings/hmrc?next=%2Ftax%2F2026%2Fq2%2Fsubmit",
  );
});

it("a quarter still in progress can't be sent", async () => {
  renderApp("/tax/2026/q3/submit");
  expect(
    await screen.findByRole("heading", { name: "Quarter 3 can’t be sent yet" }),
  ).toBeInTheDocument();
  expect(screen.getByText(/once the quarter ends on 5 January 2027/)).toBeInTheDocument();
});

it("shows a refused attempt as refused, never as a receipt", async () => {
  server.use(
    http.get("/api/v1/hmrc/submissions", () => HttpResponse.json([...submissions, refusedQ2])),
  );
  renderApp(`/tax/2026/q2/receipt/${refusedQ2.id}`);
  expect(
    await screen.findByRole("heading", { name: "HMRC didn’t accept this update" }),
  ).toBeInTheDocument();
  expect(screen.getByText("An empty or non-matching body was submitted")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Try again" })).toHaveAttribute(
    "href",
    "/tax/2026/q2/submit",
  );
});

it("the receipt's figures are what was sent, and the reference can be copied", async () => {
  const user = userEvent.setup();
  server.use(
    http.get("/api/v1/hmrc/submissions", () => HttpResponse.json([...submissions, acceptedQ2])),
  );
  renderApp(`/tax/2026/q2/receipt/${acceptedQ2.id}`);
  const figures = await screen.findByText("£12,000.00");
  expect(figures).toBeInTheDocument();
  expect(screen.getByText("£1,816.40")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Copy reference" }));
  const statuses = screen.getAllByRole("status");
  expect(statuses.some((x) => /Copied\.|Couldn’t copy/.test(x.textContent ?? ""))).toBe(true);
  expect(within(screen.getByRole("main")).getByRole("button", { name: /Print/ })).toBeVisible();
});
