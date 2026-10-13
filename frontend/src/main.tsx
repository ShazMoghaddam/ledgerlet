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
import { initSession, isSignedIn, subscribe } from "./auth/session";

const router = createBrowserRouter(routes);
const queryClient = makeQueryClient();
// Signing out forgets everything fetched, so the next person on this device sees nothing of it.
subscribe(() => {
  if (!isSignedIn()) queryClient.clear();
});

// Find out whether there's a session first, so a signed-in landlord never sees the
// sign-in page flash up on a refresh.
void initSession()
  .catch((error: unknown) => console.error("Couldn’t check the sign-in", error))
  .then(() =>
    createRoot(document.getElementById("root")!).render(
      <StrictMode>
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </StrictMode>,
    ),
  );
