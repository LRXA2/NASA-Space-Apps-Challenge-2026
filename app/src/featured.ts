import picks from "./featured.json";

// The three featured patches per region (team decision T6, docs/featured-tiles.md). They are choices for the demo,
// not results: every number shown about them is read from the exported data. scripts/check_browser.mjs checks
// that each pick still fits its kind, so re-check featured.json if a new export makes that check fail.

export type FeaturedKind = "strong" | "misleading" | "not_atacama";

export const FEATURED_KINDS: { kind: FeaturedKind; title: string; why: string }[] = [
  {
    kind: "strong",
    title: "Strong match",
    why: "A close shape match whose physical measurements agree as well.",
  },
  {
    kind: "misleading",
    title: "Looks alike, measures different",
    why: "A high cosine, but the physical checks disagree. Shape similarity alone is not enough.",
  },
  {
    kind: "not_atacama",
    title: "Match outside Atacama",
    why: "Atacama supplies most best matches because it has the most Earth patches. This one comes from elsewhere.",
  },
];

/** The featured patch slugs for a region, or undefined when the region has none. */
export function featuredFor(region: string): Record<FeaturedKind, string> | undefined {
  return (picks as Record<string, Record<FeaturedKind, string>>)[region];
}
