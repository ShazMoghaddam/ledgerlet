import { AlertIcon } from "../../components/Icons";
import { formatShort } from "../../lib/dates";
import type { Quarter } from "../../lib/quarters";
import s from "./Tax.module.css";

/**
 * A quarter's state in a few words. Never colour alone: "Ready to send" and
 * "Overdue" are spelled out, and the dot and icon only repeat them.
 *
 * `known` is false when HMRC couldn't be asked what's been sent; then a quarter
 * that has ended is described by its dates only, never called overdue on a guess.
 */
export function QuarterStatus({ quarter: q, known = true }: { quarter: Quarter; known?: boolean }) {
  const state = q.state;
  if (!known && (state.kind === "ready" || state.kind === "overdue"))
    return <span>Ended {formatShort(q.windowEnd)}</span>;

  switch (state.kind) {
    case "sent":
      return (
        <span>
          Sent {formatShort(state.on)}
          {state.viaQuarter !== q.quarter && <>, in quarter {state.viaQuarter}’s update</>}
        </span>
      );
    case "ready":
      return (
        <span className={s.ready}>
          <span className={s.dot} aria-hidden="true" />
          Ready to send
        </span>
      );
    case "overdue":
      return (
        <span className={s.overdue}>
          <AlertIcon size={16} />
          Overdue
        </span>
      );
    case "in_progress":
      return <span>In progress</span>;
    case "not_started":
      return <span className={s.muted}>Not started</span>;
  }
}
