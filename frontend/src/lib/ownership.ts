/** How much of a property the landlord owns, from the API's "50.00" style percentage. */

/** "100.00" -> "100", "50.50" -> "50.5". Trims zeros after the point only. */
export function trimPercentage(percentage: string): string {
  return percentage.includes(".") ? percentage.replace(/0+$/, "").replace(/\.$/, "") : percentage;
}

export const ownsAll = (percentage: string) => trimPercentage(percentage) === "100";

/** "You own all", "You own half", "You own 25%". */
export function ownershipText(percentage: string): string {
  const p = trimPercentage(percentage);
  if (p === "100") return "You own all";
  if (p === "50") return "You own half";
  return `You own ${p}%`;
}
