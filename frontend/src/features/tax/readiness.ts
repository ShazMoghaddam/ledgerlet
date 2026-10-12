/**
 * Can this quarter be sent to HMRC now, and if not, what's in the way? Used by the
 * quarter page and by Review and submit, so both always agree.
 */
import { useHmrcConnection, useTaxpayer } from "../../api/queries";
import { formatShort } from "../../lib/dates";
import type { Quarter } from "../../lib/quarters";

export interface Check {
  ok: boolean | undefined; // undefined: neither done nor a problem (still checking, or a note)
  text: string;
}

export type Blocker = "not_ended" | "connect" | "details" | "checking" | "unavailable";

export interface Readiness {
  checks: Check[];
  /** The one thing in the way, or undefined when it can be sent. */
  blocker?: Blocker;
}

export function useReadiness(q: Quarter, earlier: Quarter[], today: string): Readiness {
  const connection = useHmrcConnection();
  const connected = connection.data?.connected === true;
  const taxpayer = useTaxpayer(connected);
  const ended = today > q.windowEnd;
  const business = Boolean(taxpayer.data?.nino && taxpayer.data.uk_property_business_id);

  const checks: Check[] = [
    {
      ok: ended,
      text: ended
        ? `Quarter ended ${formatShort(q.windowEnd)}`
        : `Quarter ends ${formatShort(q.windowEnd)}`,
    },
    connection.isPending
      ? { ok: undefined, text: "Checking your HMRC connection…" }
      : connection.isError
        ? { ok: false, text: "Couldn’t check your HMRC connection" }
        : connected
          ? { ok: true, text: "Connected to HMRC" }
          : { ok: false, text: "Not connected to HMRC" },
  ];
  if (connected)
    checks.push(
      taxpayer.isPending
        ? { ok: undefined, text: "Finding your details at HMRC…" }
        : taxpayer.isError
          ? { ok: false, text: "Couldn’t find your details at HMRC" }
          : business
            ? { ok: true, text: "National Insurance number and property business found" }
            : { ok: false, text: "National Insurance number or property business missing" },
    );
  const unsent = earlier.filter((x) => x.state.kind !== "sent");
  if (earlier.length > 0)
    checks.push(
      unsent.length === 0
        ? { ok: true, text: `${quarterNames(earlier)} already sent` }
        : {
            ok: undefined,
            text: `${quarterNames(unsent)} ${unsent.length === 1 ? "wasn’t" : "weren’t"} sent. This update covers ${unsent.length === 1 ? "it" : "them"} too.`,
          },
    );

  const blocker: Blocker | undefined = !ended
    ? "not_ended"
    : connection.isPending || (connected && taxpayer.isPending)
      ? "checking"
      : connection.isError || taxpayer.isError
        ? "unavailable"
        : !connected
          ? "connect"
          : !business
            ? "details"
            : undefined;
  return { checks, blocker };
}

/** "Quarter 1", "Quarters 1 and 2", "Quarters 1, 2 and 3". */
export function quarterNames(quarters: Quarter[]): string {
  const n = quarters.map((x) => x.quarter);
  if (n.length === 1) return `Quarter ${n[0]}`;
  return `Quarters ${n.slice(0, -1).join(", ")} and ${n[n.length - 1]}`;
}

/** Where to fix the connection, coming back here afterwards. */
export const hmrcSettingsPath = (comeBackTo: string) =>
  `/settings/hmrc?next=${encodeURIComponent(comeBackTo)}`;
