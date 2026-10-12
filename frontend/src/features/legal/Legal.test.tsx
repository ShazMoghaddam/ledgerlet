import { screen, within } from "@testing-library/react";

import { renderApp } from "../../test/renderApp";

it("the privacy notice is public, and says who to contact", async () => {
  renderApp("/privacy", { signedIn: false });
  expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("Privacy notice");
  expect(screen.getByText(/Shaz Moghaddam, trading as LedgerLet/)).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: "shaz.moghaddam@gmail.com" })[0]).toHaveAttribute(
    "href",
    "mailto:shaz.moghaddam@gmail.com",
  );
  expect(screen.getByText(/no advertising, tracking or analytics cookies/)).toBeInTheDocument();
});

it("the terms are public, and link to the privacy notice", async () => {
  renderApp("/terms", { signedIn: false });
  expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("Terms of use");
  expect(screen.getByText(/isn’t made, endorsed or approved by HMRC/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "privacy notice" })).toHaveAttribute("href", "/privacy");
});

it("the sign-in page links to both", async () => {
  renderApp("/sign-in", { signedIn: false });
  const legal = await screen.findByRole("navigation", { name: "Legal" });
  expect(within(legal).getByRole("link", { name: "Privacy" })).toHaveAttribute("href", "/privacy");
  expect(within(legal).getByRole("link", { name: "Terms" })).toHaveAttribute("href", "/terms");
});
