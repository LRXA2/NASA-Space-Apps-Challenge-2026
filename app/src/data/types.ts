// Shapes of the files written by app/scripts/export_data.py (schema version 1).

export const SCHEMA_VERSION = 1;

export interface RegionEntry {
  slug: string;
  source_id: string;
  name: string;
  patches_file: string;
  grid_file: string;
  exported_patch_count: number;
  source_patch_count: number;
}

export interface RegionsDocument {
  schema_version: number;
  source: { stage: string; run_id: string; claim_boundary: string };
  regions: RegionEntry[];
}

export type RoverClass = "operable" | "marginal" | "non_operable";
export type WalkingClass = "easy" | "caution" | "unsuitable";
export type CrossingAxis = "north_south" | "east_west" | "northwest_southeast" | "northeast_southwest";

export interface PatchRecord {
  slug: string;
  source_id: string;
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
  region: { slug: string; source_id: string; name: string };
  patch_size_m: number;
  spacing_m: number;
  grid: GridFormat;
  patches: PatchRecord[];
}

/** One decoded terrain channel: physical values in row-major order. */
export interface TerrainChannel {
  name: string;
  unit: string;
  rows: number;
  cols: number;
  values: Float32Array;
}
