# Lunar Analog Finder app

A static React site (Vite + TypeScript). It reads precomputed files from `public/data/`. No server runs. The only computation in the browser is the optional environment upload, which runs the team's scorer in Pyodide inside a Web Worker.

Current scope: seven lunar regions and 2,910 terrain patches. Every patch has rover and on-foot predictions, slope and relative-elevation grids, 15 Earth matches (5 sites × top 3) with physical checks, and its region's environment scenario. The environment pages cover all 17 Artemis candidate regions.

How this fits with the pipelines: [`docs/architecture.md`](../docs/architecture.md).

## Run the app

Run these from the repository root. You need Node 22 or newer.

```bash
npm --prefix app install
npm --prefix app run dev
```

Open http://localhost:5173. To check the production build:

```bash
npm --prefix app run build
npm --prefix app run preview
```

## Export the data

The export reads one integrated pipeline run, `data/processed/moon_pipeline/<run>/`. Make one first (see [`data/README.md`](../data/README.md) for the inputs):

```powershell
.\.venv\Scripts\python.exe -m integration.run_all --environment-scope region
.\.venv\Scripts\python.exe app\scripts\export_data.py
.\.venv\Scripts\python.exe -m unittest discover -s app/scripts/tests -p "test_*.py"
```

On macOS or Linux, use `.venv/bin/python` and forward slashes.

The export also opens the two runs the pipeline run names in its `provenance.json`: Hanxi's walkability inference run (Moon grids) and Aarron's prepared dataset (Earth grids). It never loads model weights and never changes the source files.

Options:

- `--pipeline-run <folder>`: default, the newest completed `moon_pipeline` run.
- `--region <name>`: export one region, such as `haworth`. Repeat it for more. Leave it out to export all seven.
- `--patch-id <Hanxi patch ID>`: export only this patch. Repeat it for more. It needs exactly one `--region`.
- `--output-dir <folder>`: default `app/public/data`. Use a temporary folder to review an export first.

The script stops with a message, and a non-zero exit code, when a record is unsafe to publish. Examples: a duplicate patch ID, an unknown class, a missing tensor, a non-finite value, a match without its physical checks, a check count that disagrees with its checks, an unknown environment ID, or Darrel's old single-score format.

### Checks against the teammates' own outputs

```powershell
# Environment upload: run the published scorer in Pyodide under Node, compare with the CLI byte for byte
npm --prefix app run check:scorer -- ../data/processed/moon_pipeline/<run>/environment.csv

# CNNs: export both models to ONNX and compare with embeddings.npz and predictions.csv (needs torch, onnx, onnxruntime)
.\.venv\Scripts\python.exe app\scripts\check_onnx_parity.py <out_dir>
```

## Data files (schema version 2)

| File | Content |
| --- | --- |
| `regions.json` | Regions, the pipeline run and its caveat, the terrain run and its claim boundary. Each region's `extent_m` holds the outer edges of its tiles in the lunar south polar stereographic CRS (`+proj=stere +lat_0=-90 +lon_0=0 +R=1737400`) |
| `patches/<region>.json` | One record per patch: Hanxi ID, shared `tile_id`, similarity patch ID, grid position, classes, probabilities, crossings, measurements, `grid_offset` |
| `grids/<region>.bin` | Moon terrain grids for every patch in that region |
| `analogs/<region>.json` | Per patch slug: the tile's five Moon check values and its matches (candidate index, overall and per-site rank, cosine, tolerance bands, in-band flags) |
| `earth/candidates.json` | Earth sites, the five check labels, and every Earth patch used in a match (site, lat/lon, check values, `grid_offset`) |
| `earth/grids.bin` | Earth terrain grids for those patches |
| `environment.json` | Artemis and Apollo scenarios: Operations and Survival status, final score, fail reasons, domain scores, evidence label. Test rows are left out. `hard_gates` (`{operations, survival}` booleans, or null without the scorer) is read from the scorer config through its own `assessment_config` |
| `environment/sample_input.csv` | The scorer's input template, copied unchanged |
| `environment/scorer/` | `env_pipeline.py`, `config.yml` and the two upload helpers, copied unchanged with SHA-256 hashes in `environment.json` |

Grid file layout (both Moon and Earth):

- Patches are stored in array order. Each record has its `grid_offset` in bytes.
- Each patch is 4,096 bytes: relative elevation (metres), then slope (degrees).
- Each channel is 32 × 32 cells in row-major order. Row 0 is the top row of the source grid.
- Each value is a little-endian signed 16-bit integer. Divide it by 10 to get the physical value. The rounding error is at most 0.05.

Route names such as `haworth` and `r32-c32` are for URLs. Every record also keeps its original source IDs.

## Pages

| URL | Page |
| --- | --- |
| `#/` | Region list |
| `#/region/<region>` | Patch map and patch list for one region |
| `#/region/<region>/patch/<patch>` | One patch: classes, terrain, best Earth match, region environment |
| `#/region/<region>/patch/<patch>/analogs` | All 15 Earth matches: ranked table and Earth map |
| `#/region/<region>/patch/<patch>/analogs/<earth patch ID>` | Moon–Earth pair: physical checks and four grids on shared scales |
| `#/environment` | All 17 Artemis regions' Operations and Survival results |
| `#/environment/<scenario ID>` | One scenario's domain scores |
| `#/upload` | Score your own environment CSV in the browser |

URLs use a `#` so that links work on any static host without server rules. `src/router.ts` is the only file that knows the URL form. Pair URLs use the Earth patch ID, not the rank, because rank changes if the candidate pool grows.

`SHOW_APOLLO` in `src/pages/EnvironmentPage.tsx` switches the six Apollo reference scenarios on (team blocker T3).

## Patch map

The region page draws one square per patch with Leaflet. The map uses `L.CRS.Simple`, which is a flat grid with no basemap. Lunar coordinates are never put on an Earth map.

- Map units are source grid cells of 30 m. Each patch is 32 by 32 cells.
- x is the grid column (`top_col`). y is minus the grid row (`top_row`), because Leaflet's y axis points up.
- So row 0 is at the top, and a larger row is drawn lower. A larger column is drawn further right.
- Only patches in the data are drawn. A missing patch stays an empty gap.
- The grid is the stored grid. It is not a north-up map.

`patchBounds` in `src/components/PatchMap.tsx` is the only place that holds this convention.

The Earth map (`src/components/EarthMap.tsx`) uses OpenStreetMap tiles with attribution and numbered markers. If the tiles fail, the page says so and the result table lists the same places.

## Environment upload

`src/workers/environmentWorker.ts` loads Pyodide 0.28.3 from jsDelivr on the first upload, checks each scorer file's SHA-256 against `environment.json`, and runs `score_upload.py`. That runs Darrel's unmodified `env_pipeline.py --compact`, then `environment_data.py`, which is the same adapter the export uses, so uploaded and precomputed results share one format. Later uploads in the same visit reuse the loaded worker.

## Styling

`src/styles/tokens.css` holds placeholder colours and fonts as CSS variables. Replace that file when the design tokens are ready. Terrain colour ramps are in `src/components/colorScales.ts`.
