# App

Owns data export, React screens, maps, charts, navigation, and publishing for the Lunar Analog Finder.
Code lives in `app/`. Research pipelines and model training remain owned by the pipeline teammates.

## Specs

These seven specs describe the implemented app and its remaining acceptance work.
Checked tasks record prior implementation. A spec is not formally done until its acceptance is reviewed and `Status: done` is recorded.

- `browse-first-patch`: Open a real region and patch, inspect predictions, and view terrain grids.
- `publish-demo`: Publish the existing app and verify hosted routes, assets, and the walkthrough. Live on GitHub Pages. Needs: browse-first-patch.
- `browse-regions`: Browse seven terrain regions and all 2,910 patches. Needs: browse-first-patch.
- `earth-analogs`: Inspect each patch's 15 Earth matches from the integrated run. Needs: browse-regions.
- `compare-terrain`: Compare actual Moon–Earth grids, five physical checks, and distributions. Needs: earth-analogs.
- `environment-assessment`: Inspect Operations and Survival scores, gate evidence, and environment-only regions. Needs: browse-regions.
- `environment-upload`: Score a filled environment CSV in Pyodide. Works locally and on the live site. Needs: environment-assessment.

## Shared context

### Current records and designs

- [Architecture](../../architecture.md): pipeline, export schema, routes, and browser upload.
- [Team questions](../../team-blockers.md): recorded answers and remaining team choices.
- [Featured tiles](../../featured-tiles.md): the three demonstration patches per region (T6).
- [Product brief](../../../design/PRODUCT.md): current product scope and constraints.
- [Design handoff](../../../design/handoff/design_handoff_2026-11-13.md) and [wireframes](../../../design/wireframes.html): historical planning snapshots.
- [App README](../../../app/README.md): commands, data format, and routes.
- Ian handles app integration and verification. Gareth designed the app and its theme, chose the host, and owns export regeneration (T7).

### Implemented data flow

- `integration.run_all` joins terrain, similarity, and environment outputs through a shared lunar `tile_id`.
- All 2,910 exported patches have terrain predictions and 15 Earth matches: top three from each of five Earth sites.
- Schema v2 exports come from one `moon_pipeline/<run>/` bundle. The exporter also reads its referenced terrain and similarity dataset runs.
- The committed app uses run `20261115T070913357556Z_0070bc` with region-scope environment scores. Rebuilding tile scope needs the LOLA maps.
- Darrel's scorer supplies separate Operations and Survival assessments. Their domain lists are read by prefix, not hardcoded in the UI.
- The committed environment catalogue contains 17 Artemis scenarios and six separately labelled Apollo references. Synthetic and dummy test rows are excluded.
- The detailed export supplies gate values, thresholds, statuses, reasons, and coverage. Failed or Unknown assessments keep their final scores blank.
- Current Artemis results are Operations 14 Pass / 3 Fail and Survival 17 Pass. Thresholds are project test values, and most environmental inputs are best-effort estimates.
- Environment CSV uploads run the unmodified scorer logic in a Pyodide worker. Published text uses LF line endings and SHA-256 hashes.
- CNN ONNX exports were checked offline. No terrain-upload worker or model bank is shipped by the current app.
- Similarity, environment, and terrain predictions stay separate. Earth simulation readiness remains uncomputed.

### Layout and setup

- `app/scripts/`: exporter, shared environment adapter, upload helper, and verification scripts.
- `app/src/pages/` and `app/src/components/`: React screens and reusable views.
- `app/src/data/`: schema types, loaders, and binary decoding. `router.ts` owns hash URLs.
- `app/public/data/`: committed schema v2 JSON, grid binaries, environment template, and scorer files.
- Keep PascalCase React filenames, snake_case Python filenames, and lowercase route names with dashes.
- Route names preserve original source IDs inside the data. Pair links use Earth candidate IDs, with numeric-index compatibility.
- Gareth's Windows setup uses Python 3.12 and `.venv\Scripts\python.exe`. This checkout has no full pipeline bundle.
- Use `--pipeline-run` to select a bundle. The exporter no longer accepts the earlier `--input-dir`, `--analogs-dir`, or `--environment-file` proposals.
- Python dependencies are locked in `uv.lock`. Both `scripts/prepare_demo.ps1` and `scripts/prepare_demo.sh` now exist.
- The preparation scripts rerun research integration. Viewing or building committed app exports needs only the Node app setup.

## Decisions

Historical 13 November entries below explain the earlier plan. The dated replacement entries describe the current implementation.

- **Plan one app area for data integration and UI implementation.** A data-only assignment was considered, but Ian wants to build the app and approved this combined scope. (2026-11-13)
- **Start with one real region and patch on screen.** This replaces the proposed exporter-only first feature and proves that data conversion and UI rendering connect. (2026-11-13)
- **Write all six feature specs now.** Ian explicitly requested the full approved feature list. Later specs retain data blockers and open choices. (2026-11-13)
- **Keep records in `docs/` and application code in `app/`.** This is one repository, not a workspace containing several repositories. (2026-11-13)
- **Deploy after the first feature, not at the end.** `publish-demo` waited on `earth-analogs` and `compare-terrain`, which are blocked on Aarron. With a 15 Nov deadline, the site might never have shipped. (2026-11-13)
- **Generated data files don't count toward the three-file task limit.** One exporter run writes all seven regions. Counting its output split `browse-regions` into seven near-identical tasks. (2026-11-13)
- **Build the Earth analog screens before the environment screens.** The challenge asks for Earth analogs and where each analogy fails. The environment screens score lunar sites, which is context. The old order left the analog screens fifth and sixth, behind 12 environment tasks. Cost: the environment tab and the upload may not ship. (2026-11-13)
- **Start the analog screens from notebook 36, not from Aarron's full bundle.** Nine real matches exist today, so the screens do not wait on a new export. Cost: three query patches only, top 3 each, and the app must say so. (2026-11-13)
- **Key analog pages on Aarron's query IDs, not on Hanxi's patch IDs.** The two grids appear to be offset, so a required join blocked every analog task. Hanxi's predictions appear on an analog page only where a footprint match is confirmed. Cost: an analog query is not always reachable from a patch page. (2026-11-13)
- **Ship the sample input download early. Scoring an upload is a stretch goal.** The 13 Nov chat ended on "an action button that allows them to download this file", which is one task in `environment-assessment`. Scoring in the browser is five tasks and shows no Earth analog. Aarron asked for new-site input, so tell him if scoring is cut. (2026-11-13)
- Use Gareth's Vite, React, TypeScript, Leaflet, and canvas plan as the implementation baseline. The initial flow reads saved results and does not run models live.
- **Use the integrated pipeline instead of notebook-only analog exports.** `tile_id` joins all 2,910 terrain patches. This replaces the earlier notebook-first and independent-query plans. (2026-11-14)
- **Use schema v2 and hash routes with a relative base path.** These are implemented in the exporter, router, and Vite configuration. (2026-11-14)
- **Draw pair distributions in plain SVG in the browser.** This replaces the proposed chart-library choice and offline curve export. See [comparison decisions](compare-terrain.md#decisions). (2026-11-14)
- **Keep engineering status in `docs/` and feature specs in `design/docs/specs/`.** This was the earlier layout. (2026-11-14, replaced 2026-11-15)
- **Keep engineering records together under `docs/`.** Gareth moved specs to `docs/specs/app/`. UI designs remain under `design/`. This replaces the split records layout. (2026-11-15)
- **Use the exploration theme instead of the mission-control theme.** Aarron preferred it because the project supports reconnaissance. Gareth confirmed that direction at 20:12 in the team chat. Implementation and design review remain separate. (2026-11-14)

- **Use Playwright and axe-core for repeatable browser checks.** These are development dependencies only. They verify real production files, including the Pyodide worker, without opening a listening port. This replaces one-off browser probes for the current acceptance checks. ^[inferred] (2026-11-15)
- **Present Apollo references separately with best-effort input labels.** Darrel's T3 answer permits Operations and Survival comparisons, while requiring clearer input caveats. No terrain coverage or suitability is implied. (2026-11-15)

- **Team answers T1, T2 and T4–T6, 2026-11-15.** Environment-only uploads for the submission, with elevation uploads later (T1). GitHub Pages, chosen by Gareth once the repo was public (T2). Region-scope environment scores, labelled as shared by every patch in a region (T4). The static architecture is kept (T5). Three featured tiles per region: strong match, misleading high cosine, not Atacama (T6). (2026-11-15)
- **Remove finished planning docs.** The theme build guide and the 13 Nov developer handoff were superseded by the code, [architecture](../../architecture.md) and this file. They remain in git history. (2026-11-15)

- **Gareth regenerates the export by hand (T7).** Only when a CNN, the scorer or its template, the regions or the export format changes. See [regenerate-export.md](../../regenerate-export.md). (2026-11-15)

- **Keep the missing-column test on a dummy row.** Darrel's default `inputs/sites.csv` had blanked sky and radiation inputs on `eda_016` and `eda_017` to show the scorer's missing-value check. Darrel moved that test to `dummy_009` (hidden on the site) and restored both regions' values. `sample_input.csv` matches his file. Export regenerated from `20261115T070913357556Z_0070bc`. (2026-11-15)

## Open questions

- Does the team approve the completed feature acceptance after a real screen-reader pass?
