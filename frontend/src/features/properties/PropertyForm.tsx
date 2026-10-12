import { useState, type FormEvent, type ReactNode } from "react";
import { useNavigate, useParams } from "react-router";

import { ApiError } from "../../api/client";
import { useProperty } from "../../api/queries";
import type { Property } from "../../api/types";
import { Button, ButtonLink } from "../../components/Button";
import { ErrorSummary, type FieldError } from "../../components/ErrorSummary";
import f from "../../components/Field.module.css";
import { LoadFailed, Loading } from "../../components/QueryState";
import { usePageTitle } from "../../hooks/usePageTitle";
import { looksLikePostcode, parsePercentage, trimPercentage } from "../../lib/ownership";
import { BackLink } from "./BackLink";
import { useCreateProperty, useUpdateProperty, type PropertyFields } from "./mutations";
import s from "./Properties.module.css";

type ShareChoice = "100" | "50" | "other";

interface Values {
  nickname: string;
  line1: string;
  line2: string;
  town: string;
  postcode: string;
  share: ShareChoice | "";
  otherShare: string;
}

const BLANK: Values = {
  nickname: "",
  line1: "",
  line2: "",
  town: "",
  postcode: "",
  share: "",
  otherShare: "",
};

function valuesOf(p: Property): Values {
  const share = trimPercentage(p.ownership_percentage);
  return {
    nickname: p.nickname,
    line1: p.address_line_1,
    line2: p.address_line_2 ?? "",
    town: p.town,
    postcode: p.postcode,
    share: share === "100" || share === "50" ? share : "other",
    otherShare: share === "100" || share === "50" ? "" : share,
  };
}

/** /properties/new */
export function NewPropertyPage() {
  usePageTitle("Add a property");
  return <PropertyForm initial={BLANK} />;
}

/** /properties/:id/edit */
export function EditPropertyPage() {
  const { id } = useParams();
  const property = useProperty(id);
  usePageTitle(property.data ? `Edit ${property.data.nickname}` : "Edit property");

  if (property.isPending || property.isError)
    return (
      <div className={s.formPage}>
        <BackLink to={`/properties/${id}`}>Back to the property</BackLink>
        <h1 id="page-heading" tabIndex={-1}>
          Edit property
        </h1>
        {property.isPending ? (
          <Loading label="the property" />
        ) : (
          <LoadFailed what="the property" error={property.error} retry={property.refetch} />
        )}
      </div>
    );
  if (property.data.is_archived)
    return (
      <div className={s.formPage}>
        <BackLink to={`/properties/${id}`}>Back to the property</BackLink>
        <h1 id="page-heading" tabIndex={-1}>
          Edit {property.data.nickname}
        </h1>
        <p>This property is archived. Restore it first, then you can edit it.</p>
      </div>
    );
  return <PropertyForm existing={property.data} initial={valuesOf(property.data)} />;
}

function PropertyForm({ existing, initial }: { existing?: Property; initial: Values }) {
  const navigate = useNavigate();
  const [values, setValues] = useState<Values>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [summary, setSummary] = useState<FieldError[]>([]);
  const create = useCreateProperty();
  const update = useUpdateProperty(existing?.id ?? "");
  const saving = create.isPending || update.isPending;
  const back = existing ? `/properties/${existing.id}` : "/properties";

  const set = <K extends keyof Values>(key: K, value: Values[K]) =>
    setValues((v) => ({ ...v, [key]: value }));

  function validate(): PropertyFields | null {
    const found: Record<string, string> = {};
    const nickname = values.nickname.trim();
    if (!nickname) found["p-nickname"] = "Enter a name for the property, like “Flat 4”";
    else if (nickname.length > 100)
      found["p-nickname"] = "Keep the name to 100 characters or fewer";
    if (!values.line1.trim()) found["p-line1"] = "Enter the first line of the address";
    if (!values.town.trim()) found["p-town"] = "Enter the town or city";
    if (!values.postcode.trim()) found["p-postcode"] = "Enter the postcode";
    else if (!looksLikePostcode(values.postcode))
      found["p-postcode"] = "Enter a real UK postcode, like LS6 2AB";

    let share: string | undefined;
    if (!values.share) found["p-share-100"] = "Choose how much of it you own";
    else if (values.share === "other") {
      const parsed = parsePercentage(values.otherShare);
      if (parsed.ok) share = parsed.value;
      else found["p-other-share"] = parsed.error;
    } else share = values.share;

    setErrors(found);
    setSummary(Object.entries(found).map(([field, message]) => ({ field, message })));
    if (Object.keys(found).length || share === undefined) return null;
    return {
      nickname,
      address_line_1: values.line1.trim(),
      address_line_2: values.line2.trim() || null,
      town: values.town.trim(),
      postcode: values.postcode.trim(),
      ownership_percentage: share,
    };
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    const fields = validate();
    if (!fields) return;
    const onError = (error: Error) =>
      setSummary([
        {
          message:
            error instanceof ApiError
              ? error.message
              : "Couldn’t save. Check your connection and try again.",
        },
      ]);
    if (existing) {
      const changed = changedFields(existing, fields);
      if (Object.keys(changed).length === 0) {
        navigate(back);
        return;
      }
      update.mutate(changed, {
        onSuccess: () => navigate(back, { state: { notice: "Changes saved." } }),
        onError,
      });
    } else {
      create.mutate(fields, {
        onSuccess: (created) =>
          navigate(`/properties/${created.id}`, { state: { notice: "Property added." } }),
        onError,
      });
    }
  }

  const err = (id: string) =>
    errors[id] ? (
      <span id={`${id}-error`} className={f.error}>
        <span className="visually-hidden">Error: </span>
        {errors[id]}
      </span>
    ) : null;
  const shareNow =
    values.share === "other"
      ? parsePercentage(values.otherShare)
      : { ok: true, value: values.share };
  const shareChanged =
    existing !== undefined &&
    shareNow.ok &&
    shareNow.value !== "" &&
    shareNow.value !== trimPercentage(existing.ownership_percentage);

  return (
    <div className={s.formPage}>
      <BackLink to={back}>{existing ? "Back to the property" : "All properties"}</BackLink>
      <h1 id="page-heading" tabIndex={-1}>
        {existing ? `Edit ${existing.nickname}` : "Add a property"}
      </h1>
      <ErrorSummary errors={summary} />

      <form className={s.form} onSubmit={submit} noValidate>
        <Text
          id="p-nickname"
          label="Name"
          hint="What you call it. It’s only shown to you, for example “Flat 4” or “Oak Road”."
          value={values.nickname}
          onChange={(v) => set("nickname", v)}
          error={err("p-nickname")}
          invalid={Boolean(errors["p-nickname"])}
        />

        <fieldset className={s.address}>
          <legend className={f.label}>Address</legend>
          <Text
            id="p-line1"
            label="Address line 1"
            value={values.line1}
            onChange={(v) => set("line1", v)}
            error={err("p-line1")}
            invalid={Boolean(errors["p-line1"])}
            autoComplete="address-line1"
          />
          <Text
            id="p-line2"
            label="Address line 2 (optional)"
            value={values.line2}
            onChange={(v) => set("line2", v)}
            autoComplete="address-line2"
          />
          <Text
            id="p-town"
            label="Town or city"
            value={values.town}
            onChange={(v) => set("town", v)}
            error={err("p-town")}
            invalid={Boolean(errors["p-town"])}
            autoComplete="address-level2"
            narrow
          />
          <Text
            id="p-postcode"
            label="Postcode"
            value={values.postcode}
            onChange={(v) => set("postcode", v)}
            error={err("p-postcode")}
            invalid={Boolean(errors["p-postcode"])}
            autoComplete="postal-code"
            postcode
          />
        </fieldset>

        <fieldset
          className={`${f.choices} ${errors["p-share-100"] ? f.hasError : ""}`}
          aria-describedby={["p-share-hint", errors["p-share-100"] && "p-share-100-error"]
            .filter(Boolean)
            .join(" ")}
        >
          <legend>How much of it do you own?</legend>
          <span id="p-share-hint" className={f.hint}>
            Your share for tax. Married couples and civil partners are taxed half each, unless
            you’ve told HMRC otherwise on Form 17.
          </span>
          {err("p-share-100")}
          <div className={f.options}>
            <label className={f.choice}>
              <input
                id="p-share-100"
                type="radio"
                name="share"
                checked={values.share === "100"}
                onChange={() => set("share", "100")}
              />
              All of it
            </label>
            <label className={f.choice}>
              <input
                type="radio"
                name="share"
                checked={values.share === "50"}
                onChange={() => set("share", "50")}
              />
              Half
            </label>
            <label className={f.choice}>
              <input
                type="radio"
                name="share"
                checked={values.share === "other"}
                onChange={() => set("share", "other")}
              />
              Another share
            </label>
          </div>
          {values.share === "other" && (
            <div className={`${f.field} ${errors["p-other-share"] ? f.hasError : ""}`}>
              <label className={f.label} htmlFor="p-other-share">
                Your share
              </label>
              {err("p-other-share")}
              <div className={s.percent}>
                <input
                  id="p-other-share"
                  className={f.control}
                  inputMode="decimal"
                  value={values.otherShare}
                  onChange={(e) => set("otherShare", e.target.value)}
                  aria-invalid={errors["p-other-share"] ? true : undefined}
                  aria-describedby={errors["p-other-share"] ? "p-other-share-error" : undefined}
                />
                <span aria-hidden="true">%</span>
              </div>
            </div>
          )}
        </fieldset>

        {shareChanged && (
          <p className={s.warning} role="status">
            Changing your share changes this property’s figures for the whole tax year, including
            quarters you’ve already sent. Send the latest quarter again, or your next update will
            correct them.
          </p>
        )}

        <div className={s.actions}>
          <Button type="submit" size="large" disabled={saving}>
            {saving ? "Saving…" : existing ? "Save changes" : "Add property"}
          </Button>
          <ButtonLink to={back} variant="quiet">
            Cancel
          </ButtonLink>
        </div>
      </form>
    </div>
  );
}

/** Only what changed, so an edit never rewrites fields the landlord didn't touch. */
function changedFields(p: Property, next: PropertyFields): Partial<PropertyFields> {
  const changed: Partial<PropertyFields> = {};
  if (next.nickname !== p.nickname) changed.nickname = next.nickname;
  if (next.address_line_1 !== p.address_line_1) changed.address_line_1 = next.address_line_1;
  if (next.address_line_2 !== (p.address_line_2 ?? null))
    changed.address_line_2 = next.address_line_2;
  if (next.town !== p.town) changed.town = next.town;
  if (next.postcode.replace(/\s+/g, "").toUpperCase() !== p.postcode.replace(/\s+/g, ""))
    changed.postcode = next.postcode;
  if (next.ownership_percentage !== trimPercentage(p.ownership_percentage))
    changed.ownership_percentage = next.ownership_percentage;
  return changed;
}

function Text({
  id,
  label,
  hint,
  value,
  onChange,
  error,
  invalid = false,
  autoComplete,
  narrow = false,
  postcode = false,
}: {
  id: string;
  label: string;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
  error?: ReactNode;
  invalid?: boolean;
  autoComplete?: string;
  narrow?: boolean;
  postcode?: boolean;
}) {
  const describedBy = [hint && `${id}-hint`, invalid && `${id}-error`].filter(Boolean).join(" ");
  return (
    <div className={`${f.field} ${invalid ? f.hasError : ""}`}>
      <label className={f.label} htmlFor={id}>
        {label}
      </label>
      {hint && (
        <span id={`${id}-hint`} className={f.hint}>
          {hint}
        </span>
      )}
      {error}
      <input
        id={id}
        className={`${f.control} ${narrow ? s.narrow : ""} ${postcode ? s.postcode : ""}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete={autoComplete ?? "off"}
        autoCapitalize={postcode ? "characters" : undefined}
        spellCheck={false}
        aria-invalid={invalid ? true : undefined}
        aria-describedby={describedBy || undefined}
      />
    </div>
  );
}
