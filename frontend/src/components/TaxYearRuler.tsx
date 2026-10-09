import { daysBetween, formatShort, fractionOfSpan, type IsoDate } from "../lib/dates";
import type { Quarter } from "../lib/quarters";
import s from "./TaxYearRuler.module.css";

const MONTHS = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"];

interface Props {
  quarters: Quarter[];
  today: IsoDate;
  label: string; // e.g. "Tax year 2026-27"
}

export function TaxYearRuler({ quarters, today, label }: Props) {
  const first = quarters[0];
  const last = quarters[quarters.length - 1];
  if (!first || !last) return null;
  const start = first.windowStart;
  const end = last.windowEnd;
  const at = (day: IsoDate) => fractionOfSpan(day, start, end) * 100;
  const todayAt = at(today);
  const inYear = daysBetween(start, today) >= 0 && daysBetween(today, end) >= 0;

  return (
    <figure className={s.ruler} aria-label={label}>
      <div className={s.track} aria-hidden="true">
        {quarters.map((q) => {
          const left = at(q.windowStart);
          const width = at(q.windowEnd) - left;
          const progress =
            q.state.kind === "in_progress"
              ? Math.max(2, ((todayAt - left) / width) * 100)
              : undefined;
          return (
            <span
              key={q.quarter}
              className={`${s.segment} ${s[q.state.kind]}`}
              style={{ left: `${left}%`, width: `${width}%` }}
            >
              {progress !== undefined && (
                <span className={s.progress} style={{ width: `${progress}%` }} />
              )}
            </span>
          );
        })}
        {inYear && (
          <span className={s.today} style={{ left: `${todayAt}%` }}>
            <span className={`${s.todayLabel} ${todayAt > 80 ? s.todayLabelLeft : ""}`}>
              Today, {formatShort(today)}
            </span>
          </span>
        )}
      </div>

      <div className={s.months} aria-hidden="true">
        {MONTHS.map((m) => (
          <span key={m}>{m}</span>
        ))}
      </div>

      <ol className={s.labels}>
        {quarters.map((q) => (
          <QuarterLabel key={q.quarter} quarter={q} />
        ))}
      </ol>
    </figure>
  );
}

function QuarterLabel({ quarter: q }: { quarter: Quarter }) {
  // Screen readers always hear "Quarter 2"; a phone shows "Q2".
  const name = (
    <strong>
      <span className={s.long}>Quarter </span>
      <span className={s.short} aria-hidden="true">
        Q
      </span>
      {q.quarter}
    </strong>
  );
  switch (q.state.kind) {
    case "sent":
      return (
        <li>
          {name}Sent {formatShort(q.state.on)}
        </li>
      );
    case "ready":
      return (
        <li className={s.labelReady}>
          {name}
          <span className={s.state}>Ready to send</span>
          <span className={`${s.muted} ${s.detail}`}>, due {formatShort(q.state.deadline)}</span>
        </li>
      );
    case "overdue":
      return (
        <li className={s.labelOverdue}>
          {name}
          <span className={s.state}>Overdue</span>
          <span className={s.detail}>, was due {formatShort(q.state.deadline)}</span>
        </li>
      );
    case "in_progress":
      return (
        <li>
          {name}In progress<span className={s.detail}>, ends {formatShort(q.state.ends)}</span>
        </li>
      );
    case "not_started":
      return (
        <li>
          {name}
          <span className={s.muted}>Not started</span>
        </li>
      );
  }
}
