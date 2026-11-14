# App developer handoff

Status as of 2026-11-13. The hackathon has about two days left. Following this folder's convention, add a new dated `developer_handoff_<YYYY-MM-DD>.md` for each handoff instead of editing this one.

The app is planned but **no app code exists yet**. The stack is decided, the Python environment works, and two of the three teammates' outputs have arrived. Your first job is the **data export script** (see [Next steps](#next-steps)). It doesn't depend on the visual design.

This file covers project status, decisions, data and blockers. For screens, routes, UI rules and the wireframes, read the design handoff: [`design_handoff_2026-11-13.md`](../../design/handoff/design_handoff_2026-11-13.md) and [`../PRODUCT.md`](../../design/PRODUCT.md). Where the two files disagree, see [Clarifications](#clarifications).

## Where things are

| What | Where |
| --- | --- |
| Design handoff (screens, routes, UI rules) | [`design_handoff_2026-11-13.md`](../../design/handoff/design_handoff_2026-11-13.md) |
| Product facts and constraints | [`../PRODUCT.md`](../../design/PRODUCT.md) |
| Low-fi wireframes (revision 3) | [`../wireframes.html`](../../design/wireframes.html), [artifact](https://claude.ai/artifact/4iQVvpyT417jgJVm4npdY2) |
| Pipeline plan and data sources | [`outline.md`](../../outline.md) |
| Notebook index | [`notebooks/README.md`](../../notebooks/README.md) |
| Teammates' raw outputs (gitignored) | `temp/` |

## Status

| Area | Status | Notes |
| --- | --- | --- |
| Stack and architecture | Decided | Static React + Leaflet, Python export script, no backend. **Group sign-off requested, not confirmed yet** |
| Python environment (`.venv`) | Done | Python 3.12.13, repo requirements, CPU PyTorch 2.9.1. All 62 repo tests pass |
| Darrel's environment results | Received | `temp/darrel pipeline results.csv`. Column change coming |
| Hanxi's terrain results | Received | `temp/terrain_human_walkability_*` |
| Aarron's similarity results | **Waiting** | Needed for the Earth analog screens |
| Wireframes (low fidelity) | Revision 3 done | Waiting on the owner's approval |
| Design system and mid-fi mockup | Not started | Starts after the layout is approved |
| Data export script | Not started | **Start here** |
| React app | Not started | |
| Hosting and submission materials | Not started | GitHub Pages or Vercel |

## Project context

The challenge is NASA Space Apps 2026, *"Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars"*. A user picks a site near the lunar south pole (the Artemis III candidate regions). The app shows (1) whether a mission could operate there and (2) which Earth terrain resembles it closely enough to practise rover route-planning, with the physical differences and limits stated.

| Owner | Pipeline | Branch | What it gives the app | Code entry point |
| --- | --- | --- | --- | --- |
| Aarron | Terrain similarity CNN | `dev_aarron` | Top-k Earth patches per lunar patch, cosine score, physical differences | `notebooks/modeling/terrain_similarity/pipeline/main.py` |
| Darrel | Environment suitability engine | `dar_dev` | Per-region domain scores, hard gates, fail reasons, final scores | `darrel stuff/env_pipeline/env_pipeline.py` |
| Hanxi | Terrain operability CNN | `feature/hanxi` | Per-patch rover class, on-foot class, crossing directions, terrain grids | `operational_cnn/inference/run_lunar_human_walkability.py` |
| Gareth | App | none yet | Planning and wireframes | |

`main` was last updated on 2026-11-05. **None of the three branches has been merged.** Each person works on their own branch. There is no CONTRIBUTING file, no PR template and no CI.

## Decisions made

| Decision | Why |
| --- | --- |
| **Earth and Moon only, no Mars** | Team scope decision (in `outline.md`). Expect judges to ask about it |
| **Static React site:** Vite + React + TypeScript | Full design control. The app owner knows React. Streamlit was considered and **rejected**: it limits layout and visuals, reruns the whole script on every click, and needs a running server |
| **No backend** | The app only reads files. The static host serves `public/data/`, which removes a server to build and keep up during judging |
| **Everything precomputed** | Teammates run their pipelines. One export script turns the outputs into app data files. Nothing runs models in the browser. Aarron's search must be run ahead of time for every lunar patch (top ~10 matches, plus per Earth site if we add a site filter) |
| **Exported data is committed to git** | Static hosting builds from the repo, and `data/` and `temp/` are gitignored. Expect roughly 15 MB in total, mostly terrain grids (see the export step in [Next steps](#next-steps)) |
| **Leaflet** for maps | The owner has used it. Earth uses normal lat/lon tiles. The Moon uses `L.CRS.Simple` (a flat grid per region), because web map tiles can't show the lunar south pole |
| **Terrain drawn on `<canvas>`** from 32×32 grids | Gives a shared Moon/Earth colour scale and hover readouts. No PNG pipeline needed |
| **Charts: Recharts or Observable Plot** | Plotly.js adds about 3 MB. The choice between the two is still open |
| **Hosting: GitHub Pages or Vercel** | Free, permanent link for judges. The choice is still open |
| **CPU PyTorch** in the venv | The repo pins a CUDA build (~2.5 GB). This machine has no NVIDIA GPU, and the app only needs saved models |

## Local setup

**Python** (for the export script and the notebooks):

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r notebooks/requirements-processing.txt
uv pip install --python .venv\Scripts\python.exe torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python.exe -m unittest discover -s notebooks -t .   # expect 62 tests OK
```

**Node:** v22 and npm 10 are installed. No Vite project exists yet.

**Gitignored folders** (they won't arrive with a clone): `data/`, `temp/`, `reports/`, `.venv/`. Teammates' outputs are shared by hand (zip files) and currently live in `temp/`.

**Design tooling:** the design session used UI skills (impeccable, ui-ux-pro-max, frontend-design). They were reviewed and nothing suspicious was found. impeccable downloads a checksum-verified binary from its GitHub releases on first use. **Don't commit `.impeccable/`**, since it only holds local settings.

## Data received

### Darrel: environment engine (B)

**File:** `temp/darrel pipeline results.csv` (83 rows)

**Columns:** `ID`, nine domain scores 0–100 (`radiation`, `thermal`, `solar_illumination`, `dust`, `plasma_charging`, `uv`, `seismic`, `exosphere`, `communications_geometry`), `hard_gate_status` (Passed/Failed), `Fail Reason`, `final_habitability_score`.

- **Only 23 rows are real candidates:** `eda_001`–`eda_017` (Artemis regions) and six `apollo_*` baselines. **Filter out** the 30 `synthetic_*` and 30 `dummy_*` rows, which are test cases.
- **Column change coming:** `final_habitability_score` becomes two columns, `Ops` and `Survivability`, both 0–100 (`temp/darrel pipeline potential changes.txt`).
- **Blank scores are expected.** A final score stays blank when an evaluated hard gate **fails or is Unknown**, or when configuration is incomplete (Darrel's pipeline README, "Simple output" section).
- **Fail reasons are machine text**, e.g. `solar_illumination: window_continuous_sunlight_hours = 150.0 h; required >= 156 h`. Several reasons are joined with ` | `. Turn them into readable sentences in the export script.
- **Per-check Passed/Failed/Unknown** (needed for the environment tab) isn't in this file. Darrel's pipeline has a `--detailed` export with "audit reasons". It's unconfirmed whether that includes per-check status, so ask Darrel.
- **Not all values are measured.** `eda_001`–`007` use statistics from EDA maps. `eda_008`–`017` use **assumed values** with no measured footprint. Apollo rows mix sourced and modelled values. The UI should label this.

**Region IDs** (from Darrel's README on `dar_dev`). Hanxi's terrain data covers the first seven:

| Env ID | Region | Terrain region ID (Hanxi) |
| --- | --- | --- |
| eda_001 | Leibnitz Beta Plateau | A3CLR22_10_Leibnitz_Beta_Plateau |
| eda_002 | Malapert Massif | A3CLR22_11_Malapert_Massif |
| eda_003 | de Gerlache–Kocher Massif | A3CLR22_12_deGerlache_Kocher_Massif |
| eda_004 | Haworth | A3CLR22_2_Haworth |
| eda_005 | Faustini Rim A | A3CLR22_3_Faustini_Rim_A |
| eda_006 | de Gerlache Rim 2 | A3CLR22_4_deGerlache_Rim_2 |
| eda_007 | Connecting Ridge Extension | A3CLR22_5_Connecting_Ridge_Extension |
| eda_008 | Peak Near Shackleton | (environment only) |
| eda_009 | Connecting Ridge | (environment only) |
| eda_010 | de Gerlache Rim 1 | (environment only) |
| eda_011 | Nobile Rim 1 | (environment only) |
| eda_012 | Nobile Rim 2 | (environment only) |
| eda_013 | Amundsen Rim | (environment only) |
| eda_014 | Peak near Cabeus B | (environment only) |
| eda_015 | Mons Mouton Plateau | (environment only) |
| eda_016 | Mons Mouton | (environment only) |
| eda_017 | Slater Plain | (environment only) |

This table comes from Darrel's README, not the CSV, so confirm it with him before relying on it.

### Hanxi: terrain CNN (C)

**Use the run `20261112T120422201915Z_101366`.** It contains everything in the older `…_fc8667` run, plus a comparison against a simple slope rule. Ignore the older run.

**File:** `temp/terrain_human_walkability_lunar_inference/20261112T120422201915Z_101366/predictions.csv`. 2,910 patches across 7 regions (Haworth 841, Malapert 400, Leibnitz 225, the other four 361 each). Each patch is 960 m × 960 m, a 32×32 grid at 30 m spacing.

- **Rover:** `predicted_rover_class` (operable / marginal / non_operable), `rover_probability_*`
- **On foot:** `predicted_human_terrain_class` (easy / caution / unsuitable), `human_probability_*`
- **Crossing directions:** `predicted_*` and `probability_*` for `north_south`, `east_west`, `northwest_southeast`, `northeast_southwest`
- **Physical summaries:** `slope_median_deg`, `slope_p90_deg`, `relative_relief_m`
- **Position:** `top_row`/`top_col` (grid cells within the region; use these for the `CRS.Simple` patch grid). `center_x`/`center_y` are metres in **one shared south-polar stereographic projection** (same `crs_wkt` for all regions), so all 7 regions can go on a single overview map.
- **Cross-check against a simple rule:** `direct_human_terrain_rule`, `cnn_agrees_with_direct_human_rule`. Agreement is 57–82% depending on region. Where they disagree, the CNN is usually more cautious: 820 patches where the rule says *caution* and the CNN says *unsuitable*. This is a useful honesty point for the demo.
- **Terrain grids:** `tensors/<region>_960m.npz` → array `physical` with shape `(patches, 5, 32, 32)`, float32. Channels: `relative_elevation_m`, `slope_deg`, `roughness_90m`, `roughness_330m`, `laplacian_per_m`. Find a patch with `tensor_shard` + `tensor_index`. The app needs only the first two channels. Observed ranges: relative elevation −253 to +258 m, slope up to 34°.

Hanxi also sent the model folder (`temp/terrain_human_walkability_model/…_bd0fc2`: `model.pt`, metrics, splits). The app doesn't need it. Everything is in the inference run.

All outputs are **Earth-trained predictions with no lunar ground truth**. They aren't safety certifications, and the UI must say so.

### Aarron: similarity CNN (A), pending

His pipeline (`dev_aarron`, `pipeline/config.json`) needs three gitignored folders under `data/processed/`:

- `terrain_similarity_cnn/20261101T082707986851Z_5413e6`
- `terrain_learning_readiness/20261101T064233918547Z_4a05ac`
- `terrain_similarity_orientation/20261102T073257899753Z_7b9c4f`

It writes `retrieval.csv`, `physical_comparison.csv` and `summary.json`. **Limitation:** `compare_sites` searches one Moon region against **one named Earth site**. The app needs each lunar patch searched against **all** Earth sites. Notebook 36 does that, but the pipeline doesn't yet.

## Clarifications

Points that could trip up the next developer, including places where the design handoff and this file differ.

1. **This file is the developer handoff, and [`design_handoff_2026-11-13.md`](../../design/handoff/design_handoff_2026-11-13.md) is the design handoff.** Both are current. Use the design handoff for anything about screens and UI behaviour, and this file for data, decisions and blockers.
2. **Environment IDs:** the design handoff says the IDs run `eda_001…eda_083`. That's wrong: 83 is the total row count. Region IDs are only `eda_001`–`eda_017`. The rest are 6 Apollo baselines and 60 test rows.
3. **Design open question 1 (does Unknown blank the scores?): answered.** Yes. An evaluated Unknown hard gate blanks the final score, just like a Failed one.
4. **Design open question 2 (Apollo baselines):** the 6 Apollo rows are in the current CSV. Whether they stay after the Ops/Survivability change, and whether the app shows them, is still a team decision.
5. **Design open question 3 (`eda_*` → regions): answered,** pending Darrel's confirmation. See the region table above.
6. **Domain names:** the real nine domains include `exosphere` and have no "terrain & surface" domain. The wireframes need updating (also noted in the design handoff).
7. **Only `Passed`/`Failed` appear in `hard_gate_status`** in the current file, even though the UI rules talk about Passed/Failed/Unknown. Per-check Unknown status needs the detailed export (blocker 5).
8. **Don't export terrain grids as JSON.** Rounded JSON for all 2,910 patches is about 100 MB. Use Int16 binary at 0.1 m and 0.1° (about 12 MB total, all values fit), one file per region, loaded lazily. Decode in the browser with `Int16Array` and divide by 10.
9. **"Analog" vs "operable" are separate questions.** A high similarity score means similar shape, not easy terrain. Rough lunar terrain can have an excellent rough Earth analog. Keep scores A, B and C visually separate, and never combine them into one number.
10. **The Earth simulation-readiness score doesn't exist yet.** Earth climate, land cover and OSM data were processed in notebooks 03, 04, 26 and 27, but no one has built a score from them. The UI shows a placeholder.
11. **The patch counts in the wireframes are placeholders** (e.g. "412 patches", patch "LBP-0412"). Real counts and IDs come from `predictions.csv`.
12. **The undecided stack choices aren't blockers.** Charting library and host are still open. Pick whichever is faster when you get there.

## Blockers and open questions

| # | Item | Waiting on | Blocks |
| --- | --- | --- | --- |
| 1 | Aarron's three data folders and a sample pipeline output | Aarron (busy) | Earth analog screens 4–5, Earth map |
| 2 | Search each lunar patch against **all** Earth sites, not one named site | Aarron, or us once the data arrives | Analog export |
| 3 | **Patch IDs don't match** between pipelines: Hanxi uses `Region:960:row:col`; Aarron's notebooks use `Region:full_context:row:col:960`. Do the row/col values refer to the same grid? | Aarron + Hanxi | Linking a clicked patch to its analogs |
| 4 | Earth match patches exported as **32×32 grids**, not only PNGs | Aarron | Shared colour scale and crosshair on the pair screen |
| 5 | New CSV with `Ops` + `Survivability`, plus per-check Passed/Failed/Unknown (possibly the `--detailed` export) | Darrel | Final scores, environment tab |
| 6 | Confirm the `eda_*` → region table | Darrel | Region overview |
| 7 | Keep the 6 Apollo baselines in the app? | Team | Apollo comparison on the overview |
| 8 | **Group sign-off** on: static site, no backend, everything precomputed, exported data committed | Whole team | Low risk, but confirm before building on it |
| 9 | Featured patches for the demo (3–5 per region, including one misleading high-score match) | Team | Demo script |
| 10 | Who reruns the export when a model changes (currently Gareth) | Team | Keeping data current |

## Next steps

1. **Write the export script** (e.g. `app/scripts/export_data.py`, run with `.venv`). Inputs: the `temp/` files. Outputs to `app/public/data/`:
    - `regions.json`: 17 regions plus Apollo, with domain scores, gate status, readable fail reasons, final score(s), whether terrain data exists, and patch counts. Write it so the switch to `Ops`/`Survivability` changes one place.
    - `patches/<region>.json`: per patch, its classes, probabilities, directions, physical summaries and grid position.
    - `grids/<region>.bin`: `relative_elevation_m` and `slope_deg` per patch as Int16 × 10, in patch order (see clarification 8). About 12 MB across all regions.
    - Leave a stub for `analogs/<region>.json` with the shape the design handoff describes for source A.
2. **Set up the app shell:** Vite + React + TypeScript, the routes from the design handoff, selection state in the URL.
3. **Build the components that don't depend on visual design:** patch grid (Leaflet `CRS.Simple`), terrain canvas (32×32, shared colour scale, hover readout), status badge (icon + label for every class).
4. **When Aarron's data arrives:** add the analog export, the Earth map and the pair comparison.
5. **Styling:** once the design session delivers its tokens as CSS variables, apply them. Don't hand-pick colours before then.
6. **Ship:** deploy to GitHub Pages or Vercel, then do the demo script, slides or video and the Space Apps project page.

## Repo and tooling

- Nothing from the app or design work has been committed yet. `design/` is untracked.
- Suggested branch: `feature/app` (matches the `feature/hanxi` naming). Merge through a PR.
- Commit `design/PRODUCT.md`, everything in `design/handoff/` and optionally `design/wireframes.html`. **Don't commit** `.impeccable/` or anything in `temp/`.
- Commit notebooks with their outputs saved (repo convention in `README.md`).
