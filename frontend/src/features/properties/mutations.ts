/**
 * Adding and changing properties. A property's share changes every figure that
 * involves it, so the tax figures and transaction lists are refetched too.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";

export interface PropertyFields {
  nickname: string;
  address_line_1: string;
  address_line_2: string | null;
  town: string;
  postcode: string;
  ownership_percentage: string; // "50" or "33.33": exact, never a float
}

function useRefresh() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all(
      ["properties", "tax", "transactions"].map((key) =>
        queryClient.invalidateQueries({ queryKey: [key] }),
      ),
    );
}

export function useCreateProperty() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async (fields: PropertyFields) =>
      unwrap(await api.POST("/api/v1/properties", { body: fields })),
    onSuccess: refresh,
  });
}

export function useUpdateProperty(id: string) {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async (fields: Partial<PropertyFields>) =>
      unwrap(
        await api.PATCH("/api/v1/properties/{property_id}", {
          params: { path: { property_id: id } },
          body: fields,
        }),
      ),
    onSuccess: refresh,
  });
}

export function useArchiveProperty(id: string, archive: boolean) {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async () =>
      unwrap(
        await api.POST(
          archive
            ? "/api/v1/properties/{property_id}/archive"
            : "/api/v1/properties/{property_id}/restore",
          { params: { path: { property_id: id } } },
        ),
      ),
    onSuccess: refresh,
  });
}
