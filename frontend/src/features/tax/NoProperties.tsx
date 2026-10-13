import { useAllProperties } from "../../api/queries";
import { ButtonLink } from "../../components/Button";
import s from "./Tax.module.css";

/**
 * True once we know the landlord has never added a property (archived ones count:
 * they may already have sent updates). Undefined while still finding out.
 */
export function useHasNoProperties(): boolean | undefined {
  const properties = useAllProperties();
  return properties.data ? properties.data.length === 0 : undefined;
}

/**
 * In place of quarter statuses for a brand-new account. With no property there's
 * nothing to record or send, so "Ready to send" or "Overdue" would be untrue.
 */
export function NoProperties() {
  return (
    <section className={`${s.section} ${s.empty}`} aria-labelledby="no-properties-heading">
      <h2 id="no-properties-heading">Add your first property</h2>
      <p className={s.prose}>
        Your quarterly updates are worked out from the income and expenses of the properties you
        let. Once you’ve added one, you’ll see what’s due here, and when.
      </p>
      <div>
        <ButtonLink to="/properties/new">Add a property</ButtonLink>
      </div>
    </section>
  );
}
