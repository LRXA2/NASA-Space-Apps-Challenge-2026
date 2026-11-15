import { useSyncExternalStore } from "react";

// Hash routes (#/region/...) work on any static host without rewrite rules.
// This file is the only place that knows the URL form.

export type Route =
  | { name: "regions" }
  | { name: "region"; region: string }
  | { name: "patch"; region: string; patch: string }
  | { name: "analogs"; region: string; patch: string }
  | { name: "pair"; region: string; patch: string; candidate: string }
  | { name: "environment" }
  | { name: "scenario"; scenario: string }
  | { name: "upload" }
  | { name: "not-found"; path: string };

function parseRoute(hash: string): Route {
  const path = hash.replace(/^#/, "").replace(/\/+$/, "") || "/";
  let parts: string[];
  try {
    parts = path.split("/").filter(Boolean).map(decodeURIComponent);
  } catch {
    return { name: "not-found", path };
  }
  if (parts.length === 0) return { name: "regions" };
  if (parts[0] === "region" && parts.length === 2) return { name: "region", region: parts[1] };
  if (parts[0] === "region" && parts[2] === "patch") {
    if (parts.length === 4) return { name: "patch", region: parts[1], patch: parts[3] };
    if (parts.length === 5 && parts[4] === "analogs") return { name: "analogs", region: parts[1], patch: parts[3] };
    if (parts.length === 6 && parts[4] === "analogs") {
      return { name: "pair", region: parts[1], patch: parts[3], candidate: parts[5] };
    }
  }
  if (parts[0] === "environment" && parts.length === 1) return { name: "environment" };
  if (parts[0] === "environment" && parts.length === 2) return { name: "scenario", scenario: parts[1] };
  if (parts[0] === "upload" && parts.length === 1) return { name: "upload" };
  return { name: "not-found", path };
}

const part = encodeURIComponent;

export const links = {
  regions: () => "#/",
  region: (region: string) => `#/region/${part(region)}`,
  patch: (region: string, patch: string) => `#/region/${part(region)}/patch/${part(patch)}`,
  analogs: (region: string, patch: string) => `#/region/${part(region)}/patch/${part(patch)}/analogs`,
  /** Keyed on the Earth candidate ID, not the rank: rank changes when the candidate pool grows. */
  pair: (region: string, patch: string, candidate: string) =>
    `#/region/${part(region)}/patch/${part(patch)}/analogs/${part(candidate)}`,
  environment: () => "#/environment",
  scenario: (scenario: string) => `#/environment/${part(scenario)}`,
  upload: () => "#/upload",
};

function subscribe(notify: () => void): () => void {
  window.addEventListener("hashchange", notify);
  return () => window.removeEventListener("hashchange", notify);
}

export function useRoute(): Route {
  const hash = useSyncExternalStore(subscribe, () => window.location.hash);
  return parseRoute(hash);
}
