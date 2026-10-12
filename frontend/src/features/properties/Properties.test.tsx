import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import properties from "../../test/fixtures/properties.json";
import { renderApp } from "../../test/renderApp";
import { server } from "../../test/server";

const [ELM, OAK] = properties as [(typeof properties)[0], (typeof properties)[0]];

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-09T10:00:00Z"));
});
afterEach(() => vi.useRealTimers());

describe("Properties", () => {
  it("lists each property with its share and this year's figures", async () => {
    renderApp("/properties", { width: 1440 });
    const table = await screen.findByRole("table", { name: /Your properties/ });
    const oak = within(table).getByRole("row", { name: /Oak Road/ });
    expect(await within(oak).findByText("4,800.00")).toBeInTheDocument();
    expect(oak).toHaveTextContent("Oak Road27 Oak Road, Leeds LS6 2ABYou own half4,800.00480.0013");
    expect(
      screen.getByText(/Figures are for tax year 2026-27 so far, at your share/),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Add a property" })).toHaveAttribute(
      "href",
      "/properties/new",
    );
  });

  it("on a phone, each property is one tappable row", async () => {
    renderApp("/properties", { width: 390 });
    const link = await screen.findByRole("link", { name: /Oak Road/ });
    expect(link).toHaveAttribute("href", `/properties/${OAK.id}`);
    expect(await within(link).findByText("4,800.00")).toBeInTheDocument();
  });

  it("keeps archived properties apart, saying their figures still count", async () => {
    server.use(
      http.get("/api/v1/properties", () =>
        HttpResponse.json([
          ELM,
          { ...OAK, is_archived: true, archived_at: "2026-09-30T12:00:00Z" },
        ]),
      ),
    );
    renderApp("/properties", { width: 1440 });
    const archived = await screen.findByRole("region", { name: "Archived" });
    expect(within(archived).getByRole("link", { name: "Oak Road" })).toBeInTheDocument();
    expect(archived).toHaveTextContent("Archived 30 September 2026");
    expect(archived).toHaveTextContent("still count in your tax figures");
  });

  it("asks a new landlord to add one", async () => {
    server.use(http.get("/api/v1/properties", () => HttpResponse.json([])));
    renderApp("/properties");
    expect(
      await screen.findByRole("heading", { name: "Add your first property" }),
    ).toBeInTheDocument();
  });
});

describe("One property", () => {
  it("shows its address, share, figures and recent transactions", async () => {
    renderApp(`/properties/${OAK.id}`);
    expect(await screen.findByRole("heading", { level: 1, name: "Oak Road" })).toBeVisible();
    expect(screen.getByText("27 Oak Road, Leeds, LS6 2AB")).toBeInTheDocument();
    expect(screen.getByText(/You own half \(50%\)/)).toBeInTheDocument();
    const year = screen.getByRole("region", { name: "Tax year 2026-27 so far" });
    expect(await within(year).findByText("£4,800.00")).toBeInTheDocument();
    expect(within(year).getByText("At your share, from 13 transactions.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Add transaction" })).toHaveAttribute(
      "href",
      `/transactions/new?property=${OAK.id}`,
    );
    expect(screen.getByRole("link", { name: "All transactions for Oak Road" })).toHaveAttribute(
      "href",
      `/transactions?property=${OAK.id}`,
    );
  });

  it("asks before archiving, and says nothing is lost", async () => {
    let archived = false;
    server.use(
      http.post(`/api/v1/properties/${OAK.id}/archive`, () => {
        archived = true;
        return HttpResponse.json({
          ...OAK,
          is_archived: true,
          archived_at: "2026-10-09T10:00:00Z",
        });
      }),
    );
    const user = userEvent.setup();
    renderApp(`/properties/${OAK.id}`);
    await user.click(await screen.findByRole("button", { name: "Archive this property" }));
    const dialog = screen.getByRole("dialog", { name: "Archive Oak Road?" });
    expect(dialog).toHaveTextContent("Its transactions stay");
    await user.click(within(dialog).getByRole("button", { name: "Archive" }));
    expect(archived).toBe(true);
  });

  it("an archived property can be restored, not edited", async () => {
    server.use(
      http.get(`/api/v1/properties/${OAK.id}`, () =>
        HttpResponse.json({ ...OAK, is_archived: true, archived_at: "2026-09-30T12:00:00Z" }),
      ),
    );
    renderApp(`/properties/${OAK.id}`);
    expect(await screen.findByText("Archived on 30 September 2026")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Restore this property" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Edit/ })).toBeNull();
  });
});

describe("Adding and editing", () => {
  it("checks every field, then adds the property with an exact share", async () => {
    let sent: unknown;
    server.use(
      http.post("/api/v1/properties", async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(OAK, { status: 201 });
      }),
    );
    const user = userEvent.setup();
    const { router } = renderApp("/properties/new");
    await user.click(await screen.findByRole("button", { name: "Add property" }));
    const summary = screen.getByRole("alert");
    expect(
      within(summary)
        .getAllByRole("link")
        .map((a) => a.textContent),
    ).toEqual([
      "Enter a name for the property, like “Flat 4”",
      "Enter the first line of the address",
      "Enter the town or city",
      "Enter the postcode",
      "Choose how much of it you own",
    ]);

    await user.type(screen.getByLabelText("Name"), "Flat 4");
    await user.type(screen.getByLabelText("Address line 1"), "4 High Street");
    await user.type(screen.getByLabelText("Town or city"), "York");
    await user.type(screen.getByLabelText("Postcode"), "12345");
    await user.click(screen.getByRole("radio", { name: "Another share" }));
    await user.type(screen.getByLabelText("Your share"), "33.333");
    await user.click(screen.getByRole("button", { name: "Add property" }));
    expect(screen.getByLabelText("Postcode")).toHaveAccessibleDescription(
      "Error: Enter a real UK postcode, like LS6 2AB",
    );
    expect(screen.getByLabelText("Your share")).toHaveAccessibleDescription(
      "Error: Enter your share as a number, like 50 or 33.33",
    );

    await user.clear(screen.getByLabelText("Postcode"));
    await user.type(screen.getByLabelText("Postcode"), "yo1 7hh");
    await user.clear(screen.getByLabelText("Your share"));
    await user.type(screen.getByLabelText("Your share"), "33.33");
    await user.click(screen.getByRole("button", { name: "Add property" }));

    expect(await screen.findByText("Property added.")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe(`/properties/${OAK.id}`);
    expect(sent).toEqual({
      nickname: "Flat 4",
      address_line_1: "4 High Street",
      address_line_2: null,
      town: "York",
      postcode: "yo1 7hh",
      ownership_percentage: "33.33",
    });
  });

  it("shows the API's reason when the address is already in use", async () => {
    server.use(
      http.post("/api/v1/properties", () =>
        HttpResponse.json(
          { detail: "You already have an active property at 27 Oak Road, LS6 2AB" },
          { status: 409 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderApp("/properties/new");
    await user.type(await screen.findByLabelText("Name"), "Oak again");
    await user.type(screen.getByLabelText("Address line 1"), "27 Oak Road");
    await user.type(screen.getByLabelText("Town or city"), "Leeds");
    await user.type(screen.getByLabelText("Postcode"), "LS6 2AB");
    await user.click(screen.getByRole("radio", { name: "All of it" }));
    await user.click(screen.getByRole("button", { name: "Add property" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "You already have an active property at 27 Oak Road, LS6 2AB",
    );
  });

  it("an edit sends only what changed, and warns that a new share changes sent figures", async () => {
    let sent: unknown;
    server.use(
      http.patch(`/api/v1/properties/${OAK.id}`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ ...OAK, ownership_percentage: "100.00" });
      }),
    );
    const user = userEvent.setup();
    renderApp(`/properties/${OAK.id}/edit`);
    expect(await screen.findByLabelText("Name")).toHaveValue("Oak Road");
    expect(screen.getByRole("radio", { name: "Half" })).toBeChecked();
    expect(screen.queryByText(/Changing your share/)).toBeNull();

    await user.click(screen.getByRole("radio", { name: "All of it" }));
    expect(screen.getByText(/including quarters you’ve already sent/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText("Changes saved.")).toBeInTheDocument();
    expect(sent).toEqual({ ownership_percentage: "100" });
  });
});
