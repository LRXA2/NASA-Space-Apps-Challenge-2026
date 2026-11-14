// Shapes of the files written by app/scripts/export_data.py (schema version 2).

export const SCHEMA_VERSION = 2;

export interface RegionEntry {
  slug: string;
  source_id: string;
  name: string;
  patches_file: string;
  grid_file: string;
  analogs_file: string;
  exported_patch_count: number;
  source_patch_count: number;
  patches_with_analogs: number;
  /** Outer edges of the tiles, metres, lunar south polar stereographic. Missing in exports before this field. */
  extent_m?: { xmin: number; xmax: number; ymin: number; ymax: number };
}

export interface PipelineInfo {
  run_id: string;
  environment_scope: "tile" | "region" | null;
  caveat: string;
  earth_sites: string[];
  top_k_per_site: number;
  similarity_model: Record<string, string>;
}

export interface RegionsDocument {
  schema_version: number;
  source: { stage: string; run_id: string; claim_boundary: string };
  pipeline: PipelineInfo;
  earth_file: string;
  environment_file: string | null;
  regions: RegionEntry[];
}

export type RoverClass = "operable" | "marginal" | "non_operable";
export type WalkingClass = "easy" | "caution" | "unsuitable";
export type CrossingAxis = "north_south" | "east_west" | "northwest_southeast" | "northeast_southwest";

export interface PatchRecord {
  slug: string;
  source_id: string;
  /** Shared lunar tile ID across all pipelines: `<region>:<centre x m>:<centre y m>`. */
  tile_id: string;
  similarity_patch_id: string | null;
  top_row: number;
  top_col: number;
  center_x_m: number;
  center_y_m: number;
  tensor: { shard: string; index: number };
  grid_offset: number;
  rover: { class: RoverClass; probabilities: Record<RoverClass, number> };
  walking: { class: WalkingClass; probabilities: Record<WalkingClass, number> };
  crossing: Record<CrossingAxis, { predicted: boolean; probability: number }>;
  physical: { slope_median_deg: number; slope_p90_deg: number; relative_relief_m: number };
  direct_rule: { walking_class: WalkingClass; cnn_agrees: boolean };
}

export interface GridFormat {
  file: string;
  dtype: string;
  byte_order: string;
  scale: number;
  shape: [number, number];
  cell_order: string;
  channels: { name: string; unit: string }[];
  bytes_per_patch: number;
  byte_length: number;
}

export interface PatchesDocument {
  schema_version: number;
  run_id: string;
  pipeline_run: string;
  region: { slug: string; source_id: string; name: string };
  patch_size_m: number;
  spacing_m: number;
  grid: GridFormat;
  patches: PatchRecord[];
}

/** One Earth match for a lunar tile. Arrays follow the order of `EarthDocument.checks`. */
export interface AnalogMatch {
  /** Index into `EarthDocument.candidates`. */
  candidate: number;
  overall_rank: number;
  site_rank: number;
  cosine: number;
  bands: number[];
  within: boolean[];
}

export interface TileAnalogs {
  tile_id: string;
  query_id: string;
  moon_checks: number[];
  matches: AnalogMatch[];
}

export interface AnalogsDocument {
  schema_version: number;
  pipeline_run: string;
  region: { slug: string; source_id: string; name: string };
  candidate_pool: { sites: string[]; top_k_per_site: number; similarity_model: Record<string, string> };
  /** Keyed by patch slug. A patch without matches is absent. */
  tiles: Record<string, TileAnalogs>;
}

export interface EarthCandidate {
  id: string;
  site: string;
  latitude: number;
  longitude: number;
  checks: number[];
  grid_offset: number;
}

export interface EarthDocument {
  schema_version: number;
  pipeline_run: string;
  sites: { id: string; name: string; prepared_patch_count: number }[];
  checks: { name: string; label: string }[];
  grid: GridFormat;
  candidates: EarthCandidate[];
}

export type AssessmentStatus = "Pass" | "Fail" | "Unknown";
export type AssessmentName = "operations" | "survival";

/** One hard-gate check, copied from the scorer's detailed output (hard_gate_details). */
export interface GateCheck {
  domain: string;
  domain_label: string;
  column: string;
  label: string;
  unit: string;
  /** Null when the input was missing: the check is then Unknown. */
  value: number | null;
  operator: "above" | "below" | "between";
  threshold: number | null;
  lower: number | null;
  upper: number | null;
  /** Set only when the scorer capped the threshold to a shorter time window. */
  configured_threshold: number | null;
  window_hours: number | null;
  status: AssessmentStatus;
  reason: string;
  rationale: string;
}

export interface Assessment {
  status: AssessmentStatus;
  score: number | null;
  fail_reasons: string[];
  domains: { name: string; label: string; score: number | null }[];
  /** Null or missing: compact output, so per-check evidence is not available. */
  gates?: GateCheck[] | null;
  /** The scorer's evidence coverage, for example "9/9". */
  coverage?: string | null;
}

export type ScenarioKind = "artemis" | "apollo" | "uploaded";
export type Evidence = "measured_maps" | "assumed" | "apollo" | "uploaded";

export interface Scenario {
  id: string;
  kind: ScenarioKind;
  name: string;
  terrain_region: string | null;
  evidence: Evidence;
  operations: Assessment;
  survival: Assessment;
}

export interface EnvironmentDocument {
  schema_version: number;
  pipeline_run: string;
  scope: "tile" | "region";
  scorer: string;
  sample_input: { file: string; source: string; sha256: string } | null;
  /** The scorer and helpers for the browser upload. Null when the scorer was not in the exporting checkout. */
  upload_files: { name: string; file: string; sha256: string }[] | null;
  /** Whether each assessment can fail a hard gate under the scorer config. Null or missing: not known. */
  hard_gates?: Record<AssessmentName, boolean> | null;
  scenarios: Scenario[];
}

/** One decoded terrain channel: physical values in row-major order. */
export interface TerrainChannel {
  name: string;
  unit: string;
  rows: number;
  cols: number;
  values: Float32Array;
}
