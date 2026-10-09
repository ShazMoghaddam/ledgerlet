import { ownershipText, ownsAll, trimPercentage } from "./ownership";

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
