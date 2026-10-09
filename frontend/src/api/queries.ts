/**
 * Server state, read through TanStack Query. Each hook is one API call with a
 * stable cache key, so screens that show the same data share one request.
 */
import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "./client";
import type { TransactionCategory } from "./types";

export const keys = {
  me: ["me"] as const,
  properties: ["properties"] as const,
  obligations: (taxYear?: number) => ["tax", "obligations", taxYear ?? "current"] as const,
  summary: (taxYear: number, quarter: number) => ["tax", "summary", taxYear, quarter] as const,
  transactions: (params: TransactionParams) => ["transactions", "list", params] as const,
  transaction: (id: string) => ["transactions", "one", id] as const,
  categories: ["categories"] as const,
  hmrcConnection: ["hmrc", "connection"] as const,
  taxpayer: ["hmrc", "taxpayer"] as const,
  submissions: (taxYear: number) => ["hmrc", "submissions", taxYear] as const,
};

export interface TransactionParams {
  limit?: number;
  offset?: number;
  property_id?: string;
  date_from?: string;
  date_to?: string;
  category?: TransactionCategory;
  q?: string;
}

export const useMe = () =>
  useQuery({ queryKey: keys.me, queryFn: async () => unwrap(await api.GET("/api/v1/me")) });

export const useProperties = () =>
  useQuery({
    queryKey: keys.properties,
    queryFn: async () => unwrap(await api.GET("/api/v1/properties")),
  });

export const useObligations = (taxYear?: number) =>
  useQuery({
    queryKey: keys.obligations(taxYear),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/tax/obligations", { params: { query: { tax_year: taxYear } } }),
      ),
  });

export const useSummary = (taxYear: number | undefined, quarter: number | undefined) =>
  useQuery({
    queryKey: keys.summary(taxYear ?? 0, quarter ?? 0),
    enabled: taxYear !== undefined && quarter !== undefined,
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/tax/summary", {
          params: { query: { tax_year: taxYear, quarter: quarter ?? 1 } },
        }),
      ),
  });

export const useTransactions = (params: TransactionParams) =>
  useQuery({
    queryKey: keys.transactions(params),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/transactions", { params: { query: params } })),
  });

export const useHmrcConnection = () =>
  useQuery({
    queryKey: keys.hmrcConnection,
    queryFn: async () => unwrap(await api.GET("/api/v1/hmrc/connection")),
  });

export const useTaxpayer = () =>
  useQuery({
    queryKey: keys.taxpayer,
    queryFn: async () => unwrap(await api.GET("/api/v1/hmrc/taxpayer")),
  });

export const useSubmissions = (taxYear: number | undefined) =>
  useQuery({
    queryKey: keys.submissions(taxYear ?? 0),
    enabled: taxYear !== undefined,
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/hmrc/submissions", { params: { query: { tax_year: taxYear } } }),
      ),
  });

export const useTransaction = (id: string | undefined) =>
  useQuery({
    queryKey: keys.transaction(id ?? ""),
    enabled: id !== undefined,
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/transactions/{transaction_id}", {
          params: { path: { transaction_id: id ?? "" } },
        }),
      ),
  });

export const useCategories = () =>
  useQuery({
    queryKey: keys.categories,
    staleTime: Infinity, // fixed by HMRC; they don't change while the app is open
    queryFn: async () => unwrap(await api.GET("/api/v1/transactions/categories")),
  });
