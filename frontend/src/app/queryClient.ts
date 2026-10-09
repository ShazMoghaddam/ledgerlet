import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "../api/client";

export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        // Retrying can't fix "not found" or "not allowed"; it can fix a dropped connection.
        retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
      },
    },
  });
}
