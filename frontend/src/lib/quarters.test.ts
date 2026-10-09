import obligations from "../test/fixtures/obligations.json";
import { submissions } from "../test/fixtures/hmrc";
import type { Obligation, Submission } from "../api/types";
import { currentQuarter, nextStep, quarterStates } from "./quarters";

const ob = obligations.obligations as Obligation[];
const TODAY = "2026-10-09";

it("gives each quarter one state, as the design shows on 9 October", () => {
  const states = quarterStates(ob, submissions, TODAY).map((q) => q.state.kind);
  expect(states).toEqual(["sent", "ready", "in_progress", "not_started"]);
});

it("works out each quarter's own three months", () => {
  const [, q2, q3] = quarterStates(ob, submissions, TODAY);
  expect([q2?.windowStart, q2?.windowEnd]).toEqual(["2026-07-06", "2026-10-05"]);
  expect(q3?.windowStart).toBe("2026-10-06");
});

it("next step is sending quarter 2, not overdue", () => {
  const step = nextStep(quarterStates(ob, submissions, TODAY));
  expect(step).toMatchObject({ kind: "send", overdue: false, quarter: { quarter: 2 } });
});

it("an unsent quarter past its deadline comes first, and is overdue", () => {
  const states = quarterStates(ob, [], TODAY);
  expect(states[0]?.state.kind).toBe("overdue");
  expect(nextStep(states)).toMatchObject({ kind: "send", overdue: true, quarter: { quarter: 1 } });
});

it("a later update covers earlier quarters, because updates are cumulative", () => {
  const q2Sent: Submission = {
    ...submissions[0]!,
    quarter: 2,
    submitted_at: "2026-10-09T10:00:00Z",
  };
  const states = quarterStates(ob, [q2Sent], TODAY);
  expect(states[0]?.state).toEqual({ kind: "sent", on: "2026-10-09", viaQuarter: 2 });
  expect(nextStep(states)).toMatchObject({ kind: "wait", quarter: { quarter: 3 } });
});

it("failed attempts don't count as sent", () => {
  const failed: Submission = { ...submissions[0]!, succeeded: false, status_code: 422 };
  expect(quarterStates(ob, [failed], TODAY)[0]?.state.kind).toBe("overdue");
});

it("year to date is the latest quarter that has begun", () => {
  expect(currentQuarter(quarterStates(ob, submissions, TODAY))?.quarter).toBe(3);
});
