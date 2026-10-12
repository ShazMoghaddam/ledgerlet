import {
  ownershipText,
  ownsAll,
  trimPercentage,
  looksLikePostcode,
  parsePercentage,
} from "./ownership";

it.each([
  ["100.00", "100"],
  ["50.00", "50"],
  ["50.50", "50.5"],
  ["33.33", "33.33"],
  ["10", "10"],
])("trims %s to %s, never eating digits before the point", (raw, trimmed) => {
  expect(trimPercentage(raw)).toBe(trimmed);
});

it("describes a share in words", () => {
  expect(ownershipText("100.00")).toBe("You own all");
  expect(ownershipText("50.00")).toBe("You own half");
  expect(ownershipText("25.00")).toBe("You own 25%");
  expect(ownsAll("100.00")).toBe(true);
  expect(ownsAll("50.00")).toBe(false);
});

describe("parsePercentage", () => {
  it.each([
    ["50", "50"],
    ["33.33", "33.33"],
    ["12.5%", "12.5"],
    [" 100 ", "100"],
    ["007", "7"],
  ])("reads %j exactly as %j", (raw, value) => {
    expect(parsePercentage(raw)).toEqual({ ok: true, value });
  });

  it.each([
    ["", "Enter your share"],
    ["0", "more than 0%"],
    ["100.01", "can’t be more than 100%"],
    ["12.345", "like 50 or 33.33"],
    ["half", "like 50 or 33.33"],
  ])("refuses %j", (raw, message) => {
    const result = parsePercentage(raw);
    expect(result.ok).toBe(false);
    expect(!result.ok && result.error).toContain(message);
  });
});

it("checks postcodes the way the API does", () => {
  expect(looksLikePostcode("sw1a 1aa")).toBe(true);
  expect(looksLikePostcode("LS6 2AB")).toBe(true);
  expect(looksLikePostcode("12345")).toBe(false);
});
