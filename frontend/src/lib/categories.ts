/**
 * Short names for HMRC's categories, for tables and lists where the full HMRC
 * heading ("Legal, management and other professional fees") won't fit. Forms and
 * details use the full label from the API. Typed as a Record, so a category added
 * to the backend fails the type check until it has a short name here.
 */
import type { TransactionCategory } from "../api/types";

export const SHORT_LABEL: Record<TransactionCategory, string> = {
  rental_income: "Rent",
  lease_premium: "Lease premium",
  reverse_premium: "Reverse premium",
  other_income: "Other income",
  premises_running_costs: "Running costs",
  repairs_and_maintenance: "Repairs",
  non_residential_finance_costs: "Finance costs (non-residential)",
  professional_fees: "Professional fees",
  cost_of_services: "Services",
  travel_costs: "Travel",
  other_expenses: "Other expenses",
  residential_finance_costs: "Mortgage interest",
};

/** A line of help shown in the form when the category needs explaining. */
export const CATEGORY_HELP: Partial<Record<TransactionCategory, string>> = {
  residential_finance_costs:
    "Mortgage interest on a home you let. It’s reported separately: HMRC gives a tax credit for it instead of deducting it.",
  premises_running_costs:
    "For example landlord insurance, ground rent, service charges and council tax.",
  repairs_and_maintenance:
    "Repairs that keep the property as it was. Improvements aren’t included.",
};
