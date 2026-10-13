import type { RouteObject } from "react-router";

import { RequireSignIn } from "../auth/RequireSignIn";
import { AppShell } from "../components/AppShell";
import { CallbackPage } from "../features/auth/CallbackPage";
import { SignInPage } from "../features/auth/SignInPage";
import { HmrcSettingsPage } from "../features/hmrc/HmrcSettingsPage";
import { ReceiptPage } from "../features/hmrc/ReceiptPage";
import { SubmitPage } from "../features/hmrc/SubmitPage";
import { ImportPage } from "../features/import/ImportPage";
import { OverviewPage } from "../features/overview/OverviewPage";
import { EditTransactionPage, NewTransactionPage } from "../features/transactions/TransactionForm";
import { TransactionsPage } from "../features/transactions/TransactionsPage";
import { PrivacyPage } from "../features/legal/PrivacyPage";
import { TermsPage } from "../features/legal/TermsPage";
import { NotFoundPage } from "../features/notFound/NotFoundPage";
import { PropertiesPage } from "../features/properties/PropertiesPage";
import { EditPropertyPage, NewPropertyPage } from "../features/properties/PropertyForm";
import { PropertyPage } from "../features/properties/PropertyPage";
import { SettingsPage } from "../features/settings/SettingsPage";
import { QuarterPage } from "../features/tax/QuarterPage";
import { TaxYearPage } from "../features/tax/TaxYearPage";

/** Every URL in the app. Filters and steps will live in the URL too, so links and Back work. */
export const routes: RouteObject[] = [
  { path: "/sign-in", element: <SignInPage /> },
  { path: "/sign-in/callback", element: <CallbackPage /> },
  // Public, so HMRC and anyone thinking of signing up can read them.
  { path: "/privacy", element: <PrivacyPage /> },
  { path: "/terms", element: <TermsPage /> },
  {
    element: <RequireSignIn />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <OverviewPage /> },
          { path: "transactions", element: <TransactionsPage /> },
          { path: "transactions/:id", element: <TransactionsPage /> },
          { path: "transactions/:id/edit", element: <EditTransactionPage /> },
          { path: "transactions/new", element: <NewTransactionPage /> },
          { path: "transactions/import", element: <ImportPage /> },
          { path: "tax", element: <TaxYearPage /> },
          { path: "tax/:year", element: <TaxYearPage /> },
          { path: "tax/:year/:quarter", element: <QuarterPage /> },
          { path: "tax/:year/:quarter/submit/:step?", element: <SubmitPage /> },
          { path: "tax/:year/:quarter/receipt/:id", element: <ReceiptPage /> },
          { path: "properties", element: <PropertiesPage /> },
          { path: "properties/new", element: <NewPropertyPage /> },
          { path: "properties/:id", element: <PropertyPage /> },
          { path: "properties/:id/edit", element: <EditPropertyPage /> },
          { path: "settings", element: <SettingsPage /> },
          { path: "settings/hmrc", element: <HmrcSettingsPage /> },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
];
