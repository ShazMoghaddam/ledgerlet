import { useEffect, useId, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router";

import { ApiError } from "../../api/client";
import { useHmrcConnection, useTaxpayer } from "../../api/queries";
import type { BusinessRead } from "../../api/types";
import { Button, ButtonLink } from "../../components/Button";
import { Dialog } from "../../components/Dialog";
import f from "../../components/Field.module.css";
import { Notice } from "../../components/Notice";
import { LoadFailed, Loading } from "../../components/QueryState";
import { usePageTitle } from "../../hooks/usePageTitle";
import { formatLong } from "../../lib/dates";
import {
  useConnect,
  useDisconnect,
  useDiscoverBusinesses,
  useSetBusiness,
  useSetNino,
} from "./mutations";
import s from "./Hmrc.module.css";

/** Why connecting failed, from the fixed codes the API sends back (never free text). */
const CONNECT_ERRORS: Record<string, string> = {
  declined:
    "You chose not to give LedgerLet access at HMRC. You can connect whenever you’re ready.",
  expired: "The approval took too long, so it ran out. Start again.",
  other_browser:
    "The approval finished in a different browser from the one it started in. Start again in this browser.",
  invalid: "HMRC’s reply couldn’t be checked, so it wasn’t used. Start again.",
  rejected: "HMRC didn’t accept the approval. Start again.",
  failed: "Connecting to HMRC didn’t work. Start again.",
};

/** A path inside the app (never another site): the same rule the API applies. */
const SAFE_PATH = /^\/([A-Za-z0-9_.~?=&%-][A-Za-z0-9/_.~?=&%-]*)?$/;

/** /settings/hmrc: connect, disconnect, and the details LedgerLet files under. */
export function HmrcSettingsPage() {
  usePageTitle("HMRC connection");
  const [params, setParams] = useSearchParams();
  const next = params.get("next");
  const comeBackTo = next && SAFE_PATH.test(next) ? next : undefined;

  // HMRC sends the browser back with ?hmrc=connected or ?hmrc=error&reason=…
  // Show the result once, then tidy the address so a refresh doesn't repeat it.
  const [outcome] = useState(() => ({ result: params.get("hmrc"), reason: params.get("reason") }));
  useEffect(() => {
    if (params.has("hmrc") || params.has("reason")) {
      const tidy = new URLSearchParams(params);
      tidy.delete("hmrc");
      tidy.delete("reason");
      setParams(tidy, { replace: true });
    }
  }, [params, setParams]);

  const connection = useHmrcConnection();
  const connected = connection.data?.connected === true;

  return (
    <div className={s.page}>
      <h1 id="page-heading" tabIndex={-1}>
        HMRC connection
      </h1>
      {outcome.result === "connected" && <Notice>Connected to HMRC.</Notice>}
      {outcome.result === "error" && (
        <p role="alert" className={s.problem}>
          {CONNECT_ERRORS[outcome.reason ?? ""] ?? CONNECT_ERRORS.failed}
        </p>
      )}

      {connection.isPending ? (
        <Loading label="your HMRC connection" />
      ) : connection.isError ? (
        <LoadFailed
          what="your HMRC connection"
          error={connection.error}
          retry={connection.refetch}
        />
      ) : (
        <>
          <ConnectionSection
            connected={connected}
            connectedAt={connection.data.connected_at}
            comeBackTo={comeBackTo}
          />
          <DetailsSection connected={connected} comeBackTo={comeBackTo} />
        </>
      )}
    </div>
  );
}

function ConnectionSection({
  connected,
  connectedAt,
  comeBackTo,
}: {
  connected: boolean;
  connectedAt?: string | null;
  comeBackTo?: string;
}) {
  const connect = useConnect();
  const returnTo = comeBackTo
    ? `/settings/hmrc?next=${encodeURIComponent(comeBackTo)}`
    : "/settings/hmrc";

  return (
    <section className={s.section} aria-labelledby="connection-heading">
      <h2 id="connection-heading">Connection</h2>
      {connected ? (
        <>
          <dl className={s.facts}>
            <dt>Status</dt>
            <dd>Connected</dd>
            {connectedAt && (
              <>
                <dt>Since</dt>
                <dd>{formatLong(connectedAt.slice(0, 10))}</dd>
              </>
            )}
            <dt>Allows</dt>
            <dd>Reading and sending your Making Tax Digital updates</dd>
          </dl>
          <DisconnectButton />
        </>
      ) : (
        <>
          <p className={s.prose}>
            LedgerLet needs your permission to send updates to HMRC. You’ll sign in on HMRC’s own
            website with your Government Gateway user ID, approve LedgerLet, and come straight back
            here. LedgerLet never sees your HMRC password.
          </p>
          {connect.isError && (
            <p role="alert" className={s.problem}>
              Couldn’t start connecting. {connect.error.message}
            </p>
          )}
          <div>
            <Button
              size="large"
              disabled={connect.isPending || connect.isSuccess}
              onClick={() => connect.mutate(returnTo)}
            >
              {connect.isPending || connect.isSuccess ? "Going to HMRC…" : "Connect to HMRC"}
            </Button>
          </div>
        </>
      )}
    </section>
  );
}

function DisconnectButton() {
  const [open, setOpen] = useState(false);
  const disconnect = useDisconnect();
  return (
    <>
      <div>
        <Button variant="secondary" onClick={() => setOpen(true)}>
          Disconnect
        </Button>
      </div>
      <Dialog open={open} onClose={() => setOpen(false)} title="Disconnect from HMRC?">
        <p className={s.prose}>
          LedgerLet won’t be able to send updates until you connect again. What you’ve already sent
          stays on record, here and at HMRC.
        </p>
        {disconnect.isError && (
          <p role="alert" className={s.problem}>
            {disconnect.error.message}
          </p>
        )}
        <div className={s.actions}>
          <Button
            variant="secondary"
            disabled={disconnect.isPending}
            onClick={() => disconnect.mutate(undefined, { onSuccess: () => setOpen(false) })}
          >
            {disconnect.isPending ? "Disconnecting…" : "Disconnect"}
          </Button>
          <Button variant="quiet" onClick={() => setOpen(false)}>
            Stay connected
          </Button>
        </div>
      </Dialog>
    </>
  );
}

function DetailsSection({ connected, comeBackTo }: { connected: boolean; comeBackTo?: string }) {
  const taxpayer = useTaxpayer();
  const [editingNino, setEditingNino] = useState(false);

  if (taxpayer.isPending) return <Loading label="your details at HMRC" />;
  if (taxpayer.isError)
    return (
      <LoadFailed what="your details at HMRC" error={taxpayer.error} retry={taxpayer.refetch} />
    );

  const { nino, uk_property_business_id: business } = taxpayer.data;
  const ready = connected && Boolean(nino && business);

  return (
    <section className={s.section} aria-labelledby="details-heading">
      <h2 id="details-heading">Your details at HMRC</h2>
      <p className={s.prose}>
        Updates are filed under your National Insurance number, for your UK property business.
      </p>

      <div className={s.detail}>
        <h3>National Insurance number</h3>
        {nino && !editingNino ? (
          <div className={s.valueRow}>
            <span className="num">{nino}</span>
            <Button variant="quiet" onClick={() => setEditingNino(true)}>
              Change<span className="visually-hidden"> National Insurance number</span>
            </Button>
          </div>
        ) : (
          <NinoForm changing={Boolean(nino)} onDone={() => setEditingNino(false)} />
        )}
      </div>

      <div className={s.detail}>
        <h3>UK property business</h3>
        {business ? (
          <p className="num">{business}</p>
        ) : !nino ? (
          <p className={s.muted}>Add your National Insurance number first.</p>
        ) : !connected ? (
          <p className={s.muted}>Connect to HMRC first, then LedgerLet can find it.</p>
        ) : (
          <FindBusiness />
        )}
      </div>

      {ready && comeBackTo && (
        <div>
          <ButtonLink to={comeBackTo} size="large">
            Continue where you left off
          </ButtonLink>
        </div>
      )}
    </section>
  );
}

function NinoForm({ changing, onDone }: { changing: boolean; onDone: () => void }) {
  const id = useId();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string>();
  const save = useSetNino();

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!value.trim()) {
      setError("Enter your National Insurance number");
      return;
    }
    save.mutate(value, {
      onSuccess: () => {
        setError(undefined);
        onDone();
      },
      onError: (err) =>
        setError(
          err instanceof ApiError && err.status === 422
            ? "Enter a National Insurance number in the right format, like QQ 12 34 56 C"
            : err.message,
        ),
    });
  }

  return (
    <form className={s.inlineForm} onSubmit={submit} noValidate>
      <div className={`${f.field} ${error ? f.hasError : ""}`}>
        <label className={f.label} htmlFor={`${id}-nino`}>
          {changing ? "New National Insurance number" : "National Insurance number"}
        </label>
        <span id={`${id}-hint`} className={f.hint}>
          It’s on your payslip, P60 or letters from HMRC. For example, QQ 12 34 56 C.
          {changing && " Changing it means finding your property business again."}
        </span>
        {error && (
          <span id={`${id}-error`} className={f.error}>
            {error}
          </span>
        )}
        <input
          id={`${id}-nino`}
          className={`${f.control} ${s.ninoInput}`}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          autoComplete="off"
          spellCheck={false}
          autoCapitalize="characters"
          aria-invalid={error ? true : undefined}
          aria-describedby={`${id}-hint${error ? ` ${id}-error` : ""}`}
        />
      </div>
      <div className={s.actions}>
        <Button type="submit" disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save"}
        </Button>
        {changing && (
          <Button variant="quiet" onClick={onDone}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}

/** Ask HMRC. One UK property business is chosen automatically; several, the landlord picks. */
function FindBusiness() {
  const discover = useDiscoverBusinesses();
  const choose = useSetBusiness();
  const found = discover.data;
  const property = (found?.businesses ?? []).filter((b) => b.type_of_business === "uk-property");

  return (
    <div className={s.find}>
      {!found && (
        <>
          <p className={s.muted}>LedgerLet asks HMRC which businesses you have registered.</p>
          <div>
            <Button
              variant="secondary"
              disabled={discover.isPending}
              onClick={() => discover.mutate()}
            >
              {discover.isPending ? "Asking HMRC…" : "Find my property business"}
            </Button>
          </div>
        </>
      )}
      {discover.isError && (
        <p role="alert" className={s.problem}>
          {discover.error.message}
        </p>
      )}
      {found && property.length === 0 && (
        <p role="status" className={s.problem}>
          HMRC has no UK property business for this National Insurance number. Check the number
          above, or register your property income with HMRC first.
        </p>
      )}
      {found && property.length > 1 && !found.selected_business_id && (
        <ChooseBusiness
          businesses={property}
          pending={choose.isPending}
          error={choose.error?.message}
          onChoose={(id) => choose.mutate(id)}
        />
      )}
    </div>
  );
}

function ChooseBusiness({
  businesses,
  pending,
  error,
  onChoose,
}: {
  businesses: BusinessRead[];
  pending: boolean;
  error?: string;
  onChoose: (id: string) => void;
}) {
  const [picked, setPicked] = useState("");
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (picked) onChoose(picked);
      }}
      className={s.inlineForm}
    >
      <fieldset className={f.choices}>
        <legend className={f.label}>HMRC has more than one. Which one is for your lettings?</legend>
        <div className={f.options}>
          {businesses.map((b) => (
            <label key={b.business_id} className={f.choice}>
              <input
                type="radio"
                name="business"
                value={b.business_id}
                checked={picked === b.business_id}
                onChange={() => setPicked(b.business_id)}
              />
              {b.trading_name ? `${b.trading_name} (${b.business_id})` : b.business_id}
            </label>
          ))}
        </div>
      </fieldset>
      {error && (
        <p role="alert" className={s.problem}>
          {error}
        </p>
      )}
      <div>
        <Button type="submit" disabled={!picked || pending}>
          {pending ? "Saving…" : "Use this business"}
        </Button>
      </div>
    </form>
  );
}
