import { Link } from "react-router";

import type { Property, TransactionItem } from "../../api/types";
import { Amount } from "../../components/Amount";
import { SHORT_LABEL } from "../../lib/categories";
import { formatMonth, formatShort } from "../../lib/dates";
import { ownsAll } from "../../lib/ownership";
import s from "./TransactionResults.module.css";

type Lookup = Map<string, Property>;

interface Props {
  items: TransactionItem[];
  properties: Lookup;
  search: string; // carried into each link, so Back returns to the same filtered list
  selectedId?: string;
}

/**
 * Tablet and laptop. With room (laptop), property and category get their own
 * columns; on a tablet they sit under the description so In and Out keep their width.
 */
export function TransactionTable({
  items,
  properties,
  search,
  selectedId,
  roomy,
}: Props & { roomy: boolean }) {
  return (
    <table className={`${s.table} num`}>
      <caption className="visually-hidden">Transactions, newest first</caption>
      <thead>
        <tr>
          <th scope="col">Date</th>
          <th scope="col">Description</th>
          {roomy && <th scope="col">Property</th>}
          {roomy && <th scope="col">Category</th>}
          <th scope="col" className={s.money}>
            In
          </th>
          <th scope="col" className={s.money}>
            Out
          </th>
        </tr>
      </thead>
      <tbody>
        {items.map((t) => {
          const prop = properties.get(t.property_id);
          const share = prop && !ownsAll(prop.ownership_percentage);
          const amount = <Amount pounds={t.amount} symbol={false} />;
          return (
            <tr key={t.id} className={t.id === selectedId ? s.selected : undefined}>
              <td className={s.date}>{formatShort(t.transaction_date)}</td>
              <td>
                <Link
                  to={`/transactions/${t.id}${search}`}
                  className={s.rowLink}
                  aria-current={t.id === selectedId ? "true" : undefined}
                >
                  {t.description}
                </Link>
                {!roomy && (
                  <span className={s.meta}>
                    {prop?.nickname}, {SHORT_LABEL[t.category].toLowerCase()}
                    {share && (
                      <>
                        . Your share <Amount pounds={t.share_amount} />
                      </>
                    )}
                  </span>
                )}
                {roomy && share && (
                  <span className={s.meta}>
                    Your share <Amount pounds={t.share_amount} />
                  </span>
                )}
              </td>
              {roomy && <td>{prop?.nickname}</td>}
              {roomy && <td className={s.wideOnly}>{SHORT_LABEL[t.category]}</td>}
              <td className={s.money}>{t.kind === "income" && amount}</td>
              <td className={s.money}>{t.kind === "expense" && amount}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

/** Phone: grouped by month, with + and − so direction never depends on colour. */
export function TransactionList({ items, properties, search }: Props) {
  const months: { label: string; items: TransactionItem[] }[] = [];
  for (const t of items) {
    const label = formatMonth(t.transaction_date);
    const last = months[months.length - 1];
    if (last?.label === label) last.items.push(t);
    else months.push({ label, items: [t] });
  }

  return (
    <div className="num">
      {months.map((m) => (
        <section key={m.label} aria-label={m.label}>
          <h2 className={s.month}>{m.label}</h2>
          <ul className={s.items}>
            {m.items.map((t) => {
              const prop = properties.get(t.property_id);
              const share = prop && !ownsAll(prop.ownership_percentage);
              return (
                <li key={t.id}>
                  <Link to={`/transactions/${t.id}${search}`} className={s.item}>
                    <span>
                      {t.description}
                      <span className={s.meta}>
                        {formatShort(t.transaction_date)}, {prop?.nickname}
                        {share && (
                          <>
                            . Your share <Amount pounds={t.share_amount} />
                          </>
                        )}
                      </span>
                    </span>
                    <Amount
                      className={s.amount}
                      pounds={t.kind === "income" ? t.amount : `-${t.amount}`}
                      signed
                      symbol={false}
                    />
                  </Link>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
