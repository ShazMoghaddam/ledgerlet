/**
 * What each quarter of the tax year means to the landlord right now.
 *
 * The tax module knows the dates and deadlines; the HMRC submission history knows
 * what's been sent. This combines them into one state per quarter, in the words
 * the interface uses, and picks the single next thing to do.
 *
 * Updates are cumulative, so sending quarter 2 also covers quarter 1. A quarter is
 * "sent" if it, or any later quarter, was accepted by HMRC.
 */
import type { Obligation, Submission } from "../api/types";
import { addDays, type IsoDate } from "./dates";

export type QuarterState =
  | { kind: "sent"; on: IsoDate; viaQuarter: number }
  | { kind: "ready"; deadline: IsoDate }
  | { kind: "overdue"; deadline: IsoDate }
  | { kind: "in_progress"; ends: IsoDate }
  | { kind: "not_started"; starts: IsoDate };

export interface Quarter {
  quarter: number;
  /** The quarter's own three months (the API's period is cumulative from 6 April). */
  windowStart: IsoDate;
  windowEnd: IsoDate;
  deadline: IsoDate;
  state: QuarterState;
}

export function quarterStates(
  obligations: Obligation[],
  submissions: Submission[],
  today: IsoDate,
): Quarter[] {
  const sorted = [...obligations].sort((a, b) => a.quarter - b.quarter);
  const accepted = submissions.filter((s) => s.succeeded);

  return sorted.map((o, i) => {
    const previous = sorted[i - 1];
    const windowStart = previous ? addDays(previous.period_end, 1) : o.period_start;
    const base = { quarter: o.quarter, windowStart, windowEnd: o.period_end, deadline: o.deadline };

    const covering = accepted
      .filter((s) => s.quarter >= o.quarter)
      .sort((a, b) => a.submitted_at.localeCompare(b.submitted_at))[0];
    if (covering) {
      const on = covering.submitted_at.slice(0, 10);
      return { ...base, state: { kind: "sent", on, viaQuarter: covering.quarter } };
    }
    switch (o.status) {
      case "due":
        return { ...base, state: { kind: "ready", deadline: o.deadline } };
      case "past_deadline":
        return { ...base, state: { kind: "overdue", deadline: o.deadline } };
      case "not_started":
        return { ...base, state: { kind: "not_started", starts: windowStart } };
      case "open":
        return today < windowStart
          ? { ...base, state: { kind: "not_started", starts: windowStart } }
          : { ...base, state: { kind: "in_progress", ends: o.period_end } };
    }
  });
}

export type NextStep =
  | { kind: "send"; quarter: Quarter; overdue: boolean }
  | { kind: "wait"; quarter: Quarter }
  | { kind: "year_done" };

/** The earliest quarter that needs sending; otherwise the one being recorded now. */
export function nextStep(quarters: Quarter[]): NextStep {
  for (const q of quarters) {
    if (q.state.kind === "overdue") return { kind: "send", quarter: q, overdue: true };
    if (q.state.kind === "ready") return { kind: "send", quarter: q, overdue: false };
  }
  const current = quarters.find((q) => q.state.kind === "in_progress");
  if (current) return { kind: "wait", quarter: current };
  const upcoming = quarters.find((q) => q.state.kind === "not_started");
  return upcoming ? { kind: "wait", quarter: upcoming } : { kind: "year_done" };
}

/** The quarter whose figures are "year to date": the latest one that has begun. */
export function currentQuarter(quarters: Quarter[]): Quarter | undefined {
  return [...quarters].reverse().find((q) => q.state.kind !== "not_started");
}
