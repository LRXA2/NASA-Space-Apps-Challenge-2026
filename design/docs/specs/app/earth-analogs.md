# Browse Earth terrain analogs

Needs: browse-regions
Due: 2026-11-15

## Goal

Open a lunar query patch's saved Earth matches and inspect their rank, physical agreement, and location.
Show the search scope and missing coverage rather than implying every patch has validated analogs. See [shared context](area.md#shared-context).

This is the screen that answers the challenge. Build it from the first real data available, then widen coverage.

## Data sources, smallest first

1. **Notebook 36 (exists now).** Three lunar queries, each searched against all five Earth sites, top 3 each: nine matches. The saved outputs are in Git. The files are on Aarron's machine under `reports/terrain-similarity-oriented-demo/20261104T003123532042Z/`.
2. **One pipeline run (asked for on 13 Nov).** Gareth asked Aarron in the team chat for a finished `--moon-site Haworth --earth-site wadi_rum` run: `retrieval.csv`, `physical_comparison.csv`, `summary.json` and plots. Aarron said he would send it that evening. It covers every prepared Haworth patch against Wadi Rum only, top 3.
3. **All Moon regions against all five Earth sites.** Gareth also asked for the three data folders named in `pipeline/config.json`. With them, we can run the remaining site pairs ourselves. This is the full coverage target, not a starting condition.

The screens must work with source 1 alone. Sources 2 and 3 add queries through the same export.

## Done when

- Every published match has a traceable model/run identity, a named candidate pool, a query patch identity, and its physical-comparison records.
- Analog pages are keyed on the similarity pipeline's own query IDs, such as `A3CLR22_2_Haworth:full_context:272:368:960`. They do not need a matching patch in Hanxi's run.
- A region page lists its available analog queries. Each opens an analog page with a copyable URL.
- Rover and walking predictions appear on an analog page only for a query with a confirmed footprint match to a Hanxi patch. Otherwise the page says the predictions use a different patch grid.
- A patch page links to analogs only when its footprint match is confirmed. Otherwise it says analog results are unavailable for that patch.
- The analog page shows every supplied match in original rank order, with Earth region, cosine score, coordinates, and physical-check counts.
- The UI displays cosine as a similarity measure, not a percentage or safety rating. Weak physical matches remain visible.
- A Leaflet Earth map uses supplied Earth latitude/longitude, numbered markers, visible attribution, and a list fallback if tiles fail.
- Hovering or selecting a result links its table row and map marker. Opening a result reaches a stable pair URL, with comparison availability stated.
- Each query names its actual candidate pool, such as "all five sites" or "Wadi Rum only", and how many queries the region has. A missing bundle produces no fake matches.
- A production browser walkthrough checks one real query, the Haworth rank 2 match (cosine 0.974, 0 of 5 checks in band), and an unavailable patch against the source files.

## Out of scope

- Running the similarity model in the app, retraining, changing rankings, processing uploads, or modifying a teammate's pipeline branch.
- Earth readiness scoring, declaring global search coverage, and the detailed pair charts supplied by `compare-terrain`.

## Constraints

- Name the candidate pool on every result list. Describe results as the closest across all five sites only when the search covered all five.
- Every pipeline run reads the one embedding cache pinned in `pipeline/config.json`, so cosine scores from different Earth-site runs are comparable. Merge per-site lists only when each run's manifest names the same model, dataset and orientation runs.
- A merged top 3 is exact only when every per-site run kept at least 3 matches. Recompute rank after merging and keep each source rank in the record.
- The terrain and similarity runs use different patch grids and source versions. A footprint match needs the same projection, origin, spacing and extent. Similar-looking ID strings alone are insufficient.
- Never show the app's terrain tensor as the terrain of a different similarity query footprint.
- Preserve candidate IDs and coordinates. Missing coordinates produce a labelled unmapped result, not a marker at zero latitude/longitude.
- Each task changes at most three files and adds at most three functions or five test cases. Generated files in `app/public/data/` don't count toward the file limit.

## Verify

- Seam: export the available retrieval files and use the real app's analog page and Earth map.
- Proposed CLI addition:

```powershell
.\.venv\Scripts\python.exe app\scripts\export_data.py --input-dir temp --analogs-dir "temp/<received-retrieval-run>" --output-dir app/public/data
.\.venv\Scripts\python.exe -m unittest discover -s app/scripts/tests -p "test_*.py"
npm --prefix app run build
npm --prefix app run preview
```

- Allow `--analogs-dir` more than once, one per received run. The command is planned, not currently runnable.
- Check an orphan comparison row, a duplicate rank, unavailable coordinates, fewer matches than the declared `top_k`, and two runs with different model identities.
- Compare a real result row and marker with `retrieval.csv`. Check producer-supplied physical values against `physical_comparison.csv`.
- For source 1 without its files, compare each exported row with the saved table in notebook 36.

## Decisions

- Start from notebook 36 and key pages on Aarron's query IDs: see [area decisions](area.md#decisions).
- **Open:** Do the notebook 36 files and the pipeline run share one `retrieval.csv` schema? The pipeline was built from the notebook, but compare the columns before relying on one adapter.
- **Open:** Who runs the remaining site pairs once the three data folders arrive, and on which machine? Gareth's `.venv` has CPU PyTorch. This checkout has no environment.

## My calls

- Export analog metadata per lunar region, keyed by the original query ID. Fetch it when the analog view opens.
- Use a readable route name for a query, such as its row and column. Keep the source ID in the record.
- Put the candidate ID in the pair URL, not the rank. Rank changes when the candidate pool grows.
- Support partial query coverage honestly. A real declared subset can be demonstrated. Unavailable queries stay unavailable.
- Preserve supplied physical-check definitions without recomputing or tuning a new matching score.
- Use Haworth rank 2 from notebook 36 as the demo's misleading match. It is a real result, so the wireframe's sample rank 2 is not needed.

## Tasks

- [ ] Ask Aarron for the notebook 36 report folder with his other files. If it has not arrived when this task starts, transcribe the nine saved rows from the notebook into one source CSV. Record the notebook path, run ID and candidate pool. Verify every row against the notebook.
- [ ] Add retrieval and physical-comparison adaptation with focused rejection checks. Verify original ranks, candidate identities, candidate-pool labels, and orphan-record handling on the notebook 36 rows.
- [ ] Publish analog metadata for the three notebook 36 queries and list them on their region pages. Leave every other query and patch unavailable.
- [ ] Add the analog page with a ranked table, scope labels, physical evidence, and empty/error states. Verify that Haworth rank 2 stays visible with its 0 of 5 checks.
- [ ] Add the Leaflet Earth map with ranked markers and attribution. Verify coordinates, selected-row highlighting, and operation when the basemap is unavailable.
- [ ] Add linked result selection and stable pair links with explicit comparison availability. Verify direct URLs and back navigation.
- [ ] Add the Haworth–Wadi Rum run through the same export, labelled "Wadi Rum only". Check its schema and run identity first (blocked: Aarron's run has not arrived).
- [ ] Compare `patches.csv` footprints (`left`, `bottom`, `right`, `top`, `crs_wkt`) with Hanxi's `center_x`/`center_y` and record which queries match a Hanxi patch exactly. Enable patch links and predictions only for those (blocked: the `terrain_learning_readiness` folder has not arrived).
- [ ] Run the production walkthrough on the published queries. Label unsearched sites and query gaps explicitly.
