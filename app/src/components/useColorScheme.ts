import { useSyncExternalStore } from "react";
import type { Scheme } from "./colorScales";

const QUERY = "(prefers-color-scheme: dark)";

function subscribe(notify: () => void): () => void {
  const media = window.matchMedia(QUERY);
  media.addEventListener("change", notify);
  return () => media.removeEventListener("change", notify);
}

export function useColorScheme(): Scheme {
  return useSyncExternalStore(subscribe, () => (window.matchMedia(QUERY).matches ? "dark" : "light"));
}
