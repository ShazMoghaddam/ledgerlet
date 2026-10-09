import { formatPence, formatPounds, parseAmountInput, toApiAmount, toPence } from "./money";

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

describe("toApiAmount", () => {
  it.each([
    [9600, "96.00"],
    [5, "0.05"],
    [123456789, "1234567.89"],
  ])("%i pence is %s", (pence, text) => {
    expect(toApiAmount(pence)).toBe(text);
  });
});

describe("parseAmountInput", () => {
  it.each([
    ["96", 9600],
    ["96.5", 9650],
    ["£1,200.00", 120000],
    [" 1 200 ", 120000],
    ["0.01", 1],
  ])("reads %j as %i pence", (text, pence) => {
    expect(parseAmountInput(text)).toEqual({ ok: true, pence });
  });

  it.each([
    ["", "Enter an amount, like 96.00"],
    ["-5", "Enter the amount without a minus sign. Choose money in or out instead."],
    ["96.505", "Amounts can only have pence, like 96.50"],
    ["ninety", "Enter an amount in pounds and pence, like 96.00"],
    ["0", "Enter an amount more than £0.00"],
    ["0.00", "Enter an amount more than £0.00"],
    ["10000000000", "Enter an amount under £10,000,000,000"],
  ])("explains what's wrong with %j", (text, error) => {
    expect(parseAmountInput(text)).toEqual({ ok: false, error });
  });
});
