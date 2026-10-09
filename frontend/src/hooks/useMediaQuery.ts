import { useSyncExternalStore } from "react";

/** True while a CSS media query matches. Used where layouts differ in structure, not just style. */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const list = window.matchMedia(query);
      list.addEventListener("change", onChange);
      return () => list.removeEventListener("change", onChange);
    },
    () => window.matchMedia(query).matches,
    () => false,
  );
}

export const WIDE = "(min-width: 768px)";
export const LAPTOP = "(min-width: 1200px)";
