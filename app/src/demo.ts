import { loadRegions } from "./data/loaders";
import { useData } from "./data/useData";

// The demo walkthrough (design/exploration-theme/DESIGN.md, header "Demo path").
// The patch and the Earth candidate are choices for the live demo, not results: every number shown about
// them is read from the exported data. The candidate is the patch's best physical fit (most checks in band).
// Re-check all three after a new export: a different pipeline run can rank the Earth candidates differently.
export const DEMO = {
  region: "leibnitz-beta-plateau",
  patch: "r192-c192",
  candidate: "atacama_san_pedro:natural_screen:528:880:960",
} as const;

/**
 * False when the exported data has no demo region, for example after `export_data.py --region haworth`
 * (which scripts/prepare_demo runs). The demo links are then hidden instead of leading to an error page.
 * True while regions.json loads, so the header does not jump in the usual case.
 */
export function useDemoAvailable(): boolean {
  const regions = useData("regions", loadRegions);
  if (regions.status === "loading") return true;
  return regions.status === "ready" && regions.data.regions.some((entry) => entry.slug === DEMO.region);
}
