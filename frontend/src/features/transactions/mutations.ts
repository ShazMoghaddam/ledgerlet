/**
 * Saving transactions. After any change, everything that adds transactions up
 * (lists, tax figures, the overview) is refetched, so no screen shows stale totals.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import type { TransactionCategory } from "../../api/types";

export interface TransactionFields {
  transaction_date: string;
  category: TransactionCategory;
  description: string;
  amount: string; // "96.00", from lib/money toApiAmount
}

function useRefreshAfterChange() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["transactions"] }),
      queryClient.invalidateQueries({ queryKey: ["tax"] }),
    ]);
}

export function useCreateTransaction() {
  const refresh = useRefreshAfterChange();
  return useMutation({
    mutationFn: async ({ propertyId, fields }: { propertyId: string; fields: TransactionFields }) =>
      unwrap(
        await api.POST("/api/v1/properties/{property_id}/transactions", {
          params: { path: { property_id: propertyId } },
          body: fields,
        }),
      ),
    onSuccess: refresh,
  });
}

export function useUpdateTransaction(id: string) {
  const refresh = useRefreshAfterChange();
  return useMutation({
    mutationFn: async (fields: TransactionFields) =>
      unwrap(
        await api.PATCH("/api/v1/transactions/{transaction_id}", {
          params: { path: { transaction_id: id } },
          body: fields,
        }),
      ),
    onSuccess: refresh,
  });
}

export function useDeleteTransaction(id: string) {
  const refresh = useRefreshAfterChange();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      unwrap(
        await api.DELETE("/api/v1/transactions/{transaction_id}", {
          params: { path: { transaction_id: id } },
        }),
      ),
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: ["transactions", "one", id] });
      await refresh();
    },
  });
}
