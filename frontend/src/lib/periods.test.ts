import obligations from "../test/fixtures/obligations.json";
import type { Obligations } from "../api/types";
import { periodsFor, updatePeriodKey } from "./periods";

const periods = periodsFor(obligations as Obligations, "2026-10-09");

it("offers what each quarterly update covers, from the start of the year", () => {
  const byKey = Object.fromEntries(periods.map((p) => [p.key, p]));
  expect(byKey["2026-to-q2"]).toMatchObject({
    from: "2026-04-06",
    to: "2026-10-05",
    label: "Quarter 2 update (6 Apr to 5 Oct)",
  });
  expect([1, 2, 3, 4].map((q) => updatePeriodKey(2026, q))).toEqual([
    "2026-q1",
    "2026-to-q2",
    "2026-to-q3",
    "2026",
  ]);
});

it("offers the tax year, its quarters, last year and everything", () => {
  expect(periods.map((p) => p.key)).toEqual([
    "2026",
    "2026-q1",
    "2026-q2",
    "2026-q3",
    "2026-q4",
    "2026-to-q2",
    "2026-to-q3",
    "2025",
    "all",
  ]);
});

it("uses the tax year's own dates", () => {
  const byKey = Object.fromEntries(periods.map((p) => [p.key, p]));
  expect(byKey["2026"]).toMatchObject({ from: "2026-04-06", to: "2027-04-05" });
  expect(byKey["2026-q2"]).toMatchObject({
    from: "2026-07-06",
    to: "2026-10-05",
    label: "Quarter 2 (6 Jul to 5 Oct)",
  });
  expect(byKey["2025"]).toMatchObject({
    from: "2025-04-06",
    to: "2026-04-05",
    label: "Tax year 2025-26",
  });
  expect(byKey["all"]?.from).toBeUndefined();
});
