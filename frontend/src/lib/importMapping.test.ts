import { glimpse, splitCsvLine } from "./csv";
import { guessMapping } from "./importMapping";

describe("reading the top of a CSV", () => {
  it("keeps quoted commas inside one field", () => {
    expect(splitCsvLine('01/10/2026,"SMITH, J ""RENT""",850.00')).toEqual([
      "01/10/2026",
      'SMITH, J "RENT"',
      "850.00",
    ]);
  });

  it("finds the header and a few rows, skipping Excel's byte-order mark and blank lines", () => {
    const g = glimpse(
      "\uFEFFDate,Description,Amount\r\n\r\n01/10/2026,RENT,850\r\n02/10/2026,GAS,-20\r\n",
    );
    expect(g.columns).toEqual(["Date", "Description", "Amount"]);
    expect(g.examples).toEqual([
      ["01/10/2026", "RENT", "850"],
      ["02/10/2026", "GAS", "-20"],
    ]);
  });
});

describe("guessing which column is which", () => {
  it("handles a single signed amount column", () => {
    const m = guessMapping(
      ["Date", "Description", "Amount", "Balance"],
      [["01/10/2026", "RENT", "850", "1"]],
    );
    expect(m).toMatchObject({
      dateColumn: "Date",
      descriptionColumn: "Description",
      amountStyle: "signed",
      amountColumn: "Amount",
      dateFormat: "%d/%m/%Y",
    });
  });

  it("handles separate paid in and paid out columns", () => {
    const m = guessMapping(
      ["Transaction Date", "Transaction Description", "Paid Out", "Paid In", "Balance"],
      [["2026-10-01", "RENT", "", "850.00", "1"]],
    );
    expect(m).toMatchObject({
      dateColumn: "Transaction Date",
      descriptionColumn: "Transaction Description",
      amountStyle: "split",
      paidInColumn: "Paid In",
      paidOutColumn: "Paid Out",
      dateFormat: "%Y-%m-%d",
    });
  });

  it.each([
    ["01 Oct 2026", "%d %b %Y"],
    ["01/10/26", "%d/%m/%y"],
    ["01-10-2026", "%d-%m-%Y"],
  ])("recognises dates like %s", (sample, format) => {
    expect(guessMapping(["Date", "Details", "Amount"], [[sample, "X", "1"]]).dateFormat).toBe(
      format,
    );
  });

  it("leaves a column blank rather than guessing wildly", () => {
    expect(guessMapping(["When", "What", "How much"], []).dateColumn).toBe("");
  });
});
