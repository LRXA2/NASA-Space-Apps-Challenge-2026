# Score an uploaded environment CSV

Needs: environment-assessment
Due: 2026-11-15
Implementation exists. Hosted acceptance waits on `publish-demo`. See [area decisions](area.md#decisions).

## Goal

Let a user download an environment input template, fill it with their own site values, upload it, and see Operations and Survival results computed in the browser.
This goes one step past what the team settled on in chat on 13 Nov, without a backend. See [shared context](area.md#shared-context).

What the chat settled: show precomputed results, and give a button to download a sample input file. That button ships in `environment-assessment`.
What stays open: Aarron asked for new lunar sites to run through all the pipelines. This spec covers Darrel's scorer only.

## Done when

- The sample download from `environment-assessment` sits beside the upload control. No second template file is needed.
- Uploading a filled CSV scores every row in the browser with Darrel's unmodified `env_pipeline.py` and `config.yml`. No request leaves the browser except loading Pyodide.
- Each uploaded row shows its Operations and Survival results in the environment tab's layout: domain scores, status, failure reason, and final score. The page labels the rows as user-supplied, not NASA candidate sites.
- Scoring Darrel's `sample_input.csv` in the browser gives the same values as his CLI output for all 83 rows.
- A file with an unregistered column, an out-of-range value, a duplicate ID, a ragged row, or no rows shows Darrel's error message and no partial results.
- The first upload shows a loading state while Pyodide downloads. A second upload in the same visit does not download it again.
- The sample download and an upload work on the hosted site, not only on the local preview.

## Out of scope

- Uploads for the terrain or similarity CNNs, raw elevation files, and any backend.
- Saving, sharing, or linking to uploaded results. Results last only until the page reloads.
- Editing weights, gates, or other `config.yml` settings in the UI.
- Adding uploaded rows to the region catalogue or comparing them with the 17 Artemis regions.

## Constraints

- Copy Darrel's scorer logic and config from `env_algo_task/env_pipeline/`. Normalize text line endings to LF and hash the published bytes. Do not patch scoring logic for the browser.
- The scorer imports PyYAML. Load it with Pyodide's `pyyaml` package.
- Run Pyodide in a Web Worker, so the page stays responsive while it loads and scores.
- Reuse the Operations/Survival display components from `environment-assessment`. Do not build a second results layout.
- Keep each task within three files and three functions or five test cases. Generated files in `app/public/` don't count toward the file limit.

## Verify

- Seam: the upload page in the browser, on the local production preview and then on the hosted site.
- Generate a detailed CLI reference from the scorer on the current checkout. A complete pipeline bundle is not needed:

```powershell
.\.venv\Scripts\python.exe env_algo_task\env_pipeline\env_pipeline.py --input env_algo_task\env_pipeline\sample_input.csv --output temp\env_cli_reference.csv --detailed --overwrite
node app/scripts/check_scorer_parity.mjs temp/env_cli_reference.csv
npm --prefix app run build
npm --prefix app run preview
```

- `check_scorer_parity.mjs` exists and runs the published files in Pyodide under Node. It compares detailed output after masking only the config hash that can differ with line endings.
- In the browser, upload `sample_input.csv` unchanged and one invalid file per error type. Check the network panel: Pyodide loads once per visit.

## Decisions

- **Run Darrel's unmodified scorer in the browser with Pyodide, not a TypeScript port.** Scores stay identical to his CLI, and his updates are a file copy. He changed the scorer on 13 Nov. A port meant 745 lines to rewrite by 15 Nov and re-port on every change. Cost: about 10 MB downloaded on the first upload. (2026-11-13)

## My calls

- Load Pyodide from its pinned jsDelivr build. Self-host it only if the demo venue blocks the CDN.
- Run the exporter's environment adapter in the same worker, so uploaded and precomputed results share one normalized format. This needs `environment-assessment` to put its adapter in its own standard-library-only module.
- Call Darrel's `run()` on files in Pyodide's virtual filesystem, so his file checks and error messages apply unchanged.
- Use Darrel's `sample_input.csv` as the template. A second, shorter template was planned, but one file is less to keep in step with his scorer.

## Tasks

- [x] Export Darrel's `env_pipeline.py` and `config.yml` into `app/public/`, with their source commit and file hashes. Verify the hashes match `dar_dev` and come from the same commit as the published `sample_input.csv`. Historical note, 14 Nov: the published hashes match the files. The export records paths and SHA-256, not a source commit.
- [x] Add the Pyodide worker that loads PyYAML, runs Darrel's `run()` and the environment adapter on an uploaded CSV, and returns results or the error message. Add `check_scorer_parity.mjs` and verify all 83 sample rows match the CLI output. Historical note, 14 Nov: the 83-row comparison passed in `test_score_upload.py`. `check_scorer_parity.mjs` was not run, because no reference CSV is on this machine.
- [x] Add the upload page with the sample download, file picker, loading state, and error display. Verify each invalid-file case shows Darrel's message and no partial results. Historical note, 14 Nov: checked one invalid file on the preview. It showed the scorer's message and no results.
- [x] Render uploaded rows with the environment tab's Operations and Survival components and the user-supplied label. Verify a passing row and a blank-score row against the CLI output. Historical note, 14 Nov: 83 rows rendered on the preview. A blank-score row was not checked.
- [ ] Run the upload walkthrough on the production preview and the hosted site. Verify the sample download, one upload, and that a second upload does not reload Pyodide. (blocked: hosting deferred by Ian. Local checks passed on 15 Nov: scorer/template hashes, Pass/Fail/Unknown uploads, row navigation, five invalid files, and worker reuse. The 83-row Pyodide parity check also passed)

## Results

Verified on 2026-11-15 against `8769b86` plus the local upload navigation fix.
The published scorer files and template match their SHA-256 hashes.
Gareth's input guide remains unchanged. The browser check verifies its complete column list, expanded mobile layout, and automated accessibility.
`npm --prefix app run check:scorer -- /tmp/nasa-app-qa/reference.csv` matches all 83 current CLI rows in Pyodide 0.28.3.
The reference was generated with the current scorer's `--detailed` mode. See Verify above for portable commands.
`npm --prefix app run check:browser` checks Pass, Fail, and Unknown upload rows, expanded gate evidence, and worker reuse.
Duplicate IDs, unknown columns, out-of-range values, empty input, and ragged rows show errors and clear old results.
Opening a result now expands and focuses its details without changing the app route. This fixes a reproduced Page not found error.
All 29 app-script tests and the production build pass. Automated accessibility checks pass on expanded upload results.
Hosted acceptance is deferred. Gate/weight editing and CNN terrain uploads are not implemented.
