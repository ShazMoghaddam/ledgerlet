import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { notConnected, taxpayer } from "../../test/fixtures/hmrc";
import { renderApp } from "../../test/renderApp";
import { server } from "../../test/server";

it("when connected, shows the connection and the details updates are filed under", async () => {
  renderApp("/settings/hmrc");
  expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("HMRC connection");
  expect(await screen.findByText("Connected")).toBeInTheDocument();
  expect(screen.getByText("4 August 2026")).toBeInTheDocument();
  expect(await screen.findByText("OE****77A")).toBeInTheDocument();
  expect(screen.getByText("XDIS36257256364")).toBeInTheDocument();
});

it("starts connecting, asking HMRC to come back to where the landlord was going", async () => {
  server.use(http.get("/api/v1/hmrc/connection", () => HttpResponse.json(notConnected)));
  let body: unknown;
  server.use(
    http.post("/api/v1/hmrc/connect", async ({ request }) => {
      body = await request.json();
      // Never resolve to a real page: the test only checks what was asked for.
      return HttpResponse.json({ detail: "stop here" }, { status: 503 });
    }),
  );
  const user = userEvent.setup();
  renderApp("/settings/hmrc?next=%2Ftax%2F2026%2Fq2");
  await user.click(await screen.findByRole("button", { name: "Connect to HMRC" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Couldn’t start connecting.");
  expect(body).toEqual({ return_to: "/settings/hmrc?next=%2Ftax%2F2026%2Fq2" });
});

it("ignores a next address that leads off the site", async () => {
  server.use(http.get("/api/v1/hmrc/connection", () => HttpResponse.json(notConnected)));
  let body: unknown;
  server.use(
    http.post("/api/v1/hmrc/connect", async ({ request }) => {
      body = await request.json();
      return HttpResponse.json({ detail: "stop here" }, { status: 503 });
    }),
  );
  const user = userEvent.setup();
  renderApp("/settings/hmrc?next=%2F%2Fevil.example");
  await user.click(await screen.findByRole("button", { name: "Connect to HMRC" }));
  await screen.findByRole("alert");
  expect(body).toEqual({ return_to: "/settings/hmrc" });
});

it("confirms a connection HMRC just approved, then tidies the address", async () => {
  const { router } = renderApp("/settings/hmrc?next=%2Ftax%2F2026%2Fq2&hmrc=connected");
  expect(await screen.findByText("Connected to HMRC.")).toBeInTheDocument();
  expect(router.state.location.search).toBe("?next=%2Ftax%2F2026%2Fq2");
  // Everything's in place, so it offers the way back.
  expect(await screen.findByRole("link", { name: "Continue where you left off" })).toHaveAttribute(
    "href",
    "/tax/2026/q2",
  );
});

it.each([
  ["declined", "You chose not to give LedgerLet access at HMRC."],
  ["other_browser", "in a different browser"],
  ["expired", "ran out"],
  ["anything-else", "Connecting to HMRC didn’t work."],
])("explains a failed connection (%s) in its own words", async (reason, text) => {
  renderApp(`/settings/hmrc?hmrc=error&reason=${reason}`);
  expect(await screen.findByRole("alert")).toHaveTextContent(text);
});

it("asks before disconnecting", async () => {
  let deleted = false;
  server.use(
    http.delete("/api/v1/hmrc/connection", () => {
      deleted = true;
      return new HttpResponse(null, { status: 204 });
    }),
  );
  const user = userEvent.setup();
  renderApp("/settings/hmrc");
  await user.click(await screen.findByRole("button", { name: "Disconnect" }));
  expect(screen.getByRole("dialog", { name: "Disconnect from HMRC?" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Stay connected" }));
  expect(deleted).toBe(false);
  await user.click(screen.getByRole("button", { name: "Disconnect" }));
  const dialog = screen.getByRole("dialog");
  await user.click(
    Array.from(dialog.querySelectorAll("button")).find((b) => b.textContent === "Disconnect")!,
  );
  expect(deleted).toBe(true);
});

it("saves a National Insurance number, explaining a wrong format", async () => {
  server.use(
    http.get("/api/v1/hmrc/taxpayer", () =>
      HttpResponse.json({ nino: null, uk_property_business_id: null }),
    ),
    http.put("/api/v1/hmrc/taxpayer", async ({ request }) => {
      const { nino } = (await request.json()) as { nino: string };
      return nino.startsWith("QQ")
        ? HttpResponse.json({ ...taxpayer, uk_property_business_id: null })
        : HttpResponse.json({ detail: [{ msg: "Value error" }] }, { status: 422 });
    }),
  );
  const user = userEvent.setup();
  renderApp("/settings/hmrc");
  const input = await screen.findByLabelText("National Insurance number");
  await user.click(screen.getByRole("button", { name: "Save" }));
  expect(screen.getByText("Enter your National Insurance number")).toBeInTheDocument();

  await user.type(input, "AB 12");
  await user.click(screen.getByRole("button", { name: "Save" }));
  expect(
    await screen.findByText(/Enter a National Insurance number in the right format/),
  ).toBeInTheDocument();
  expect(input).toHaveAttribute("aria-invalid", "true");
});

it("finds the property business at HMRC", async () => {
  let asked = false;
  server.use(
    http.get("/api/v1/hmrc/taxpayer", () =>
      HttpResponse.json(asked ? taxpayer : { nino: taxpayer.nino, uk_property_business_id: null }),
    ),
    http.post("/api/v1/hmrc/businesses/discover", () => {
      asked = true;
      return HttpResponse.json({
        businesses: [
          {
            business_id: taxpayer.uk_property_business_id,
            type_of_business: "uk-property",
            trading_name: null,
          },
        ],
        selected_business_id: taxpayer.uk_property_business_id,
      });
    }),
  );
  const user = userEvent.setup();
  renderApp("/settings/hmrc");
  await user.click(await screen.findByRole("button", { name: "Find my property business" }));
  expect(await screen.findByText("XDIS36257256364")).toBeInTheDocument();
});

it("says plainly when HMRC has no property business for the number", async () => {
  server.use(
    http.get("/api/v1/hmrc/taxpayer", () =>
      HttpResponse.json({ nino: taxpayer.nino, uk_property_business_id: null }),
    ),
    http.post("/api/v1/hmrc/businesses/discover", () =>
      HttpResponse.json({
        businesses: [
          { business_id: "XAIS1", type_of_business: "self-employment", trading_name: "Bakes" },
        ],
        selected_business_id: null,
      }),
    ),
  );
  const user = userEvent.setup();
  renderApp("/settings/hmrc");
  await user.click(await screen.findByRole("button", { name: "Find my property business" }));
  expect(await screen.findByText(/HMRC has no UK property business/)).toBeInTheDocument();
});
