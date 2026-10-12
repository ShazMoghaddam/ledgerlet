/**
 * The headline figures in an update as HMRC received it (the stored request body),
 * so a receipt shows what was sent, not today's figures.
 *
 * The body holds pounds as JSON numbers with two decimals (e.g. 1816.4). They're
 * turned back into whole pence straight away, so all adding up is exact.
 */
const FINANCE = "residentialFinancialCost";
const CONSOLIDATED = "consolidatedExpenses";

const pence = (value: unknown) => (typeof value === "number" ? Math.round(value * 100) : 0);
const sum = (values: unknown[]) => values.reduce<number>((total, v) => total + pence(v), 0);

export interface SentFigures {
  income: number;
  expenses: number;
  financeCosts: number;
  consolidated: boolean;
}

export function sentFigures(body: Record<string, unknown>): SentFigures {
  const property = (body.ukProperty ?? {}) as {
    income?: Record<string, unknown>;
    expenses?: Record<string, unknown>;
  };
  const income = property.income ?? {};
  const expenses = property.expenses ?? {};
  return {
    income: sum(Object.values(income)),
    expenses: sum(
      Object.entries(expenses)
        .filter(([k]) => k !== FINANCE)
        .map(([, v]) => v),
    ),
    financeCosts: pence(expenses[FINANCE]),
    consolidated: CONSOLIDATED in expenses,
  };
}
