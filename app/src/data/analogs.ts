import { DataError, decodePatch, loadAnalogs, loadEarth, loadGridFile, loadPatches, loadRegions } from "./loaders";
import type {
  AnalogMatch,
  AnalogsDocument,
  EarthCandidate,
  EarthDocument,
  PatchRecord,
  PatchesDocument,
  RegionEntry,
  TerrainChannel,
  TileAnalogs,
} from "./types";

export interface PatchAnalogs {
  entry: RegionEntry;
  patches: PatchesDocument;
  record: PatchRecord;
  analogs: AnalogsDocument;
  /** Undefined when this patch has no Earth matches in the build. */
  tile: TileAnalogs | undefined;
  earth: EarthDocument;
}

/** Everything an analog or pair page needs for one lunar patch. Unknown names give readable errors. */
export async function loadPatchAnalogs(region: string, patch: string): Promise<PatchAnalogs> {
  const entry = (await loadRegions()).regions.find((candidate) => candidate.slug === region);
  if (!entry) throw new DataError(`No region named "${region}" is in this build.`);
  const [patches, analogs, earth] = await Promise.all([
    loadPatches(entry.patches_file),
    loadAnalogs(entry.analogs_file),
    loadEarth(),
  ]);
  const record = patches.patches.find((candidate) => candidate.slug === patch);
  if (!record) throw new DataError(`No patch named "${patch}" is in this build of ${patches.region.name}.`);
  return { entry, patches, record, analogs, tile: analogs.tiles[patch], earth };
}

export function candidateOf(earth: EarthDocument, match: AnalogMatch): EarthCandidate {
  const candidate = earth.candidates[match.candidate];
  if (!candidate) throw new DataError("A match points at an Earth patch that is missing from this build.");
  return candidate;
}

export function siteName(earth: EarthDocument, site: string): string {
  return earth.sites.find((entry) => entry.id === site)?.name ?? site;
}

/** "all five Earth sites, top 3 from each": the candidate pool, stated on every result list. */
export function poolLabel(analogs: AnalogsDocument, earth: EarthDocument): string {
  const { sites, top_k_per_site } = analogs.candidate_pool;
  const names = sites.map((site) => siteName(earth, site));
  const count = sites.length === 5 ? "all five Earth sites" : `${sites.length} Earth sites (${names.join(", ")})`;
  return `${count}, top ${top_k_per_site} from each`;
}

export async function loadEarthTerrain(earth: EarthDocument, candidate: EarthCandidate): Promise<TerrainChannel[]> {
  return decodePatch(await loadGridFile(earth.grid), earth.grid, candidate.grid_offset);
}

export async function loadMoonTerrain(patches: PatchesDocument, record: PatchRecord): Promise<TerrainChannel[]> {
  return decodePatch(await loadGridFile(patches.grid), patches.grid, record.grid_offset);
}

// The similarity pipeline's relief is the 5th-to-95th-percentile height range. The patch page shows the full
// range (highest minus lowest) from the walkability pipeline, so the two numbers differ for the same terrain.
const CHECK_LABELS: Record<string, string> = {
  central_relief_m: "Relief, 5th to 95th percentile (m)",
};

/** A physical check's label for display. Overrides labels that would be confused with another page's measure. */
export function checkLabel(check: { name: string; label: string }): string {
  return CHECK_LABELS[check.name] ?? check.label;
}

/**
 * The match a pair URL names. Takes the Earth patch ID (the canonical form) or the candidate's number in
 * earth/candidates.json, which is what the analogs file stores.
 */
export function findMatch(earth: EarthDocument, matches: AnalogMatch[], id: string): AnalogMatch | undefined {
  const byId = matches.find((entry) => candidateOf(earth, entry).id === id);
  if (byId || !/^\d+$/.test(id)) return byId;
  return matches.find((entry) => entry.candidate === Number(id));
}

export function checksWithin(match: AnalogMatch): number {
  return match.within.filter(Boolean).length;
}

/** The match with the most physical checks in band. Ties go to the better (lower) rank. */
export function bestFit(matches: AnalogMatch[]): AnalogMatch | undefined {
  return matches.reduce<AnalogMatch | undefined>(
    (best, match) => (!best || checksWithin(match) > checksWithin(best) ? match : best),
    undefined,
  );
}

/** A site's short name for buttons and tiles: "Atacama (San Pedro), Chile" gives "Atacama". */
export function shortSiteName(earth: EarthDocument, site: string): string {
  return siteName(earth, site).split(/[,(]/)[0].trim();
}
