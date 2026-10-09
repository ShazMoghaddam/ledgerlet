import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import preview from "../../test/fixtures/import-preview.json";
import properties from "../../test/fixtures/properties.json";
import { server } from "../../test/server";
import { previewForm } from "./mutations";
import { renderApp } from "../../test/renderApp";

const OAK = properties.find((p) => p.nickname === "Oak Road")!.id;
const CSV = [
  "Date,Description,Amount,Balance",
  "01/10/2026,OCTOBER RENT J BLOGGS,1600.00,4210.55",
  "03/10/2026,Boiler service,-96.00,4114.55",
  "05/10/2026,Letting agent fee,-144.00,3970.55",
].join("\n");
const statement = () => new File([CSV], "oak-road.csv", { type: "text/csv" });

/**
 * Answer the preview and record what confirm receives. The preview's upload body isn't
 * read here: jsdom's FormData can't be read back through Node's fetch (it hangs), so
 * previewForm is tested on its own below, and the browser tests cover the real upload.
 */
function captureImport() {
  const sent: { previews: number; rows?: unknown } = { previews: 0 };
  server.use(
    http.post("/api/v1/properties/:id/imports/preview", ({ request }) => {
      sent.previews += 1;
      expect(request.headers.get("content-type")).toMatch(/^multipart\/form-data; boundary=/);
      return HttpResponse.json(preview);
    }),
    http.post("/api/v1/properties/:id/imports/confirm", async ({ request }) => {
      sent.rows = ((await request.json()) as { rows: unknown }).rows;
      return HttpResponse.json(
        { created: 3, skipped_already_imported: 0, transaction_ids: [] },
        { status: 201 },
      );
    }),
  );
  return sent;
}

async function toReview(user: ReturnType<typeof userEvent.setup>) {
  await user.upload(await screen.findByLabelText("Statement file"), statement());
  await user.click(screen.getByRole("button", { name: "Continue" }));
  await screen.findByRole("region", { name: "The start of your file" });
  await user.click(screen.getByRole("button", { name: "Continue" }));
  await screen.findByText(/rows selected/);
}

it("checks the property and file before going on", async () => {
  // applyAccept: false lets the test pick a PDF, as someone could by changing the picker's filter.
  const user = userEvent.setup({ applyAccept: false });
  renderApp("/transactions/import");
  await user.click(await screen.findByRole("button", { name: "Continue" }));
  expect(
    within(screen.getByRole("alert"))
      .getAllByRole("link")
      .map((a) => a.textContent),
  ).toEqual([
    "Choose the property the statement is for",
    "Choose a CSV file exported from your bank",
  ]);

  await user.upload(
    screen.getByLabelText("Statement file"),
    new File(["%PDF"], "statement.pdf", { type: "application/pdf" }),
  );
  await user.click(screen.getByRole("button", { name: "Continue" }));
  expect(screen.getByRole("alert")).toHaveTextContent("The file must be a CSV");
});

it("shows the landlord's own columns and guesses which is which", async () => {
  const user = userEvent.setup();
  renderApp(`/transactions/import?property=${OAK}`);
  await user.upload(await screen.findByLabelText("Statement file"), statement());
  await user.click(screen.getByRole("button", { name: "Continue" }));

  const sample = await screen.findByRole("region", { name: "The start of your file" });
  expect(
    within(sample)
      .getAllByRole("columnheader")
      .map((h) => h.textContent),
  ).toEqual(["Date", "Description", "Amount", "Balance"]);
  expect(screen.getByLabelText("Date")).toHaveValue("Date");
  expect(screen.getByLabelText("Description")).toHaveValue("Description");
  expect(screen.getByLabelText("Amount")).toHaveValue("Amount");
  expect(screen.getByLabelText("Dates look like")).toHaveValue("%d/%m/%Y");
  expect(screen.getByRole("listitem", { current: "step" })).toHaveTextContent("Match the columns");
});

it("previews, lets the landlord categorise, and imports exactly what they kept", async () => {
  const sent = captureImport();
  const user = userEvent.setup();
  renderApp(`/transactions/import?property=${OAK}`);
  await toReview(user);

  expect(sent.previews).toBe(1);

  // New rows start ticked, possible duplicates unticked, unreadable rows can't be ticked.
  const box = (name: RegExp) => screen.getByRole("checkbox", { name });
  expect(box(/Import Letting agent fee/)).toBeChecked();
  expect(box(/Import OCTOBER RENT J BLOGGS/)).not.toBeChecked();
  expect(box(/Import Boiler service/)).not.toBeChecked();
  expect(box(/Import Smoke alarm batteries/)).toBeDisabled();
  expect(screen.getByText(/Amount 'twelve' isn't a number\. Correct it/)).toBeInTheDocument();

  // Categories used last time are filled in.
  expect(screen.getByLabelText(/Category for Letting agent fee/)).toHaveValue("professional_fees");

  // Two ticked rows have no category yet.
  await user.click(screen.getByRole("button", { name: "Import 3 transactions" }));
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Choose a category for 2 rows you’re importing",
  );
  expect(sent.rows).toBeUndefined();

  // Fill one in bulk (money out), the other by hand (money in).
  await user.selectOptions(
    screen.getByLabelText("Fill in rows without a category"),
    "premises_running_costs",
  );
  await user.click(screen.getByRole("button", { name: "Apply" }));
  expect(screen.getByLabelText(/Category for HOMESERVE PLC/)).toHaveValue("premises_running_costs");
  await user.selectOptions(
    screen.getByLabelText(/Category for COUNCIL TAX REFUND/),
    "other_income",
  );
  await user.click(screen.getByRole("button", { name: "Import 3 transactions" }));

  expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("Statement imported");
  expect(screen.getByRole("status")).toHaveTextContent("3 transactions added to Oak Road.");
  expect(screen.getByRole("link", { name: "See Oak Road transactions" })).toHaveAttribute(
    "href",
    `/transactions?property=${OAK}`,
  );
  const fp = (description: string) =>
    preview.rows.find((r) => r.description === description)!.fingerprint;
  expect(sent.rows).toEqual([
    {
      fingerprint: fp("Letting agent fee"),
      transaction_date: "2026-10-05",
      description: "Letting agent fee",
      amount: "144.00",
      direction: "out",
      category: "professional_fees",
    },
    {
      fingerprint: fp("HOMESERVE PLC"),
      transaction_date: "2026-10-06",
      description: "HOMESERVE PLC",
      amount: "18.50",
      direction: "out",
      category: "premises_running_costs",
    },
    {
      fingerprint: fp("COUNCIL TAX REFUND"),
      transaction_date: "2026-10-07",
      description: "COUNCIL TAX REFUND",
      amount: "42.00",
      direction: "in",
      category: "other_income",
    },
  ]);
});

it("a possible duplicate can still be imported if the landlord ticks it", async () => {
  const sent = captureImport();
  const user = userEvent.setup();
  renderApp(`/transactions/import?property=${OAK}`);
  await toReview(user);
  await user.click(screen.getByRole("checkbox", { name: /Import Boiler service/ }));
  for (const name of [
    /Import Letting agent fee/,
    /Import HOMESERVE PLC/,
    /Import COUNCIL TAX REFUND/,
  ]) {
    await user.click(screen.getByRole("checkbox", { name }));
  }
  await user.click(screen.getByRole("button", { name: "Import 1 transaction" }));
  await screen.findByText("Statement imported");
  expect(
    (sent.rows as { description: string; category: string }[]).map((r) => [
      r.description,
      r.category,
    ]),
  ).toEqual([["Boiler service", "repairs_and_maintenance"]]);
});

it("explains when the statement can't be read with the chosen columns", async () => {
  server.use(
    http.post("/api/v1/properties/:id/imports/preview", () =>
      HttpResponse.json({ detail: "Column 'Date' was not found in the file" }, { status: 400 }),
    ),
  );
  const user = userEvent.setup();
  renderApp(`/transactions/import?property=${OAK}`);
  await user.upload(await screen.findByLabelText("Statement file"), statement());
  await user.click(screen.getByRole("button", { name: "Continue" }));
  await screen.findByRole("region", { name: "The start of your file" });
  await user.click(screen.getByRole("button", { name: "Continue" }));
  await waitFor(() =>
    expect(screen.getByRole("alert")).toHaveTextContent(
      "The statement couldn’t be read with these settings: Column 'Date' was not found in the file",
    ),
  );
});

describe("previewForm", () => {
  const base = {
    dateColumn: "Date",
    descriptionColumn: "Details",
    amountColumn: "Amount",
    paidInColumn: "",
    paidOutColumn: "",
    dateFormat: "%d/%m/%Y",
    invertSign: true,
  };

  it("sends one signed amount column", () => {
    const form = previewForm(statement(), { ...base, amountStyle: "signed" });
    expect(form.get("file")).toBeInstanceOf(File);
    expect(Object.fromEntries([...form.entries()].filter(([k]) => k !== "file"))).toEqual({
      date_column: "Date",
      description_column: "Details",
      amount_column: "Amount",
      invert_sign: "true",
      date_format: "%d/%m/%Y",
    });
  });

  it("or separate money in and out columns, and nothing else about amounts", () => {
    const form = previewForm(statement(), {
      ...base,
      amountStyle: "split",
      paidInColumn: "Paid in",
      paidOutColumn: "Paid out",
    });
    expect(form.get("paid_in_column")).toBe("Paid in");
    expect(form.get("paid_out_column")).toBe("Paid out");
    expect(form.has("amount_column")).toBe(false);
    expect(form.has("invert_sign")).toBe(false);
  });
});

it("says plainly when there's nothing new to import", async () => {
  server.use(
    http.post("/api/v1/properties/:id/imports/preview", () =>
      HttpResponse.json({
        ...preview,
        new: 0,
        possible_duplicates: 0,
        already_imported: 5,
        rows: preview.rows.map((r) =>
          r.status === "invalid" ? r : { ...r, status: "already_imported" },
        ),
      }),
    ),
  );
  const user = userEvent.setup();
  renderApp(`/transactions/import?property=${OAK}`);
  await toReview(user);
  expect(screen.getByText(/Nothing new to import/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Import 0 transactions" })).toBeDisabled();
});
