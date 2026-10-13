import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderApp } from "../../test/renderApp";

// A build with Auth0 configured: the sign-in page offers Auth0, not a token box.
const startSignIn = vi.fn<(next: string) => Promise<void>>(() => Promise.resolve());
vi.mock("../../auth/session", async (original) => ({
  ...(await original<typeof import("../../auth/session")>()),
  signInMethod: "auth0",
  startSignIn: (next: string) => startSignIn(next),
}));

it("sends the landlord to Auth0, remembering where they were going", async () => {
  const user = userEvent.setup();
  renderApp("/sign-in?next=%2Ftax", { signedIn: false });
  expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  expect(screen.queryByLabelText("Development token")).toBeNull();
  await user.click(screen.getByRole("button", { name: "Continue to sign in" }));
  expect(startSignIn).toHaveBeenCalledWith("/tax");
  expect(screen.getByRole("button", { name: "Going to sign-in…" })).toBeDisabled();
});

it("says so if Auth0 can't be reached, and lets the landlord try again", async () => {
  startSignIn.mockRejectedValueOnce(new Error("offline"));
  const user = userEvent.setup();
  renderApp("/sign-in", { signedIn: false });
  await user.click(await screen.findByRole("button", { name: "Continue to sign in" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Couldn’t reach the sign-in page");
  expect(screen.getByRole("button", { name: "Continue to sign in" })).toBeEnabled();
});
