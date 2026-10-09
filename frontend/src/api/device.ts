/**
 * Facts about this device that HMRC's fraud prevention rules require us to pass on
 * (the Gov-Client-* headers). The server builds the headers; the browser supplies
 * what only the browser knows, as JSON in X-LedgerLet-Device.
 *
 * The device id is random, kept in this browser, and only identifies the device to
 * HMRC. It isn't linked to anything else.
 */

const KEY = "ledgerlet.device-id";

function deviceId(): string {
  try {
    const existing = localStorage.getItem(KEY);
    if (existing) return existing;
    const created = crypto.randomUUID();
    localStorage.setItem(KEY, created);
    return created;
  } catch {
    return crypto.randomUUID(); // storage blocked: a fresh id per page load
  }
}

export function deviceHeader(): string {
  return JSON.stringify({
    device_id: deviceId(),
    js_user_agent: navigator.userAgent,
    screens: [
      {
        width: screen.width,
        height: screen.height,
        scaling_factor: window.devicePixelRatio,
        colour_depth: screen.colorDepth,
      },
    ],
    window_width: window.innerWidth,
    window_height: window.innerHeight,
    utc_offset_minutes: -new Date().getTimezoneOffset(),
  });
}
