# Browse Earth terrain analogs

Needs: browse-regions
Due: 2026-11-15

## Goal

Inspect each lunar patch's ranked Earth matches, physical agreement, and geographic location.
The app reads the integrated pipeline export. See [shared context](area.md#shared-context).

## Data sources

- `integration.run_all` produces `moon_tiles.csv`, `earth_matches.csv`, `physical_comparison.csv`, and provenance.
- Every exported patch has a shared `tile_id`, a Hanxi source ID, and its matching similarity source ID.
- All 2,910 tiles have 15 matches: top three from each of five Earth sites.
- `app/scripts/export_data.py` writes `analogs/<region>.json`, `earth/candidates.json`, and the referenced grid files.
- Notebook 36 was an earlier fallback. No notebook transcription or single-site-only bundle is used by the current app.

## Done when

- Every published match retains the pipeline run, tile identity, similarity query, candidate pool, ranks, and physical checks.
- A selected terrain patch opens its analog page at `#/region/<region>/patch/<patch>/analogs`.
- Source footprints are joined through the shared tile identity. Similar-looking IDs never substitute for that join.
- Each list shows all 15 matches, with overall and per-site rank, region, cosine, coordinates, and physical-check counts.
- Cosine stays a similarity measure. Weak physical matches remain visible and scores are not presented as safety ratings.
- A Leaflet Earth map uses supplied latitude/longitude, numbered markers, visible attribution, and a result-list fallback.
- Row and marker interaction share the selected result. Pair links use candidate IDs, not unstable ranks.
- The page identifies all five searched sites and makes unavailable data explicit. It never invents matches.
- A production walkthrough checks a real patch, a weak match, unavailable data, copied URLs, and browser navigation.

## Out of scope

- Live inference, retraining, reranking, uploads, and editing the pipeline teammates' model code.
- Earth readiness scoring and the detailed pair charts supplied by `compare-terrain`.

## Constraints

- Read one integrated run. Its model, dataset, orientation cache, and scope define the comparison.
- Preserve `overall_rank` and `site_rank`. Do not merge unrelated runs or create a new score.
- The exporter validates each match against the tile's similarity query and its physical records.
- Missing coordinates produce a labelled unmapped result, not a marker at zero latitude/longitude.
- Keep source IDs in data even when readable slugs are used in routes.
- Each source task changes at most three files and adds at most three functions or five tests. Generated app data is excluded.

## Verify

- Seam: export a completed integrated run and inspect the actual analog page and Earth map.

```powershell
.\.venv\Scripts\python.exe app\scripts\export_data.py --pipeline-run data/processed/moon_pipeline/<run> --output-dir app/public/data
.\.venv\Scripts\python.exe -m unittest discover -s app/scripts/tests -p "test_*.py"
npm --prefix app run build
npm --prefix app run preview
```

- Replace `<run>` with an available completed bundle. There is no `--input-dir` or `--analogs-dir` interface now.
- Check ranks, missing physical records, candidate identity, query joins, and declared match counts against the source data.
- Run `npm --prefix app run check:browser` for tile-failure and keyboard row/marker checks. The latest evidence is recorded under Verification, 2026-11-15.

## Decisions

- The initial notebook-first and independent-query plans were replaced by the integrated tile join in `3b5937e`.
- Pair URLs retain Earth candidate IDs. Numeric candidate-index URLs are also accepted for compatibility.
- No new candidate-pool or model-policy decision is made by this records update.

## My calls

- Fetch analog metadata per region when the analog view opens.
- Keep real poor matches visible. The Haworth `r32-c32` example below belongs to the current grid, not notebook 36's query.
- Preserve prior superseded task descriptions as history. They are not work still to perform.

## Tasks


- Superseded, 14 Nov: the export reads the integrated pipeline run (`3b5937e`), not notebook 36. Original task: ~~Ask Aarron for the notebook 36 report folder with his other files. If it has not arrived when this task starts, transcribe the nine saved rows from the notebook into one source CSV. Record the notebook path, run ID and candidate pool. Verify every row against the notebook.~~
- [x] Add retrieval and physical-comparison adaptation with focused rejection checks. Verify original ranks, candidate identities, candidate-pool labels, and orphan-record handling on the notebook 36 rows. Note, 14 Nov: built on the pipeline run, not the notebook 36 rows. `app/scripts/tests/test_export_data.py` covers ranks, candidates and missing checks.
- Superseded, 14 Nov: all seven regions publish analogs for every patch (`3b5937e`), not three notebook 36 queries. Original task: ~~Publish analog metadata for the three notebook 36 queries and list them on their region pages. Leave every other query and patch unavailable.~~
- [x] Add the analog page with a ranked table, scope labels, physical evidence, and empty/error states. Verify that Haworth rank 2 stays visible with its 0 of 5 checks. Note, 14 Nov: checked on the production preview with Haworth patch `r32-c32`. Its rank 2 match (Wadi Rum, cosine 0.944) shows 0 of 5 checks.
- [x] Add the Leaflet Earth map with ranked markers and attribution. Verify coordinates, selected-row highlighting, and operation when the basemap is unavailable. Note, 14 Nov: markers, coordinates and attribution seen on the preview. The tile-failure fallback is in `EarthMap.tsx` but was not exercised. Row highlighting was added by the following task. Keyboard linking and tile-failure behaviour still need an explicit walkthrough.
- [x] Add linked result selection and stable pair links with explicit comparison availability. Verify direct URLs and back navigation. Note, 14 Nov: checked on the preview. Hovering a row marks its map marker, and hovering a marker marks its row. A pair link opens, and Back returns to the analog list. Keyboard focus on a row was not confirmed.
- Superseded, 14 Nov: every patch is searched against all five Earth sites, so no Wadi Rum-only run is published. Original task: ~~Add the Haworth–Wadi Rum run through the same export, labelled "Wadi Rum only". Check its schema and run identity first~~
- Superseded, 14 Nov: `integration/` joins the two pipelines on a shared `tile_id`, and the export rejects a match whose query is not the tile's similarity patch. Original task: ~~Compare `patches.csv` footprints (`left`, `bottom`, `right`, `top`, `crs_wkt`) with Hanxi's `center_x`/`center_y` and record which queries match a Hanxi patch exactly. Enable patch links and predictions only for those~~
- [x] Run the production walkthrough on the published queries. Label unsearched sites and query gaps explicitly. Note, 14 Nov: ran on the preview for Haworth patch `r32-c32`. The page names the pool as all five Earth sites. Every published patch has matches, so the no-matches state was not seen.


## Results

Historical verification, 2026-11-14, against the integrated exporter and page code.
All 27 app-script tests and the production build pass in this checkout.
The browser notes above are prior checks. Tile-failure and keyboard-focus linking were not rerun on 14 Nov. They passed the 15 Nov check below.
Final acceptance and `Status: done` remain for review.

### Verification, 2026-11-15

Checked `8769b86` plus the local interaction fixes with `npm --prefix app run check:browser`.
The browser check verifies all 15 matches, failed Earth tiles, and keyboard linking in both directions. Marker focus now highlights the matching row. All 43,650 exported matches have valid candidates, ranks, and five checks.
Automated accessibility and page-overflow checks pass at 1440 px and 375 px.
The production build and all 29 app-script tests pass. These results replace earlier pending local checks above.
Final feature acceptance remains for review.
