import { sentFigures } from "./sentFigures";

it("adds up what was sent, in whole pence", () => {
  const body = {
    fromDate: "2026-04-06",
    toDate: "2026-10-05",
    ukProperty: {
      income: { periodAmount: 12000, otherIncome: 0.1, premiumsOfLeaseGrant: 0.2 },
      expenses: {
        premisesRunningCosts: 312.4,
        repairsAndMaintenance: 640,
        professionalFees: 864,
        residentialFinancialCost: 2940,
      },
    },
  };
  // 0.1 + 0.2 is 0.30000000000000004 in floating point; in pence it's exactly 30.
  expect(sentFigures(body)).toEqual({
    income: 1200030,
    expenses: 181640,
    financeCosts: 294000,
    consolidated: false,
  });
});

it("knows when expenses went as one total", () => {
  const body = {
    ukProperty: {
      income: { periodAmount: 100 },
      expenses: { consolidatedExpenses: 50.5, residentialFinancialCost: 10 },
    },
  };
  expect(sentFigures(body)).toMatchObject({ expenses: 5050, consolidated: true });
});
