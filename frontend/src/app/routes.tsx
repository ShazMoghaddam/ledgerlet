import type { RouteObject } from "react-router";

import { RequireSignIn } from "../auth/RequireSignIn";
import { AppShell } from "../components/AppShell";
import { SignInPage } from "../features/auth/SignInPage";
import { OverviewPage } from "../features/overview/OverviewPage";
import { NotFoundPage, SectionPlaceholder } from "../features/placeholder/SectionPlaceholder";

const soon = "This screen is being built and arrives in the next update.";

/** Every URL in the app. Filters and steps will live in the URL too, so links and Back work. */
export const routes: RouteObject[] = [
  { path: "/sign-in", element: <SignInPage /> },
  {
    element: <RequireSignIn />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <OverviewPage /> },
          {
            path: "transactions",
            element: <SectionPlaceholder title="Transactions" description={soon} />,
          },
          {
            path: "transactions/new",
            element: <SectionPlaceholder title="Add a transaction" description={soon} />,
          },
          {
            path: "transactions/import",
            element: <SectionPlaceholder title="Import a bank statement" description={soon} />,
          },
          { path: "tax", element: <SectionPlaceholder title="Tax" description={soon} /> },
          {
            path: "tax/:year/:quarter/submit",
            element: <SectionPlaceholder title="Review and submit" description={soon} />,
          },
          {
            path: "properties",
            element: <SectionPlaceholder title="Properties" description={soon} />,
          },
          {
            path: "properties/new",
            element: <SectionPlaceholder title="Add a property" description={soon} />,
          },
          {
            path: "properties/:id",
            element: <SectionPlaceholder title="Property" description={soon} />,
          },
          {
            path: "settings",
            element: <SectionPlaceholder title="Settings" description={soon} showSignOut />,
          },
          {
            path: "settings/hmrc",
            element: <SectionPlaceholder title="HMRC connection" description={soon} />,
          },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
];
