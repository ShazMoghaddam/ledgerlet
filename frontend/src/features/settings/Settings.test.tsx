import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { notConnected } from "../../test/fixtures/hmrc";
import me from "../../test/fixtures/me.json";
import { renderApp } from "../../test/renderApp";
import { server } from "../../test/server";

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-09T10:00:00Z"));
});
afterEach(() => vi.useRealTimers());

it("shows the account, the HMRC link and the credit", async () => {
  renderApp("/settings");
  expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("Settings");
  expect(
    await screen.findByText("A development sign-in, with no email address"),
  ).toBeInTheDocument();
  expect(await screen.findByRole("link", { name: "Manage HMRC connection" })).toHaveAttribute(
    "href",
    "/settings/hmrc",
  );
  const about = screen.getByRole("region", { name: "About LedgerLet" });
  expect(about).toHaveTextContent("It isn’t made or endorsed by HMRC.");
  expect(within(about).getByRole("link", { name: "Shaz Moghaddam" })).toHaveAttribute(
    "href",
    "https://shazmoghaddam.github.io/",
  );
  expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();
});

it("offers to connect when not connected", async () => {
  server.use(http.get("/api/v1/hmrc/connection", () => HttpResponse.json(notConnected)));
  renderApp("/settings");
  expect(await screen.findByRole("link", { name: "Connect to HMRC" })).toBeInTheDocument();
});

it("saves a name", async () => {
  let sent: unknown;
  server.use(
    http.patch("/api/v1/me", async ({ request }) => {
      sent = await request.json();
      return HttpResponse.json({ ...me, display_name: "Shaz" });
    }),
  );
  const user = userEvent.setup();
  renderApp("/settings");
  await user.type(await screen.findByLabelText("Your name"), "Shaz");
  await user.click(screen.getByRole("button", { name: "Save name" }));
  expect(await screen.findByText("Name saved.")).toBeInTheDocument();
  expect(sent).toEqual({ display_name: "Shaz" });
});

it("fixes the quarters once HMRC has an update this year", async () => {
  // The sample landlord sent quarter 1 on 4 August.
  renderApp("/settings");
  const quarters = await screen.findByRole("region", { name: "Your quarters" });
  expect(
    await within(quarters).findByText(/already sent HMRC an update for 2026-27/),
  ).toBeInTheDocument();
  expect(within(quarters).getByText("Standard: to the 5th")).toBeInTheDocument();
  expect(within(quarters).queryByRole("radio")).toBeNull();
});

it("lets the quarters change before anything is sent", async () => {
  let sent: unknown;
  server.use(
    http.get("/api/v1/hmrc/submissions", () => HttpResponse.json([])),
    http.patch("/api/v1/me", async ({ request }) => {
      sent = await request.json();
      return HttpResponse.json({ ...me, period_basis: "calendar" });
    }),
  );
  const user = userEvent.setup();
  renderApp("/settings");
  const calendar = await screen.findByRole("radio", { name: "Calendar: to the end of the month" });
  expect(screen.getByRole("radio", { name: "Standard: to the 5th" })).toBeChecked();
  expect(screen.getByRole("button", { name: "Save quarters" })).toBeDisabled();
  await user.click(calendar);
  await user.click(screen.getByRole("button", { name: "Save quarters" }));
  expect(await screen.findByText(/Quarters changed/)).toBeInTheDocument();
  expect(sent).toEqual({ period_basis: "calendar" });
});
