/**
 * HMRC responses for the sample landlord. These can't be exported from the backend
 * (they need HMRC), so they're written here, typed against the API so they can't
 * drift from its shapes.
 */
import type { HmrcConnection, Submission, Taxpayer } from "../../api/types";

export const connection: HmrcConnection = {
  connected: true,
  connected_at: "2026-08-04T09:12:00Z",
  access_token_expires_at: "2026-10-09T13:00:00Z",
  scope: "read:self-assessment write:self-assessment",
};

export const notConnected: HmrcConnection = {
  connected: false,
  connected_at: null,
  access_token_expires_at: null,
  scope: null,
};

export const taxpayer: Taxpayer = { nino: "OE****77A", uk_property_business_id: "XDIS36257256364" };

/** Quarter 1 was sent on 4 August. */
export const submissions: Submission[] = [
  {
    id: "00000004-0000-0000-0000-000000000001",
    business_id: "XDIS36257256364",
    tax_year: 2026,
    quarter: 1,
    period_start: "2026-04-06",
    period_end: "2026-07-05",
    consolidated_expenses: false,
    succeeded: true,
    status_code: 204,
    hmrc_correlation_id: "c5a1f1e2-7b7e-4b8a-9d3e-2f1a0c9b8e71",
    submitted_at: "2026-08-04T10:42:00Z",
    request_body: {},
    response_body: {},
  },
];
