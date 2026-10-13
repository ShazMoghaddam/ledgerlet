import { whoseProperties } from "./Statement";

describe("whoseProperties", () => {
  it.each([
    [0, "your properties"],
    [1, "your property"],
    [2, "both properties"],
    [3, "all 3 properties"],
  ])("%i reads as “%s”", (count, text) => expect(whoseProperties(count)).toBe(text));
});
