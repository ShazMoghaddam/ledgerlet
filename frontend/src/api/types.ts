/** Friendly names for the generated API types (src/api/schema.d.ts, from the backend). */
import type { components } from "./schema";

type Schemas = components["schemas"];

export type Landlord = Schemas["LandlordRead"];
export type Property = Schemas["PropertyRead"];
export type Obligation = Schemas["ObligationRead"];
export type Obligations = Schemas["ObligationsRead"];
export type ObligationStatus = Schemas["ObligationStatus"];
export type TaxSummary = Schemas["TaxSummary"];
export type Totals = Schemas["Totals"];
export type TransactionItem = Schemas["TransactionListItem"];
export type TransactionPage = Schemas["TransactionPage"];
export type TransactionCategory = Schemas["TransactionCategory"];
export type Category = Schemas["CategoryRead"];
export type HmrcConnection = Schemas["ConnectionStatus"];
export type Taxpayer = Schemas["TaxpayerRead"];
export type Submission = Schemas["SubmissionRead"];
export type ImportPreview = Schemas["ImportPreview"];
export type PreviewRow = Schemas["PreviewRow"];
export type ImportResult = Schemas["ImportResult"];
export type ImportRowConfirm = Schemas["ImportRowConfirm"];
