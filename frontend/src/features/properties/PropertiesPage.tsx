import { Link } from "react-router";

import { useAllProperties } from "../../api/queries";
import type { Property, PropertySummary } from "../../api/types";
import { Amount } from "../../components/Amount";
import { ButtonLink } from "../../components/Button";
import { PlusIcon } from "../../components/Icons";
import { LoadFailed, Loading } from "../../components/QueryState";
import { WIDE, useMediaQuery } from "../../hooks/useMediaQuery";
import { usePageTitle } from "../../hooks/usePageTitle";
import { formatLong } from "../../lib/dates";
import { ownershipText } from "../../lib/ownership";
import s from "./Properties.module.css";
import { useYearFigures } from "./yearFigures";

/** /properties: every property, with its share and this tax year's figures so far. */
export function PropertiesPage() {
  usePageTitle("Properties");
  const properties = useAllProperties();

  return (
    <div className={s.page}>
      <div className={s.head}>
        <h1 id="page-heading" tabIndex={-1}>
          Properties
        </h1>
        {/* An empty list has its own, larger button: one is enough. */}
        {properties.data?.length !== 0 && (
          <ButtonLink to="/properties/new">
            <PlusIcon size={18} />
            Add a property
          </ButtonLink>
        )}
      </div>
      {properties.isPending ? (
        <Loading label="your properties" />
      ) : properties.isError ? (
        <LoadFailed what="your properties" error={properties.error} retry={properties.refetch} />
      ) : properties.data.length === 0 ? (
        <Empty />
      ) : (
        <Lists properties={properties.data} />
      )}
    </div>
  );
}

function Lists({ properties }: { properties: Property[] }) {
  const figures = useYearFigures();
  const active = properties.filter((p) => !p.is_archived);
  const archived = properties.filter((p) => p.is_archived);

  return (
    <>
      <section className={s.section} aria-labelledby="active-heading">
        <h2 id="active-heading" className="visually-hidden">
          Properties you let
        </h2>
        {figures.error ? (
          <LoadFailed what="this year’s figures" error={figures.error} retry={figures.retry} />
        ) : (
          figures.label && (
            <p className={s.note}>
              Figures are for {figures.label.toLowerCase()} so far, at your share.
            </p>
          )
        )}
        {active.length === 0 ? (
          <p className={s.note}>
            All your properties are archived. <Link to="/properties/new">Add a property</Link> to
            record new income and expenses.
          </p>
        ) : (
          <PropertyRows
            properties={active}
            figures={figures.byProperty}
            pending={figures.isPending}
          />
        )}
      </section>

      {archived.length > 0 && (
        <section className={s.section} aria-labelledby="archived-heading">
          <h2 id="archived-heading">Archived</h2>
          <p className={s.note}>
            Properties you no longer let. Their past income and expenses still count in your tax
            figures; they just don’t appear in forms.
          </p>
          <ul className={s.archivedList}>
            {archived.map((p) => (
              <li key={p.id}>
                <Link to={`/properties/${p.id}`}>{p.nickname}</Link>
                <span className={s.meta}>
                  {p.address_line_1}, {p.postcode}
                  {p.archived_at && <>. Archived {formatLong(p.archived_at.slice(0, 10))}</>}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

function PropertyRows({
  properties,
  figures,
  pending,
}: {
  properties: Property[];
  figures: Map<string, PropertySummary>;
  pending: boolean;
}) {
  const wide = useMediaQuery(WIDE);
  const money = (p: Property, key: "income" | "expenses") => {
    const f = figures.get(p.id);
    if (f) return <Amount pounds={f.totals[key]} symbol={false} />;
    return pending ? "…" : <Amount pounds="0.00" symbol={false} />;
  };

  if (!wide)
    return (
      <ul className={s.cards}>
        {properties.map((p) => (
          <li key={p.id}>
            <Link to={`/properties/${p.id}`} className={s.card}>
              <span className={s.cardName}>{p.nickname}</span>
              <span className={s.meta}>
                {p.address_line_1}, {p.town}. {ownershipText(p.ownership_percentage)}
              </span>
              <span className={`${s.cardFigures} num`}>
                <span>In {money(p, "income")}</span>
                <span>Out {money(p, "expenses")}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    );

  return (
    <table className={`${s.table} num`}>
      <caption className="visually-hidden">
        Your properties, with this tax year’s figures at your share
      </caption>
      <thead>
        <tr>
          <th scope="col">Property</th>
          <th scope="col">Your share</th>
          <th scope="col" className={s.money}>
            Income
          </th>
          <th scope="col" className={s.money}>
            Expenses
          </th>
          <th scope="col" className={s.money}>
            Transactions
          </th>
        </tr>
      </thead>
      <tbody>
        {properties.map((p) => (
          <tr key={p.id}>
            <th scope="row">
              <Link to={`/properties/${p.id}`}>{p.nickname}</Link>
              <span className={s.meta}>
                {p.address_line_1}, {p.town} {p.postcode}
              </span>
            </th>
            <td>{ownershipText(p.ownership_percentage)}</td>
            <td className={s.money}>{money(p, "income")}</td>
            <td className={s.money}>{money(p, "expenses")}</td>
            <td className={s.money}>
              {figures.get(p.id)?.transaction_count ?? (pending ? "…" : 0)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Empty() {
  return (
    <section className={s.empty} aria-labelledby="empty-heading">
      <h2 id="empty-heading">Add your first property</h2>
      <p>
        LedgerLet works out what to send HMRC from the income and expenses of each property you let.
        Start with one; you can add more at any time.
      </p>
      <div>
        <ButtonLink to="/properties/new" size="large">
          Add a property
        </ButtonLink>
      </div>
    </section>
  );
}
