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

/**
 * Read a share typed by the landlord ("50", "33.33", "12.5%") into the exact string
 * the API takes. Never via a float, so 33.33 stays 33.33.
 */
export function parsePercentage(
  raw: string,
): { ok: true; value: string } | { ok: false; error: string } {
  const text = raw.trim().replace(/%$/, "").trim();
  if (!text) return { ok: false, error: "Enter your share, as a percentage" };
  if (!/^\d{1,3}(\.\d{1,2})?$/.test(text))
    return { ok: false, error: "Enter your share as a number, like 50 or 33.33" };
  const [whole = "0", part = ""] = text.split(".");
  const hundredths = Number(whole) * 100 + Number(part.padEnd(2, "0"));
  if (hundredths === 0) return { ok: false, error: "Your share must be more than 0%" };
  if (hundredths > 10000) return { ok: false, error: "Your share can’t be more than 100%" };
  return { ok: true, value: trimPercentage(`${Number(whole)}.${part.padEnd(2, "0")}`) };
}

/** The same postcode shape the API accepts, so most typos are caught before saving. */
const UK_POSTCODE =
  /^(GIR0AA|[A-PR-UWYZ]([0-9]{1,2}|[A-HK-Y][0-9]{1,2}|[0-9][A-HJKPS-UW]|[A-HK-Y][0-9][ABEHMNPRV-Y])[0-9][ABD-HJLNP-UW-Z]{2})$/;

export function looksLikePostcode(raw: string): boolean {
  return UK_POSTCODE.test(raw.replace(/\s+/g, "").toUpperCase());
}
