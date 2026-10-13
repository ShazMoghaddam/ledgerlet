import { callbackError } from "./CallbackPage";

describe("callbackError", () => {
  it("passes on the sign-in service's own reason", () => {
    expect(
      callbackError({ error: "access_denied", error_description: "Service not found: x." }),
    ).toBe("The sign-in service said: “Service not found: x.”");
  });

  it("explains a declined consent screen", () => {
    expect(callbackError({ error: "access_denied" })).toBe(
      "You chose not to give LedgerLet access.",
    );
  });

  it("falls back to the likeliest cause", () => {
    expect(callbackError(new Error("Invalid state"))).toBe(
      "The sign-in link may have expired or already been used.",
    );
    expect(callbackError(undefined)).toMatch(/expired/);
  });
});
