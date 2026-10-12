/**
 * Each property's figures for the tax year so far, at the landlord's share. They
 * come from the same tax summary HMRC is sent, so the two can never disagree.
 */
import { useObligations, useSummary } from "../../api/queries";
import type { PropertySummary } from "../../api/types";
import { ukToday } from "../../lib/dates";
import { currentQuarter, quarterStates } from "../../lib/quarters";

export function useYearFigures() {
  const obligations = useObligations();
  const today = ukToday();
  const quarter = obligations.data
    ? currentQuarter(quarterStates(obligations.data.obligations, [], today))
    : undefined;
  const summary = useSummary(obligations.data?.tax_year, quarter?.quarter);
  const byProperty = new Map<string, PropertySummary>(
    (summary.data?.properties ?? []).map((p) => [p.property_id, p]),
  );
  return {
    byProperty,
    label: obligations.data ? `Tax year ${obligations.data.tax_year_label}` : undefined,
    isPending: obligations.isPending || (quarter !== undefined && summary.isPending),
    error: obligations.error ?? summary.error,
    retry: () => {
      void obligations.refetch();
      void summary.refetch();
    },
  };
}
