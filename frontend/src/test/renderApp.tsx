import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router";

import { routes } from "../app/routes";
import { signIn } from "../auth/session";

export const SAMPLE_TOKEN = "header.payload.signature";

/** The whole app at a URL, signed in by default, at a given window width. */
export function renderApp(path = "/", { width = 1440, signedIn = true } = {}) {
  window.innerWidth = width;
  if (signedIn) signIn(SAMPLE_TOKEN);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { router };
}
