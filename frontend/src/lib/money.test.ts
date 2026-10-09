import { formatPence, formatPounds, toPence } from "./money";

describe("toPence", () => {
  it.each([
    ["1200.00", 120000],
    ["1816.40", 181640],
    ["0.1", 10],
    ["7", 700],
    ["-490.00", -49000],
    [" 96.00 ", 9600],
  ])("%s is %i pence", (text, pence) => {
    expect(toPence(text)).toBe(pence);
  });

  it.each(["", "abc", "1.005", "1,200.00", "£5", "1e3", "NaN"])("refuses %j", (text) => {
    expect(() => toPence(text)).toThrow();
  });

  it("adds up exactly where floats would not", () => {
    expect(toPence("0.10") + toPence("0.20")).toBe(toPence("0.30"));
  });
});

describe("formatPence", () => {
  it("formats pounds with grouping and two places", () => {
    expect(formatPence(1018360)).toBe("£10,183.60");
    expect(formatPence(5)).toBe("£0.05");
    expect(formatPence(0)).toBe("£0.00");
  });

  it("uses a real minus sign, and a plus only when asked", () => {
    expect(formatPence(-9600)).toBe("−£96.00");
    expect(formatPence(160000, { signed: true, symbol: false })).toBe("+1,600.00");
    expect(formatPence(160000)).toBe("£1,600.00");
  });

  it("refuses fractions of a penny", () => {
    expect(() => formatPence(1.5)).toThrow();
  });
});

it("formatPounds goes straight from API text to display text", () => {
  expect(formatPounds("12000.00")).toBe("£12,000.00");
});
