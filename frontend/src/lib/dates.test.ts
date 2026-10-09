import {
  addDays,
  daysBetween,
  formatLong,
  formatMonth,
  formatShort,
  fractionOfSpan,
  ukToday,
} from "./dates";

it("formats API dates the British way", () => {
  expect(formatShort("2026-10-03")).toBe("3 Oct");
  expect(formatShort("2026-09-28")).toBe("28 Sep"); // never "Sept"
  expect(formatLong("2026-11-07")).toBe("7 November 2026");
  expect(formatMonth("2026-09-28")).toBe("September 2026");
});

it("counts days, including across a month end", () => {
  expect(daysBetween("2026-10-09", "2026-11-07")).toBe(29);
  expect(daysBetween("2026-11-07", "2026-10-09")).toBe(-29);
  expect(addDays("2026-07-05", 1)).toBe("2026-07-06");
});

it("works out today in the UK, not on the device clock", () => {
  // 23:30 UTC on 30 June is already 1 July in London (BST).
  expect(ukToday(new Date("2026-06-30T23:30:00Z"))).toBe("2026-07-01");
  // In winter London is on UTC.
  expect(ukToday(new Date("2026-12-31T23:30:00Z"))).toBe("2026-12-31");
});

it("places a day along a span, clamped to the ends", () => {
  expect(fractionOfSpan("2026-04-06", "2026-04-06", "2027-04-05")).toBe(0);
  expect(fractionOfSpan("2027-04-05", "2026-04-06", "2027-04-05")).toBe(1);
  expect(fractionOfSpan("2030-01-01", "2026-04-06", "2027-04-05")).toBe(1);
  expect(fractionOfSpan("2026-10-09", "2026-04-06", "2027-04-05")).toBeCloseTo(186 / 364, 5);
});
