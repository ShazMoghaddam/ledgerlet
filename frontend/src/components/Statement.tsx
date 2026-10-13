import type { Totals } from "../api/types";
import { toPence } from "../lib/money";
import { Amount } from "./Amount";
import s from "./Statement.module.css";

/**
 * Income, expenses and profit, ruled like a bank statement, with mortgage interest
 * explained underneath (it's reported separately, so it isn't in the profit).
 */
export function Statement({ totals: t, whose }: { totals: Totals; whose: string }) {
  return (
    <>
      <dl className={`${s.statement} num`}>
        <div>
          <dt>Income</dt>
          <dd>
            <Amount pounds={t.income} />
          </dd>
        </div>
        <div>
          <dt>Expenses</dt>
          <dd>
            <Amount pounds={t.expenses} />
          </dd>
        </div>
        <div className={s.total}>
          <dt>Profit</dt>
          <dd>
            <Amount pounds={t.profit} />
          </dd>
        </div>
      </dl>
      <p className={s.note}>
        Your share across {whose}.
        {toPence(t.residential_finance_costs) > 0 && (
          <>
            {" "}
            Mortgage interest of <Amount pounds={t.residential_finance_costs} /> is reported
            separately, because HMRC gives a tax credit for it.
          </>
        )}
      </p>
    </>
  );
}

/** "your property", "both properties", "all 3 properties"; "your properties" for none yet. */
export const whoseProperties = (count: number) =>
  count === 0
    ? "your properties"
    : count === 1
      ? "your property"
      : count === 2
        ? "both properties"
        : `all ${count} properties`;
