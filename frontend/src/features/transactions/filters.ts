/**
 * The list's filters live in the URL (?period=2026-q2&property=…&q=boiler&page=2),
 * so a filtered list can be bookmarked, shared, refreshed or reached with Back.
 */
import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";

import type { TransactionCategory } from "../../api/types";
import { SHORT_LABEL } from "../../lib/categories";

export const PAGE_SIZE = 50;

export interface Filters {
  period?: string; // a key from lib/periods; undefined means this tax year
  property?: string;
  category?: TransactionCategory;
  q?: string;
  page: number;
}

const isCategory = (value: string | null): value is TransactionCategory =>
  value !== null && value in SHORT_LABEL;

export function useFilters() {
  const [params, setParams] = useSearchParams();

  const filters: Filters = useMemo(() => {
    const page = Number(params.get("page") ?? "1");
    const category = params.get("category");
    return {
      period: params.get("period") ?? undefined,
      property: params.get("property") ?? undefined,
      category: isCategory(category) ? category : undefined,
      q: params.get("q") ?? undefined,
      page: Number.isInteger(page) && page > 0 ? page : 1,
    };
  }, [params]);

  /** Change some filters. Any change other than the page goes back to page 1. */
  const update = useCallback(
    (changes: Partial<Filters>, { replace = false } = {}) => {
      setParams(
        (current) => {
          const next = new URLSearchParams(current);
          for (const [key, value] of Object.entries(changes)) {
            if (value === undefined || value === "") next.delete(key);
            else next.set(key, String(value));
          }
          if (!("page" in changes)) next.delete("page");
          if (next.get("page") === "1") next.delete("page");
          return next;
        },
        { replace },
      );
    },
    [setParams],
  );

  return { filters, update, search: params.toString() ? `?${params.toString()}` : "" };
}
