/**
 * The one way the app talks to the API. Paths, parameters and responses are all
 * typed from the backend's own OpenAPI description, so a backend change that the
 * frontend doesn't handle fails the type check instead of failing in the browser.
 */
import createClient, { type Middleware } from "openapi-fetch";

import { getToken, signOut } from "../auth/session";
import { deviceHeader } from "./device";
import type { paths } from "./schema";

const auth: Middleware = {
  onRequest({ request }) {
    const token = getToken();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    if (new URL(request.url).pathname.startsWith("/api/v1/hmrc/")) {
      request.headers.set("X-LedgerLet-Device", deviceHeader());
    }
    return request;
  },
  onResponse({ response }) {
    // Expired or invalid sign-in: drop it, and the app shows the sign-in page.
    if (response.status === 401) signOut();
    return response;
  },
};

export const api = createClient<paths>({
  baseUrl: window.location.origin,
  // Look fetch up on each call (not once at start-up), so test mocks can stand in for it.
  fetch: (request) => globalThis.fetch(request),
});
api.use(auth);

/** An API failure, with the server's own message when it sent one. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Unwrap an openapi-fetch result: the data, or an ApiError with a message a person can act on. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.data !== undefined) return result.data;
  // A 204 (deleted, nothing to return) has no body and that's success.
  if (result.response.ok) return undefined as T;
  throw new ApiError(result.response.status, messageFor(result.response.status, result.error));
}

function messageFor(status: number, error: unknown): string {
  const detail = (error as { detail?: unknown } | undefined)?.detail;
  if (typeof detail === "string") return detail;
  // FastAPI validation errors: a list of {msg} objects, or of strings.
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((d) => (typeof d === "string" ? d : String((d as { msg?: unknown }).msg ?? "")))
      .filter(Boolean)
      .join(". ");
  }
  if (status >= 500) return "Something went wrong on LedgerLet’s side. Try again in a moment.";
  if (status === 404) return "It may have been deleted, or the link is wrong.";
  return `The request didn’t work (${status}).`;
}
