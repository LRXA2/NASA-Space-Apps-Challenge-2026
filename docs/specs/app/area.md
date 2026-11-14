# App

Owns the working application for browsing lunar assessments and comparing Earth terrain analogs.
This includes app data exports, React screens, maps, charts, navigation, and publishing the demo.
Planned code: `app/`. Research pipelines and model training remain owned by the pipeline teammates.

## Specs

All seven specs are written. They contain proposed checks and tasks, not completed implementation.

Build them in the order listed. The order is by value to the challenge, which asks for Earth analogs. `Needs:` lines are hard dependencies only.
If the next task waits on a teammate's data, take the next unblocked task further down. Return to the waiting spec as soon as its data arrives.

1. `browse-first-patch`: Open one real region and patch, inspect rover and walking predictions, and view slope and relative elevation. Include the minimum React app and data export needed for this flow.
2. `publish-demo`: Open the working demonstration through a hosted link, including direct screen links and navigation. Deploy after the first feature, then redeploy as later specs merge. Needs: browse-first-patch.
3. `browse-regions`: Browse all seven prepared terrain regions and their patches. Needs: browse-first-patch.
4. `earth-analogs`: View ranked Earth matches and their locations for a lunar query patch. Starts with the nine real matches from notebook 36, then Aarron's full bundle. Needs: browse-regions.
5. `compare-terrain`: Compare a Moon–Earth pair using terrain grids or figures, physical differences, and distribution charts. Needs: earth-analogs.
6. `environment-assessment`: Inspect the 17 Artemis-region scenarios, domain scores, failed checks, and regions without terrain data. Needs: browse-regions.
7. `environment-upload` (stretch): Upload a filled copy of the sample input and see Operations and Survival scores computed in the browser. The sample download itself ships in `environment-assessment`. Start it only when specs 1 to 6 are done. Needs: environment-assessment, publish-demo.

## Shared context

### Product and designs

- [Product brief](../../../design/PRODUCT.md): audience, purpose, scope, and product constraints.
- [Design handoff](../../../design/handoff/design_handoff_2026-11-13.md): layouts, routes, and interactions.
- [Developer handoff](../../handoff/developer_handoff_2026-11-13.md): data details and corrections to the design handoff.
- [Wireframes](../../../design/wireframes.html): clickable HTML layouts with sample values. They are not the React implementation or scientific results.
- [Research outline](../../../outline.md): pipeline context. Active scope is Earth and Moon only.
- Gareth has supplied layouts. Ian's app work includes both data integration and UI implementation. Detailed ownership between Ian and Gareth remains unassigned.

### Inputs and pipeline boundaries

- Hanxi (`feature/hanxi`) supplies rover and walking predictions, crossing directions, and terrain tensors.
- Use inference run `terrain_human_walkability_lunar_inference/20261112T120422201915Z_101366`: 2,910 patches in seven regions, each 960 m square on a 30 m grid.
- Each tensor contains five 32-by-32 channels. The app initially needs relative elevation and slope. Use `tensor_shard` and `tensor_index` to locate them.
- Darrel (`dar_dev`) supplies environmental scores. The current 83 rows contain 17 Artemis-region scenarios, six Apollo baselines, and 60 test cases.
- Exclude synthetic and dummy cases from the region catalogue. Preserve whether scenario values are measured, modeled, or assumed.
- Darrel's scorer changed on 13 Nov (`dar_dev`, `eb4edbf`). It now writes two assessments, `operations` and `survival`, each with domain scores, a `Pass`/`Fail`/`Unknown` status, a failure reason, and a final score. `seismic`, `exosphere` and `communications_geometry` are gone. `soil` and `earth_visibility` are new.
- The received `results.csv` still uses the old format (`final_habitability_score`, nine domains). New-format results from Darrel have not arrived.
- Aarron (`dev_aarron`) supplies retrieval and physical comparisons. His current wrapper searches one Moon region against one Earth region.
- Notebook 36 already holds real results: three lunar queries (Leibnitz, Haworth, Malapert), each searched against all five Earth sites, top 3 each. Its saved outputs are in Git. Its files (`retrieval.csv`, `physical_comparison.csv`, `selected_queries.csv`, PNG figures, `DEMO.md`) are on Aarron's machine under `reports/terrain-similarity-oriented-demo/20261104T003123532042Z/`.
- One of those nine matches is a real misleading match: Haworth rank 2 (Wadi Rum) has cosine 0.974 and 0 of 5 physical checks in band.
- Aarron's query IDs sit at rows and columns such as `144:112`, `272:368` and `432:368`. Hanxi's patches sit on multiples of 32. If both count 30 m cells from one origin, the notebook 36 queries are half a patch off Hanxi's grid. The units and origin are unconfirmed.
- Gareth asked Aarron in the team chat on 13 Nov for the three data folders in `pipeline/config.json` and one finished Haworth–Wadi Rum run. Aarron said he would send them that evening. Nothing from Aarron is in this checkout yet.
- Full coverage (every lunar patch against all Earth sites, with Earth terrain grids) is still the target. The analog screens no longer wait for it.
- Similarity, environment, and terrain predictions answer different questions. Keep their results separate.
- Earth simulation readiness has no implemented score. Show it as unavailable until supported results exist.

### Planned layout and naming

- `app/scripts/export_data.py`: convert pipeline outputs to browser data files.
- `app/src/pages/` and `app/src/components/`: React pages and reusable components, with PascalCase filenames such as `PatchPage.tsx`.
- `app/src/data/`: TypeScript data definitions and loaders. Use lowercase or camelCase filenames such as `types.ts` and `loaders.ts`.
- `app/src/styles/tokens.css`: shared design values when Gareth supplies the visual design.
- `app/public/data/`: exported region metadata, patch metadata, terrain grids, and later analog results.
- Use lowercase names with dashes for specs, route names, and region filenames, such as `browse-first-patch` and `leibnitz-beta-plateau`.
- Preserve original source IDs inside exported records. A readable route name does not replace the source identity.
- Follow the developer handoff's compact terrain format: per-region binary grids with signed 16-bit values scaled by 10.
- The first feature spec defines the proposed ordering and units. Review its small implementation choices before starting its tasks.

### Gareth's machine and this checkout

- Target Gareth's documented Windows setup: Python 3.12, `.venv\Scripts\python.exe`, and input bundles under `temp/`.
- Proposed export command from the repo root: `.venv\Scripts\python.exe app\scripts\export_data.py`.
- Keep paths relative to the repo and allow an input directory option. Do not hardcode either person's home directory.
- This checkout has the received artifacts under `data/app_inputs/`, including `results.csv` and Hanxi's inference run. It has no `temp/` or `.venv` yet.
- Input bundles, models, and local environments stay ignored by Git. The working static plan commits app exports under `app/public/data/`.
- Gareth's reported environment and test results are evidence from his machine, not verification of this checkout.

## Decisions

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

## Open questions

- **Open:** How should users upload new lunar sites for the two CNNs: raw elevation files or prepared 32-by-32 tensors? Raw files would need a backend for preprocessing. No CNN upload is planned for the weekend.
- In the 13 Nov chat Aarron described the CNN input as "just an image". Both CNNs read elevation-derived grids, not photographs. Confirm with him what a user would supply before anyone promises a CNN upload.
- The team chat on 13 Nov agreed to show precomputed results and a sample input download. Darrel's scorer needs only the standard library and PyYAML, which Pyodide ships, so `environment-upload` can run in the browser without a backend. The static stack does not change.
- **Open:** Which app components will Ian and Gareth each own as implementation starts?
- **Open:** Which chart library and static host should the later features use? The developer handoff leaves both undecided.
- **Open:** Should the app include the Apollo reference scenarios? Will Darrel keep hard gates switched off? With gates off, no scenario fails.
- **Open:** Do Aarron's `row:col` values count 30 m cells from the same origin as Hanxi's `top_row`/`top_col`? If yes, which of Aarron's queries land exactly on a Hanxi patch? Ask Aarron, or check `patches.csv` footprints against Hanxi's `center_x`/`center_y` when the `terrain_learning_readiness` folder arrives.
- **Open:** Which real matches should be featured beyond the nine from notebook 36?
- **Open:** Who regenerates and reviews exported data when pipeline results change?
