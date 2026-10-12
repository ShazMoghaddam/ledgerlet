/**
 * Changing the HMRC connection and the details LedgerLet files under, and sending
 * updates. After each change the HMRC queries are refetched, so every screen agrees.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import { keys } from "../../api/queries";

function useRefreshHmrc() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["hmrc"] });
}

/** Start connecting: the API returns HMRC's sign-in page, and the browser goes there. */
export function useConnect() {
  return useMutation({
    mutationFn: async (returnTo: string) =>
      unwrap(await api.POST("/api/v1/hmrc/connect", { body: { return_to: returnTo } })),
    onSuccess: ({ authorize_url }) => window.location.assign(authorize_url),
  });
}

export function useDisconnect() {
  const refresh = useRefreshHmrc();
  return useMutation({
    mutationFn: async () => unwrap(await api.DELETE("/api/v1/hmrc/connection")),
    onSuccess: refresh,
  });
}

export function useSetNino() {
  const refresh = useRefreshHmrc();
  return useMutation({
    mutationFn: async (nino: string) =>
      unwrap(await api.PUT("/api/v1/hmrc/taxpayer", { body: { nino } })),
    onSuccess: refresh,
  });
}

/** Ask HMRC for the landlord's businesses. A single UK property business is chosen for them. */
export function useDiscoverBusinesses() {
  const refresh = useRefreshHmrc();
  return useMutation({
    mutationFn: async () => unwrap(await api.POST("/api/v1/hmrc/businesses/discover")),
    onSuccess: refresh,
  });
}

export function useSetBusiness() {
  const refresh = useRefreshHmrc();
  return useMutation({
    mutationFn: async (businessId: string) =>
      unwrap(
        await api.PUT("/api/v1/hmrc/taxpayer/business", { body: { business_id: businessId } }),
      ),
    onSuccess: refresh,
  });
}

export interface UpdateChoice {
  taxYear: number;
  quarter: number;
  consolidated: boolean;
}

/** Exactly what would be sent to HMRC. Sends nothing. */
export const usePreviewUpdate = ({ taxYear, quarter, consolidated }: UpdateChoice) =>
  useQuery({
    queryKey: ["hmrc", "preview", taxYear, quarter, consolidated],
    queryFn: async () =>
      unwrap(
        await api.POST("/api/v1/hmrc/submissions/preview", {
          body: { tax_year: taxYear, quarter, consolidated_expenses: consolidated },
        }),
      ),
  });

/** Send the update. Every attempt is recorded by the API, accepted or not. */
export function useSendUpdate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ taxYear, quarter, consolidated }: UpdateChoice) =>
      unwrap(
        await api.POST("/api/v1/hmrc/submissions", {
          body: { tax_year: taxYear, quarter, consolidated_expenses: consolidated },
        }),
      ),
    // Refetch the history whatever happened: a refused attempt is on record too.
    onSettled: (_data, _error, { taxYear }) =>
      queryClient.invalidateQueries({ queryKey: keys.submissions(taxYear) }),
  });
}
