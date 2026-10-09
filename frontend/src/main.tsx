import "@fontsource-variable/source-sans-3";
import "@fontsource-variable/source-serif-4";
import "./styles/tokens.css";
import "./styles/base.css";

import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider, createBrowserRouter } from "react-router";

import { makeQueryClient } from "./app/queryClient";
import { routes } from "./app/routes";
import { getToken, subscribe } from "./auth/session";

const router = createBrowserRouter(routes);
const queryClient = makeQueryClient();
// Signing out forgets everything fetched, so the next person on this device sees nothing of it.
subscribe(() => {
  if (!getToken()) queryClient.clear();
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
);
