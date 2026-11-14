# Score an uploaded environment CSV

Needs: environment-assessment, publish-demo
Due: 2026-11-15
Priority: stretch. Start only when the other six specs are done. See [area decisions](area.md#decisions).

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

- Run Darrel's files byte-for-byte. Copy them from `dar_dev` and record the source commit. Do not patch them for the browser. If something fails in Pyodide, report it to Darrel.
- The scorer imports PyYAML. Load it with Pyodide's `pyyaml` package.
- Run Pyodide in a Web Worker, so the page stays responsive while it loads and scores.
- Reuse the Operations/Survival display components from `environment-assessment`. Do not build a second results layout.
- Keep each task within three files and three functions or five test cases. Generated files in `app/public/` don't count toward the file limit.

## Verify

- Seam: the upload page in the browser, on the local production preview and then on the hosted site.
- CLI reference output for the parity check, from a `dar_dev` checkout of `darrel stuff/env_pipeline/`:

```powershell
.\.venv\Scripts\python.exe "darrel stuff\env_pipeline\env_pipeline.py" --input "darrel stuff\env_pipeline\sample_input.csv" --output temp\env_cli_reference.csv --overwrite
node app/scripts/check_scorer_parity.mjs temp/env_cli_reference.csv
npm --prefix app run build
npm --prefix app run preview
```

- `check_scorer_parity.mjs` is a proposed script. It does not exist yet. It runs the same files in Pyodide under Node and compares every value with the CLI output.
- In the browser, upload `sample_input.csv` unchanged and one invalid file per error type. Check the network panel: Pyodide loads once per visit.

## Decisions

- **Run Darrel's unmodified scorer in the browser with Pyodide, not a TypeScript port.** Scores stay identical to his CLI, and his updates are a file copy. He changed the scorer on 13 Nov. A port meant 745 lines to rewrite by 15 Nov and re-port on every change. Cost: about 10 MB downloaded on the first upload. (2026-11-13)

## My calls

- Load Pyodide from its pinned jsDelivr build. Self-host it only if the demo venue blocks the CDN.
- Run the exporter's environment adapter in the same worker, so uploaded and precomputed results share one normalized format. This needs `environment-assessment` to put its adapter in its own standard-library-only module.
- Call Darrel's `run()` on files in Pyodide's virtual filesystem, so his file checks and error messages apply unchanged.
- Use Darrel's `sample_input.csv` as the template. A second, shorter template was planned, but one file is less to keep in step with his scorer.

## Tasks

- [ ] Export Darrel's `env_pipeline.py` and `config.yml` into `app/public/`, with their source commit and file hashes. Verify the hashes match `dar_dev` and come from the same commit as the published `sample_input.csv`.
- [ ] Add the Pyodide worker that loads PyYAML, runs Darrel's `run()` and the environment adapter on an uploaded CSV, and returns results or the error message. Add `check_scorer_parity.mjs` and verify all 83 sample rows match the CLI output.
- [ ] Add the upload page with the sample download, file picker, loading state, and error display. Verify each invalid-file case shows Darrel's message and no partial results.
- [ ] Render uploaded rows with the environment tab's Operations and Survival components and the user-supplied label. Verify a passing row and a blank-score row against the CLI output.
- [ ] Run the upload walkthrough on the production preview and the hosted site. Verify the sample download, one upload, and that a second upload does not reload Pyodide.
