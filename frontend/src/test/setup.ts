import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";

import { server } from "./server";

// jsdom has <dialog> but not its methods; these behave like the browser's for tests.
HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
  this.open = true;
};
HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
  this.open = false;
  this.dispatchEvent(new Event("close"));
};

/**
 * jsdom has no layout, so no matchMedia. This one answers min-width queries from
 * window.innerWidth, which tests set to try phone, tablet and laptop layouts.
 */
window.matchMedia = (query: string) => {
  const min = /min-width:\s*(\d+)px/.exec(query);
  const matches = min ? window.innerWidth >= Number(min[1]) : false;
  return {
    matches,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  } as MediaQueryList;
};

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  cleanup();
  sessionStorage.clear();
});
afterAll(() => server.close());
