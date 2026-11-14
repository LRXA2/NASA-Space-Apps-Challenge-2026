# Architecture

Status as of 2026-11-14. The hackathon ends 2026-11-15. Each section says whether it describes something that **exists** or something **planned**.

## Summary

The app is a static website. Three teammate pipelines run on our own machines, one integration command joins their outputs by lunar tile, and an export script converts the result into small files that the website reads. No server runs at any point. The only computation in the browser is the optional upload feature, which runs models as static files inside the page.

## Rules every part follows

- **Three separate scores.** Terrain similarity (Aarron), environment (Darrel) and terrain operability (Hanxi) answer different questions. They are never combined into one number.
- **Cosine similarity is not a percentage**, and no score is a safety rating. All terrain predictions come from models trained on Earth, and there is no lunar ground truth.
- **Everything shown is precomputed** and traceable to a run folder with a `provenance.json`.
- **Unknown is not a pass.** Missing values stay missing.

## Data flow

```
 Teammate runs (shared as zips)             Downloads (optional)
 ├─ Hanxi: walkability inference run        └─ 4 LOLA illumination maps
 ├─ Aarron: dataset, model, embedding cache
 └─ Darrel: env_pipeline.py + sample_input.csv (in the repo)
                │
                ▼  copied into data/processed/ (see data/README.md)
   python -m integration.run_all                       ← exists
                │
                ▼
   data/processed/moon_pipeline/<run>/                 ← exists (gitignored)
                │
                ▼
   app/scripts/export_data.py                          ← exists (v1), v2 planned
                │
                ▼
   app/public/data/   (committed to git)
                │
                ▼  npm run build
   app/dist/  →  static host                           ← planned
                │
                ▼
   Browser: React app reads JSON and binary files.
   Optional upload: Web Workers run Pyodide (environment) and ONNX models (terrain).
```

## Pipelines

| Owner | Pipeline | Code | Output used by the app |
| --- | --- | --- | --- |
| Aarron | Terrain similarity CNN | `notebooks/modeling/terrain_similarity/` | Top Earth matches per lunar tile, cosine, physical checks |
| Darrel | Environment scorer | `env_algo_task/env_pipeline/env_pipeline.py` | Operations and Survival assessments: domain scores, status, fail reason, final score |
| Hanxi | Terrain walkability CNN | `operational_cnn/` | Rover class, on-foot class, crossing directions, terrain grids |
| (integration) | Joins all three by tile | `integration/`, `notebooks/shared/moon_tiles.py` | `moon_pipeline/<run>/` |
| Gareth, Ian | App | `app/` | The website |

### Model inputs

Both CNNs read 32 × 32 grids: one 960 m tile at 30 m spacing. Each has its own scaler.

| Model | Channels | Outputs |
| --- | --- | --- |
| Aarron, `TerrainSimilarityCNN` | `relative_elevation_m`, `slope_deg`, `local_elevation_std_m` | 64-value unit vector. Mean of 8 rotations and reflections |
| Hanxi, `TerrainMobilityCNN` | `relative_elevation_m`, `slope_deg`, `roughness_90m`, `roughness_330m`, `laplacian_per_m` | Rover class (3), crossing directions (4), on-foot class (3) |

The channels come from elevation via `notebooks/shared/processing.py:terrain` (gradient slope, box-filter roughness over 3 and 11 cells, 4-neighbour laplacian). They are computed on the whole region before tiles are cut, so a tile's values depend on up to 5 cells of terrain around it.

## Shared tile identity (exists)

Before integration, each pipeline named the same tile differently:

- Aarron: `<region>:full_context:<centre row>:<centre col>:960`
- Hanxi: `<region>:960:<top row>:<top col>`

`notebooks/shared/moon_tiles.py` gives every tile one ID: **`<region>:<centre x m>:<centre y m>`**, in the common lunar south-polar stereographic projection. Tiles are snapped to one 960 m grid per region. A source more than 1 m off that grid is rejected, not matched to the nearest tile.

Checked on 2026-11-14: all 2,910 tiles have both an Aarron patch and a Hanxi patch. Their Moon grids agree to within 0.0002 m in relative elevation, and exactly in slope.

## Integration: `python -m integration.run_all` (exists)

Configured by `integration/run_all.json`. It needs the runs listed in [`data/README.md`](../data/README.md) and the similarity weights in `notebooks/modeling/terrain_similarity/weights/`. Each input is checked against its run's `provenance.json`. It takes about 90 seconds on CPU.

**Environment scope:**

- `tile` (default) needs the 4 LOLA maps. It measures Sun visibility, Earth visibility, permanent shadow and sky visibility inside each 960 m tile. Darrel's other inputs stay at their region values.
- `--environment-scope region` needs no maps. Every tile gets its region's scores (`eda_001`–`eda_007`).
- `--no-environment` skips the environment step.

**Writes** `data/processed/moon_pipeline/<run>/`:

| File | Rows | Content |
| --- | --- | --- |
| `moon_tiles.csv` | 2,910 | `tile_id`, centre and bounds in metres, each source's patch ID, coverage flags |
| `moon_sites.csv` | 2,910 | Hanxi's classes, probabilities and slope figures, plus `env_*` columns |
| `earth_matches.csv` | 43,650 | 2,910 tiles × 5 Earth sites × top 3. `site_rank`, `overall_rank`, `cosine_similarity`, lat/lon, relief and slope differences, `physical_checks_within_band` |
| `environment.csv` | 83 | Darrel's compact output (see below) |
| `environment_sites.csv`, `tile_support.csv` | | Tile scope only: scorer input per tile, and which tiles were measured |
| `summary.json`, `summary_by_region.csv` | | Counts, best Earth site per region, stage run paths |

Each stage also keeps its own run folder under `data/processed/` (`moon_tiles/`, `moon_sites/`, `terrain_similarity_tile_matches/`). `summary.json` → `stage_runs` points to them. The per-check physical comparison (`physical_comparison.csv`) is only in the `terrain_similarity_tile_matches` run.

### Environment output format

`ID`, then `operations_<domain>_score` (thermal, solar_illumination, dust, plasma_charging, earth_visibility, soil), `survival_<domain>_score` (radiation, thermal, plasma_charging, uv), `operations_status`, `survival_status` (`Pass` / `Fail` / `Unknown`), `operations_fail_reason`, `survival_fail_reason`, `operations_score`, `survival_score`.

Read domain columns by prefix, because the domain list has changed before. `--detailed` adds `*_coverage` and `*_details` (JSON) columns.

The 83 rows are 17 Artemis regions (`eda_001`–`eda_017`), 6 Apollo references, and 60 test rows (`synthetic_*`, `dummy_*`). The app never shows the test rows. Only `eda_001`–`eda_007` have terrain. Most input values are assumptions, not measurements (Darrel's README).

## App data files

### Schema v1 (exists, Hanxi's data only)

| File | Content |
| --- | --- |
| `regions.json` | Exported regions, source run ID, claim boundary |
| `patches/<region>.json` | One record per patch: classes, probabilities, crossings, measurements, grid position, `grid_offset` |
| `grids/<region>.bin` | Relative elevation and slope, Int16 × 10, little-endian, 4,096 bytes per patch |

About 16 MB in total. The format is described in [`app/README.md`](../app/README.md).

### Schema v2 (planned, reads `moon_pipeline/<run>/`)

| File | Change | Estimated size |
| --- | --- | --- |
| `regions.json` | Add the pipeline run ID and the environment scope | small |
| `patches/<region>.json` | Add `tile_id` and the similarity patch ID to each record. Keep the Hanxi ID and the `r<row>-c<col>` route name | +5% |
| `grids/<region>.bin` | Unchanged | 12 MB |
| `analogs/<region>.json` | Per tile: 15 matches (5 sites × top 3) as compact arrays, keyed by `tile_id` | ~4 MB total |
| `earth/candidates.json` | The 2,222 Earth patches that appear in any match: site, lat/lon, 5 physical features | ~0.5 MB |
| `earth/grids.bin` | Those patches' relative elevation and slope from Aarron's dataset tensors, in the same Int16 × 10 format | ~9 MB |
| `environment.json` | 17 Artemis rows (and Apollo, if kept): both assessments, domains by prefix, status, fail reasons, evidence labels | small |
| `upload/` | Only if uploads ship: ONNX models, Earth embedding bank, scalers, Darrel's scorer files and template | ~3 MB |

The export still opens Hanxi's run for tensor locations and grid rows and columns, because `moon_sites.csv` doesn't keep them. Paths in `summary.json` use Windows backslashes. Normalise them.

## App structure (exists, extended as planned)

```
app/
  scripts/export_data.py      Pipeline output → public/data/ (rejects unsafe records)
  scripts/tests/              Export tests
  public/data/                Committed exports
  src/
    router.ts                 Only file that knows the URL form (hash routes)
    data/types.ts             Types for every exported file
    data/loaders.ts           Fetch, check schema version, decode grids
    pages/                    One component per route
    components/               PatchMap (Leaflet CRS.Simple), TerrainCanvas, StatusBadge, …
    workers/                  Planned: upload workers (Pyodide, ONNX)
```

| Route | Page | Status |
| --- | --- | --- |
| `#/` | Region list | exists |
| `#/region/<region>` | Patch map and list | exists |
| `#/region/<region>/patch/<patch>` | Patch terrain and predictions | exists |
| `#/region/<region>/patch/<patch>/analogs` | Ranked Earth matches and Earth map | planned |
| `#/region/<region>/patch/<patch>/analogs/<candidate>` | Moon–Earth pair comparison | planned |
| `#/environment/<region>` or a tab | Operations and Survival | planned |
| `#/upload` | Upload your own data | planned, scope open |

Maps: Leaflet without react-leaflet. The Moon uses `L.CRS.Simple` in grid cells per region (not north-up, no basemap). The Earth map uses a normal lat/lon basemap with attribution. Terrain grids are drawn on `<canvas>` with a shared colour scale. The chart library is not chosen yet (Observable Plot or Recharts; Plotly is too heavy).

## Upload in the browser (planned, scope open)

| Pipeline | Runs as | Template | Status |
| --- | --- | --- | --- |
| Environment | Darrel's unmodified `env_pipeline.py` and `config.yml` in Pyodide (stdlib + PyYAML), in a Web Worker | Darrel's `sample_input.csv` | Not yet run in Pyodide |
| Similarity CNN | ONNX model in onnxruntime-web, 8 orientations, cosine against the shipped Earth embedding bank (5,693 × 64) | Elevation grid (below) | ONNX export checked |
| Walkability CNN | ONNX model in onnxruntime-web, softmax and sigmoid built into the model | Same elevation grid | ONNX export checked |

**ONNX check (2026-11-14).**

- Similarity model, 393 KB: largest difference from `embeddings.npz` over 8,603 patches is 2.2e-7. The top Earth match is identical for all 2,910 Moon tiles.
- Walkability model, 363 KB: largest probability difference from `predictions.csv` over 2,910 patches is 5.4e-7, with 0 class changes.

The check script is not in the repo yet.

**Terrain template (proposed):** Esri ASCII grid (`.asc`, which QGIS can export), 42 × 42 cells at 30 m in a projected metric grid. That is the 32 × 32 tile plus a 5-cell margin, because the 330 m window needs it. A TypeScript port computes the channels exactly as `processing.py:terrain` does. To test the port without a DEM, rebuild the elevation from Hanxi's relative-elevation channel (elevation minus a constant), recompute the other channels, and compare them inside the tile.

**Fallback:** a small hosted Python backend running the real code. Only if the TypeScript port can't match, because it adds a server to keep running during judging.

## Hosting (planned, host open)

The build is fully static: `npm --prefix app run build` → `app/dist/`. Hash routes and a relative `base` mean any static host works without rewrite rules.

- **GitHub Pages:** needs a public repo, or an admin to enable Pages on a private one.
- **Vercel:**
  - Connecting the repo builds on every push, but the repo owner has to grant access.
  - The Vercel CLI (`npx vercel`) uploads a local build from your own machine instead. That needs only a free Vercel account, not repo access, but every redeploy is a manual command.

## Decisions

| Decision | Status |
| --- | --- |
| Static site, no backend, exports committed | Decided (group sign-off still requested) |
| Vite + React + TypeScript, Leaflet without react-leaflet, canvas terrain | Decided |
| Int16 × 10 binary grids per region | Decided |
| Hash routes, relative base path | Decided (Ian) |
| Integration output (`moon_pipeline/<run>/`) is the only export input | Decided 2026-11-14 |
| `tile_id` is the join key across all three pipelines | Decided 2026-11-14 |
| Pair URLs use the Earth candidate ID, not the rank | Decided (Ian) |
| Host | **Open** |
| Upload scope: environment only, or environment plus both CNNs | **Open, team input** |
| Environment per region, or per tile with the LOLA maps | **Open** |
| Show the Apollo reference rows | **Open, team input** |
| Chart library | Open, pick when needed |

Questions for teammates are in [team-blockers.md](team-blockers.md).

## Known caveats

- `integration/run_all.py` `CAVEAT` always says environment values are per tile, even when the run used region scope. Use `summary.json` → `environment_scope` instead.
- Hard gates are off in Darrel's config, so all 83 rows are `Pass` and no score is blank.
- Atacama is the best match for about 88% of tiles. It also has 3,078 of the 5,693 Earth patches.
- 193 match rows have cosine above 0.95 with 0 of 5 physical checks in band. Keep these visible: they show why physical checks matter.
- The Earth simulation-readiness score does not exist. Show it as not computed.
