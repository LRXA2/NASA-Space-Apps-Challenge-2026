# Architecture

Status as of 2026-11-15. The hackathon ends 2026-11-15. Each section says whether it describes something that **exists** or something **planned**.

## Summary

The app is a static website with no application backend. Offline integration joins the three pipelines by lunar tile and exports browser data. Environment uploads run the scorer in a Pyodide worker. Terrain CNN uploads are not implemented. Charts derive distributions from published grids in the browser.

## Rules every part follows

- **Three separate scores.** Terrain similarity (Aarron), environment (Darrel) and terrain operability (Hanxi) answer different questions. They are never combined into one number.
- **Cosine similarity is not a percentage**, and no score is a safety rating. All terrain predictions come from models trained on Earth, and there is no lunar ground truth.
- **Catalogue results are precomputed** and traceable to a run folder with `provenance.json`. Uploaded environment results are computed locally and labelled user-supplied.
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
   app/scripts/export_data.py                          ← exists (schema v2)
                │
                ▼
   app/public/data/   (committed to git)
                │
                ▼  npm run build
   app/dist/  →  GitHub Pages (pages.yml)              ← live (T2)
                │
                ▼
   Browser: React app reads JSON and binary files.
   Optional upload: Pyodide environment scoring exists. Browser terrain inference is not built (T1).
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
| `environment_detailed.csv` | 83 | The same scoring with `--detailed`: compact columns plus `*_coverage` and `*_details`. The app reads per-gate evidence from it |
| `environment_sites.csv`, `tile_support.csv` | | Tile scope only: scorer input per tile, and which tiles were measured |
| `physical_comparison.csv` | 218,250 | The five physical checks behind every match: Moon value, Earth value, tolerance band, in band |
| `summary.json`, `summary_by_region.csv` | | Counts, best Earth site per region, stage run paths (POSIX), a caveat worded for the environment scope |

Each stage also keeps its own run folder under `data/processed/` (`moon_tiles/`, `moon_sites/`, `terrain_similarity_tile_matches/`). `summary.json` → `stage_runs` points to them.

### Environment output format

`ID`, then `operations_<domain>_score` (thermal, solar_illumination, dust, plasma_charging, earth_visibility, soil), `survival_<domain>_score` (radiation, thermal, plasma_charging, uv), `operations_status`, `survival_status` (`Pass` / `Fail` / `Unknown`), `operations_fail_reason`, `survival_fail_reason`, `operations_score`, `survival_score`.

Read domain columns by prefix, because the domain list has changed before. `--detailed` adds `*_coverage` and `*_details` (JSON) columns. Inside `*_details`, `hard_gate_details` is a JSON string: one entry per gate with the column, unit, value, condition (operator and threshold, or lower and upper), status (`Passed`/`Failed`/`Unknown`, shown as Pass/Fail/Unknown) and reason. A duration gate capped to a short window also has `configured_threshold` and `window_duration_hours` (D2).

The 83 rows are 17 Artemis regions (`eda_001`–`eda_017`), 6 Apollo references, and 60 test rows (`synthetic_*`, `dummy_*`). The app never shows the test rows. Only `eda_001`–`eda_007` have terrain. Most input values are assumptions, not measurements (Darrel's README).

## App data files (schema v2, exists)

Written by `app/scripts/export_data.py` from one `moon_pipeline/<run>/` folder, plus the two runs it names (Hanxi's run for Moon grids, Aarron's dataset for Earth grids). 31 MB in total, committed under `app/public/data/`. The full format is in [`app/README.md`](../app/README.md#data-files-schema-version-2).

| File | Content | Size |
| --- | --- | --- |
| `regions.json` | Regions with their `extent_m` (tile bounds in the lunar south polar stereographic CRS), pipeline run and caveat, terrain run and claim boundary | small |
| `patches/<region>.json` | Hanxi's classes and probabilities per patch, plus `tile_id` and the similarity patch ID | 1.6 MB |
| `grids/<region>.bin` | Moon relative elevation and slope, Int16 × 10 | 12 MB |
| `analogs/<region>.json` | Per patch: Moon check values and 15 matches (rank, cosine, bands, in-band flags) | 6.6 MB |
| `earth/candidates.json` | The 2,222 Earth patches used in any match: site, lat/lon, check values | 0.4 MB |
| `earth/grids.bin` | Their relative elevation and slope, same format, from Aarron's dataset | 9.1 MB |
| `environment.json` | 17 Artemis and 6 Apollo scenarios (test rows left out): both assessments, domains read by prefix. `gates` per assessment holds each hard-gate check from the detailed output (null if only compact output was available). `hard_gates` says whether each assessment can fail a gate under the scorer config; the app labels a Pass "gates off" when it can't | small |
| `environment/` | `sample_input.csv` and the scorer files for the upload, copied with SHA-256 hashes. Only line endings change (to LF, as git stores them), so the hashes match on every checkout and host | small |

Moon grids from Hanxi's and Aarron's tensors agree (checked 2026-11-14), so Moon and Earth grids share one scale on the pair page.

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
    workers/                  environmentWorker.ts (Pyodide). ONNX worker not built
```

| Route | Page | Status |
| --- | --- | --- |
| `#/` | Polar overview map and region list | exists |
| `#/region/<region>` | Patch map and list | exists |
| `#/region/<region>/patch/<patch>` | Patch terrain, predictions, best Earth match, region environment | exists |
| `#/region/<region>/patch/<patch>/analogs` | Ranked Earth matches and Earth map | exists |
| `#/region/<region>/patch/<patch>/analogs/<earth patch ID>` | Moon–Earth pair comparison | exists |
| `#/environment`, `#/environment/<scenario>` | Operations and Survival per region | exists |
| `#/upload` | Score your own environment CSV | exists (environment only) |

Maps use Leaflet without react-leaflet. The Moon uses `L.CRS.Simple` in stored grid cells, with no north-up basemap. Earth uses latitude/longitude tiles with attribution. Canvas terrain panels share one scale per measurement. `DistributionChart.tsx` draws cumulative distributions in plain SVG from each 1,024-cell grid. No chart library is required.

## Upload in the browser (environment exists, terrain deferred)

| Pipeline | Runs as | Template | Status |
| --- | --- | --- | --- |
| Environment | Darrel's unmodified `env_pipeline.py` and `config.yml` in Pyodide 0.28.3 (stdlib + PyYAML), in a Web Worker | Darrel's `sample_input.csv`, with a collapsible input guide (`InputGuide.tsx`) summarising the scorer README. Keep the two aligned | **Exists.** Output identical to the CLI for all 83 sample rows (`npm --prefix app run check:scorer`) |
| Similarity CNN | Deferred (T1): ONNX inference, 8 orientations, and cosine against the Earth embedding bank (5,693 × 64) | Elevation grid (below) | Offline ONNX export checked. Browser integration is not built |
| Walkability CNN | Deferred (T1): ONNX inference with softmax and sigmoid in the model | Same elevation grid | Offline ONNX export checked. Browser integration is not built |

**ONNX check (2026-11-14).**

- Similarity model, 393 KB: largest difference from `embeddings.npz` over 8,603 patches is 2.2e-7. The top Earth match is identical for all 2,910 Moon tiles.
- Walkability model, 363 KB: largest probability difference from `predictions.csv` over 2,910 patches is 5.4e-7, with 0 class changes.

Rerun with `app/scripts/check_onnx_parity.py`.

**Terrain template, for a later elevation upload (confirmed by Aarron, not built):** a 42 × 42 `.asc` elevation grid at 30 m spacing, in metres, with no missing values. This surrounds the 32 × 32 tile with a five-cell margin. A proposed TypeScript preprocessing port would need to match `processing.py:terrain` before browser CNN results could be accepted. Models must ship with their own saved scalers. See A1–A2 and H1–H3 in the team answers.

## Hosting: GitHub Pages (T2)

The build is fully static: `npm --prefix app run build` → `app/dist/`. Hash routes and a relative `base` mean any static host works without rewrite rules.

The repo is public, so the site deploys to GitHub Pages. [pages.yml](../.github/workflows/pages.yml) builds `app/` and publishes `app/dist` on every push to `main`, or by hand from the Actions tab. A repo admin sets Settings → Pages → Source to "GitHub Actions" once. The site is live at <https://lrxa2.github.io/NASA-Space-Apps-Challenge-2026/>. Pyodide still loads from jsDelivr on the first upload.

Vercel was the alternative. It needs a personal account that then owns the demo URL, and its preview deploys aren't needed for the submission.

## Regenerating the export (T7)

Confirmed (T7): run by hand, by Gareth, on a machine holding the git-ignored inputs in `data/`. Only when a CNN, the scorer or its template, the regions or the export format changes. Step-by-step instructions for whoever runs it: [regenerate-export.md](regenerate-export.md). CI's `CommittedExportTests` fails when the published scorer or template no longer matches `env_algo_task/env_pipeline/`.

## Decisions

| Decision | Status |
| --- | --- |
| Static site, no backend, exports committed | Decided, kept by the team (T5) |
| Vite + React + TypeScript, Leaflet without react-leaflet, canvas terrain | Decided |
| Int16 × 10 binary grids per region | Decided |
| Hash routes, relative base path | Decided (Ian) |
| Integration output (`moon_pipeline/<run>/`) is the only export input | Decided and built 2026-11-14 |
| `tile_id` is the join key across all three pipelines | Decided 2026-11-14 |
| Pair URLs use the Earth candidate ID, not the rank | Decided (Ian) |
| Host | **GitHub Pages (T2)**, deployed from `main` by `pages.yml` |
| Upload scope: environment only, or environment plus both CNNs | **Environment only (T1)** for the submission. Elevation uploads can follow later |
| Environment per region, or per tile with the LOLA maps | **Per region (T4)**, labelled as shared by every tile in the region. Per tile can follow later |
| Featured tiles | **Three per region (T6)**: strong match, misleading high cosine, not Atacama. Shown on the region page from `app/src/featured.json` |
| Show the Apollo reference rows | **Yes (T3)**, labelled as equatorial comparison sites scored from best-effort estimates |
| Distribution charts | Built with plain SVG in `DistributionChart.tsx`, no chart dependency (`b0b4641`) |
| Visual direction | Exploration theme selected by Gareth after Aarron's reconnaissance rationale. It is merged through `dd3503f`. See the app area decision |

Questions for teammates are in [team-blockers.md](team-blockers.md).

## Known caveats

- Hard gates are on (Darrel, D1, 2026-11-14). The thresholds are project test values, not NASA limits. `pipeline_mode: strict` turns a blank required input into Unknown with a reason. The app labels a Pass "gates off" only for an assessment whose config has no active gate.
- Two relief measures: the patch page shows Hanxi's max − min (`relative_relief_m`), and the physical checks use Aarron's p95 − p5 (`central_relief_m`). Both come from the same grid.
- Atacama is the best match for about 88% of tiles. It also has 3,078 of the 5,693 Earth patches.
- 193 match rows have cosine above 0.95 with 0 of 5 physical checks in band. Keep these visible: they show why physical checks matter.
- The Earth simulation-readiness score does not exist. Show it as not computed.
