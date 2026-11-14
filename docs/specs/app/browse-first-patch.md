# Browse the first real patch

Due: 2026-11-15

## Goal

Open one lunar region and inspect one real terrain patch in a working React app.
This connects the data export to the UI before expanding coverage. See [shared context](area.md#shared-context).

## Done when

- Running the exporter on an integrated pipeline bundle produces region metadata, patch metadata, and a binary terrain file for the selected patch.
- The export preserves the source patch ID, run ID, classes, probabilities, crossing predictions, physical summaries, and tensor location.
- Decoded terrain contains two 32-by-32 grids: relative elevation in metres and slope in degrees. Quantization error is at most 0.05 in each unit.
- In the running app, a region entry opens its real patch. The patch URL can be copied, reopened, and reached with browser navigation.
- The patch screen shows rover and walking classes with text and an icon, model probabilities, four undirected crossing axes, and physical summaries.
- Two labelled canvases show the actual source grids. Hovering a cell shows its row, column, value, and unit. A legend explains each colour scale.
- Missing exports, unknown routes, invalid binary lengths, and unavailable patches produce readable errors without invented results.
- A production build and browser walkthrough pass. Displayed predictions match the source CSV, and selected cell values match its tensor within the stated tolerance.

## Out of scope

- All seven regions, the Leaflet patch map, Earth analogs, environment scores, and final visual styling.
- Uploads, backend processing, live inference, model training, and interpreting an ordinary photograph as terrain input.

## Constraints

- Follow Gareth's layouts and the [area decisions](area.md#decisions). A working screen is required. An isolated exporter is insufficient.
- Run Python 3.12 with repository-relative paths. Select the integrated input bundle with `--pipeline-run`.
- Read Hanxi's `20261112T120422201915Z_101366` run through the integrated bundle's manifest. Do not load model weights or rerun inference.
- Read only the two required physical channels. Do not change normalization, orientation, heights, predictions, or source files.
- Preserve source IDs separately from readable route names. Normalize Windows path separators and reject tensor paths outside the selected run.
- Reject duplicate IDs, missing tensor references, invalid shapes, nonfinite values, and signed 16-bit overflow. Use `allow_pickle=False` for tensor files.
- Export finite JSON and compact binary. State schema version, patch order, grid shape, channel order, scale, units, and byte order in metadata.
- Keep probability labels explicit: model confidence does not establish safety. Include the terrain-specific limitations from the handoff.
- Each task touches at most three files and adds at most three functions or five test cases. Generated files in `app/public/data/` don't count toward the file limit.

## Verify

- Seam: run the exporter against the actual local input bundle, serve the app, and follow the region-to-patch flow in a browser.
- These commands exist. Regeneration requires the integrated bundle and its referenced datasets. Building the committed app does not.

```powershell
.\.venv\Scripts\python.exe app\scripts\export_data.py --pipeline-run data/processed/moon_pipeline/<run> --region leibnitz-beta-plateau --patch-id "A3CLR22_10_Leibnitz_Beta_Plateau:960:32:32" --output-dir app/public/data
.\.venv\Scripts\python.exe -m unittest discover -s app/scripts/tests -p "test_*.py"
npm --prefix app run dev
npm --prefix app run build
npm --prefix app run preview
```

- Replace `<run>` with a completed bundle on the machine running the export. This checkout currently lacks that bundle and `.venv`.
- In the browser, check a known cell, back/forward navigation, a copied patch URL, a missing data file, and an invalid patch ID.
- Until hosting is selected, verify URLs through the local development and preview servers. Hosted deep links belong to `publish-demo`.

## Decisions

- Start with one real region and patch instead of an exporter-only milestone: see [area decisions](area.md#decisions).

- **Use hash routes (`#/region/...`) from a small router in `app/src/router.ts`, with no routing library.** They work on any static host without rewrite rules, and the smallest approach was asked for. Cost: URLs differ from the handoff's path form. Only `router.ts` knows the URL form, so `publish-demo` can still change it. (2026-11-13)
- **Fit each colour scale to the patch it shows.** One fixed scale for all patches needs the range of every region, which this spec does not export. Cost: colours are not comparable between patches, and the legend says so. `compare-terrain` passes a shared scale instead. (2026-11-13)
- **Use placeholder colours as CSS variables in `app/src/styles/tokens.css`.** Gareth's tokens replace that one file. Terrain ramps are in `app/src/components/colorScales.ts`. (2026-11-13)

## My calls

- Use Leibnitz Beta Plateau and source patch `A3CLR22_10_Leibnitz_Beta_Plateau:960:32:32` for the first walkthrough. This is a stable example, not a selected best site.
- The first release used schema version 1. Integration now uses version 2, retaining the same little-endian terrain layout.
- Round physical values multiplied by 10. Store byte offsets explicitly. Browser decoding must respect little-endian order and divide by 10.
- Use neutral styles and labelled scales initially. Gareth's final tokens can replace the presentation without changing the data contract.
- Select no routing or UI test library in this spec. Use the smallest approach that meets the browser checks and record any consequential choice before implementation.

## Tasks

- [x] Add a minimal Vite/React boot page, dependency commands, and ignore rules in at most three files. Verify the development page and production build. Keep temporary package installation from creating an extra tracked lockfile in this task.
- [x] Add region metadata export with optional patch selection, source IDs, validation, and command documentation. Verify real values and rejected records.
- [x] Add binary terrain export and its metadata contract. Check tensor identity, shape, byte order, quantization, and overflow with at most five focused test cases.
- [x] Add typed browser loading and binary decoding with readable unavailable/error states. Verify a decoded source cell and a truncated file through the boot page.
- [x] Add the real region entry and URL-addressable patch selection. Verify copied links, unknown selections, and back/forward navigation.
- [x] Render the selected patch's classes, probabilities, crossing axes, and measurements with labelled status badges. Compare them with the source row.
- [x] Draw slope and relative elevation with legends and hover readouts. Verify orientation, cell coordinates, units, and the prediction limitations in the browser.
- [x] Publish the first region JSON, patch JSON, and grid binary as the three app data files. Run the exporter checks, production build, and full browser walkthrough on those files.

## Results

Historical checks from 2026-11-13 used this macOS checkout (Python 3.12.3, NumPy 2.4.4, Node 26.5, Vite 8.3).
The initial app was committed in `3458c47`. Integration later replaced its raw-input CLI with `--pipeline-run`.
Commands and observations below describe that initial release, not a fresh rerun.

- Export: `python3 app/scripts/export_data.py --input-dir data/app_inputs --region leibnitz-beta-plateau --patch-id "A3CLR22_10_Leibnitz_Beta_Plateau:960:32:32"` wrote `regions.json`, `patches/leibnitz-beta-plateau.json` and a 4,096-byte `grids/leibnitz-beta-plateau.bin`.
- Exporter tests: 10 pass (`python3 -m unittest discover -s app/scripts/tests -p "test_*.py"`). They cover preserved source values, patch selection, duplicate IDs, unknown classes and regions, Windows path separators, paths outside the run, tensor identity, quantization tolerance, int16 overflow, non-finite values, wrong shapes, missing files and bad tensor indices.
- Build: `npm --prefix app run build` passes, including the TypeScript check.
- Browser, production preview: the region list opens the region, and the region opens the patch. A pasted patch URL opens directly. Back and forward work.
- Displayed predictions match `predictions.csv`: rover operable 0.80 / 0.20 / 0.00, on foot caution 0.01 / 0.97 / 0.02, crossing 0.95 / 0.95 / 0.82 / 0.92, slopes 8.9° and 12.8°, relief 180.1 m.
- Hover readouts match the source tensor: relative elevation at row 0 column 0 is −86.6 m (source −86.59), row 0 column 31 is −15.1 m (−15.12), row 31 column 0 is 7.8 m (7.76), row 12 column 5 is −48.2 m (−48.17). Slope at row 12 column 5 is 10.5° (10.55). This confirms row 0 is drawn at the top.
- Error states, checked on the built files: a truncated grid file (4,000 bytes), a missing grid file, a missing `regions.json`, an unknown region, an unknown patch and an unknown route each show a readable message. Predictions stay visible when only the grid file is bad.
- Also checked: arrow-key readout, phone width (375 px, no sideways scroll), light and dark colour schemes.

Limitations recorded at the initial check:

- The initial check did not test Gareth's Windows setup. Later team checks are recorded in `docs/architecture.md`.
- The package lockfile was outside the initial commit. It is now tracked in `app/package-lock.json`. A fresh install remains a publishing check.
- The boot task touched more than three files (Vite needs `package.json`, `tsconfig.json`, `vite.config.ts`, `index.html` and `src/main.tsx`).
- Styling is neutral. Gareth's layout and tokens are not applied.
- `.claude/launch.json` was added for local preview servers. It is a local tool file and is not in the commits.

Current record review, 2026-11-14: schema v2, the hash router, and committed exports are present.
`python3 -m unittest discover -s app/scripts/tests -p 'test_*.py'` passes all 27 app-script tests.
`npm --prefix app run build` passes the TypeScript check and Vite build. No new browser walkthrough was run.
All existing tasks remain checked. Final acceptance and `Status: done` remain for review.

### Verification, 2026-11-15

Checked `8769b86` plus the local interaction fixes with `npm --prefix app run check:browser`.
Copied links, refresh, browser history, invalid region/patch routes, and truncated terrain files pass the production browser check.
Automated accessibility and page-overflow checks pass at 1440 px and 375 px.
The production build and all 29 app-script tests pass. These results replace earlier pending local checks above.
Final feature acceptance remains for review.
