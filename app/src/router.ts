import { useSyncExternalStore } from "react";

// Hash routes (#/region/...) work on any static host without rewrite rules.
// This file is the only place that knows the URL form.

export type Route =
  | { name: "regions" }
  | { name: "region"; region: string }
  | { name: "patch"; region: string; patch: string }
  | { name: "not-found"; path: string };

export function parseRoute(hash: string): Route {
  const path = hash.replace(/^#/, "").replace(/\/+$/, "") || "/";
  let parts: string[];
  try {
    parts = path.split("/").filter(Boolean).map(decodeURIComponent);
  } catch {
    return { name: "not-found", path };
  }
  if (parts.length === 0) return { name: "regions" };
  if (parts[0] === "region" && parts.length === 2) return { name: "region", region: parts[1] };
  if (parts[0] === "region" && parts[2] === "patch" && parts.length === 4) {
    return { name: "patch", region: parts[1], patch: parts[3] };
  }
  return { name: "not-found", path };
}

export const links = {
  regions: () => "#/",
  region: (region: string) => `#/region/${encodeURIComponent(region)}`,
  patch: (region: string, patch: string) =>
    `#/region/${encodeURIComponent(region)}/patch/${encodeURIComponent(patch)}`,
};

function subscribe(notify: () => void): () => void {
  window.addEventListener("hashchange", notify);
  return () => window.removeEventListener("hashchange", notify);
}

export function useRoute(): Route {
  const hash = useSyncExternalStore(subscribe, () => window.location.hash);
  return parseRoute(hash);
}
