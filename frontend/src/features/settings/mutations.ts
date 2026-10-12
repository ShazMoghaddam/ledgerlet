import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import type { components } from "../../api/schema";

type Changes = components["schemas"]["LandlordUpdate"];

/**
 * Change your own settings. The update basis moves every quarter's dates, so
 * everything is refetched afterwards, not just the profile.
 */
export function useUpdateMe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (changes: Changes) =>
      unwrap(await api.PATCH("/api/v1/me", { body: changes })),
    onSuccess: () => queryClient.invalidateQueries(),
  });
}
