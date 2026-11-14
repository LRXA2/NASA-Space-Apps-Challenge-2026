# Browse prepared terrain regions

Needs: browse-first-patch
Due: 2026-11-15

## Goal

Choose any of the seven prepared lunar terrain regions and inspect its patches through a map and direct links.
Expand the first working flow without adding environment or similarity results. See [shared context](area.md#shared-context).

## Done when

- The catalogue lists seven terrain regions and 2,910 patches with source-derived names and counts.
- Every exported patch has a unique source ID and a valid terrain offset. Counts are Leibnitz 225, Malapert 400, Haworth 841, and 361 in each other region.
- A Leaflet `CRS.Simple` map places each 960 m patch correctly using the selected region's grid. Gaps remain gaps.
- Map squares and a selectable patch list open the same patch URL. The list offers a keyboard-accessible alternative to map selection.
- Rover and walking colour modes retain text or pattern distinctions. Hover and selection show the corresponding classes.
- Selecting a region loads only that region's patch metadata and terrain binary. Changing regions does not retain stale selections or canvases.
- A real-data walkthrough opens patches in each region, checks map orientation against row/column positions, and reopens copied links after a production build.

## Out of scope

- Ten environment-only regions, environment ranking, Earth analogs, global lunar imagery, and arbitrary lunar locations.
- A best-analog colour mode until real analog data exists.

## Constraints

- Reuse the first feature's exporter, schema, decoder, status labels, and canvases. Do not create a second terrain format.
- Use the complete pinned inference run. Derive counts and ordering from records, not placeholder wireframe counts.
- Use one documented coordinate convention. In grid-cell units, each rectangle is 32 cells wide and high. Row growth must map downwards.
- Do not put lunar projected metres onto an Earth latitude/longitude basemap.
- Each task changes at most three files and adds at most three functions or five test cases. Generated files in `app/public/data/` don't count toward the file limit. Export to a temporary directory and review it before replacing published data.
- Reuse the implemented region and patch filters. Do not regenerate app data without the bundle and source datasets it references.

## Verify

- Seam: export and open each actual region in the running app, using both the map and the selectable list.
- The existing exporter selects a completed bundle with `--pipeline-run`. Omit `--patch-id` for a whole region, or both filters for all regions.

```powershell
.\.venv\Scripts\python.exe app\scripts\export_data.py --pipeline-run data/processed/moon_pipeline/<run> --region leibnitz-beta-plateau --output-dir app/public/data
.\.venv\Scripts\python.exe -m unittest discover -s app/scripts/tests -p "test_*.py"
npm --prefix app run build
npm --prefix app run preview
```

- Compare exported IDs, counts, and tensor references with the CSV for each region. No extra test patches may be inserted.
- Check network requests when switching regions, an unexported region, keyboard selection, and mobile-width navigation.

## Results

Checked 2026-11-13 on `gareth/app`, on top of `6fdc8f8`, on this macOS checkout. Committed afterwards as `7ae9ae8` and `306e3fe`. The browser checks ran on the production preview (`npm --prefix app run preview`), build `index-DYl3hwOX.js`.

- Historical data check (now located at `design/docs/goals/browse-regions-check.py`): `python3 docs/goals/browse-regions-check.py` printed `DATA CHECK: PASS (7 regions, 2910 patches)`. It compares every patch ID, grid position, tensor reference, class and cell with the source CSV and tensors. The largest cell error is 0.05.
- Counts: Leibnitz 225, Malapert 400, de Gerlache–Kocher 361, Haworth 841, Faustini Rim A 361, de Gerlache Rim 2 361, Connecting Ridge Extension 361.
- Exporter tests: 10 pass. Build: `npm --prefix app run build` passes.
- In each of the seven regions, the map draws one square per patch, and the square count equals the list link count.
- In each region, a click on a map square opened the same URL as that patch's list link. That URL, opened in a new tab, showed the same source patch ID.
- A fresh load of a region page requested only `regions.json` and that region's patch file. The grid file loads on the patch page only.
- Orientation, all regions: the smallest row is drawn at the top and the smallest column at the left. Haworth: row 32 at y=154, row 928 at y=602, column 32 at x=62, column 928 at x=510.
- Class modes: the map key names each class in text with its patch count, and each class has its own pattern. Haworth rover: 528 operable, 181 marginal, 132 non-operable. Haworth on foot: 204 easy, 350 caution, 287 unsuitable.
- Hover on a square, or keyboard focus on a list link, shows the row, column and both classes, and outlines the square.
- Keyboard only: 13 Tab presses reach the first list link, and Enter opens the patch.
- Changing region leaves no old squares, outline or canvases. The colour mode is kept.
- An unknown region shows "This region is unavailable" with a link to the region list.
- Phone width (375 px): the page does not scroll sideways. The first run found the patch table 421 px wide. The table cells are now tighter below 520 px.
- Haworth: 841 squares were in place 460 ms after the link was followed. The pane was not in front, so treat the time as approximate.

Not done or not checked:

- This original browser check did not verify Gareth's Windows setup. Later Windows pipeline observations are recorded in `docs/architecture.md`.
- No region has a missing patch, so "gaps remain gaps" follows from the code only: the map draws only patches in the data.
- Pan and zoom smoothness for Haworth was not measured, only the first draw.
- The map task changed more than three files: `package.json`, `package-lock.json`, `PatchMap.tsx`, `RegionPage.tsx`, `StatusBadge.tsx`, `app.css` and `README.md`.
- This initial terrain-only export was about 15 MB. Schema v2 adds analogs and Earth grids, bringing committed app data to about 31 MB.

## Decisions

- Keep data integration and screens in the same feature: see [area decisions](area.md#decisions).

## My calls

- Use a region list for the initial catalogue. A decorative south-pole overview is not required for browsing to work.
- Expose no invented featured-patch labels. Use deterministic source order until the team chooses examples.
- Publish all seven regions from one exporter run. One run writes every region, so per-region tasks would repeat the same work seven times.

## Tasks

- [x] Add region switching and a selectable Leaflet patch grid using the existing metadata contract. Verify selection, class modes, keyboard fallback, and lazy loading with the first region.
- [x] Publish all seven regions (2,910 patches) from one exporter run: patch metadata, grid binaries, and catalogue entries. Verify per-region counts, unique source IDs, binary offsets, and one cell value per region against its source tensor.
- [x] Run the seven-region production walkthrough. Verify map orientation, gaps, map responsiveness for Haworth's 841 patches, independent region navigation, and copied patch links in each region.

Current record review, 2026-11-14: the catalogue retains seven regions and 2,910 patches.
The region table now pages at 50 rows. Historical checks above predate that pagination.
The current production build passes. No new map or keyboard walkthrough was run.
Final acceptance and `Status: done` remain for review.

### Verification, 2026-11-15

Checked `8769b86` plus the local interaction fixes with `npm --prefix app run check:browser`.
The browser check verifies Haworth pagination, patch navigation, and narrow-screen layout. Its data audit checks all 2,910 unique tiles and binary offsets.
Automated accessibility and page-overflow checks pass at 1440 px and 375 px.
The production build and all 29 app-script tests pass. These results replace earlier pending local checks above.
Final feature acceptance remains for review.
