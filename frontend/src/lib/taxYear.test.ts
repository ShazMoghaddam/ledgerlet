import { parseTaxPath, taxYearLabel, taxYearOf, taxYearPath } from "./taxYear";

it("starts the tax year on 6 April", () => {
  expect(taxYearOf("2026-04-05")).toBe(2025);
  expect(taxYearOf("2026-04-06")).toBe(2026);
  expect(taxYearOf("2027-01-31")).toBe(2026);
  expect(taxYearLabel(2026)).toBe("2026-27");
  expect(taxYearLabel(2099)).toBe("2099-00");
});

it("reads only well-formed tax addresses", () => {
  expect(parseTaxPath("2026", "q2")).toEqual({ year: 2026, quarter: 2 });
  expect(parseTaxPath("2026", "q5")).toEqual({ year: 2026, quarter: undefined });
  expect(parseTaxPath("26", "2")).toEqual({ year: undefined, quarter: undefined });
});

it("keeps this year's page at /tax", () => {
  expect(taxYearPath(2026, "2026-10-09")).toBe("/tax");
  expect(taxYearPath(2026, "2027-04-06")).toBe("/tax/2026");
});
