# Compare lunar and Earth terrain

Needs: earth-analogs
Due: 2026-11-15

## Goal

Explain one Earth match using actual terrain grids, five physical checks, and distribution charts.
The current page uses numeric grids only. See [shared context](area.md#shared-context).

## Done when

- A pair URL resolves to one verified lunar patch and a candidate from that patch's match list.
- Four 32-by-32 canvases show slope and relative elevation over the stated 960 m extent.
- The slope pair shares a degree scale. The elevation pair shares a separate metre scale.
- Values retain physical units. Independent height stretching never makes a pair appear more similar.
- One crosshair shows corresponding raster cells across the four panels. It does not claim geographic co-location.
- Five physical checks retain source values, differences, tolerance bands, and in-band flags without changing the rank.
- Labels distinguish similarity relief, p95 minus p5, from terrain-page relief, maximum minus minimum.
- Plain SVG charts display cumulative slope and elevation distributions from each published grid, with units and sample counts.
- Missing grids show an unavailable state while physical checks remain accessible. No other candidate's terrain is substituted.
- The page preserves original raster orientation and explains model limitations and uncomputed Earth readiness.
- A production walkthrough verifies a real pair, shared scales, poor matches, copied links, and missing data.

## Out of scope

- Figure-only mode, notebook image extraction, new scoring, changed physical tolerances, automatic alignment, and independent height rescaling.
- Claims that crosshair positions represent the same geographic point or a predicted rover route.

## Constraints

- The lunar grid comes from the selected Hanxi patch. Earth grids come from the similarity dataset named by the integrated run.
- The shared tile join validates query identity. Earlier integration checks recorded lunar-grid agreement between the two datasets.
- The exporter must retain those identities. A nearby tensor or an ID rename cannot replace a verified query.
- Compute the charts from the published numeric grids in the browser. No curve export or chart dependency is required.
- Preserve the model's rotation/reflection caveat. Displayed grids are not automatically aligned or rotated to north.
- Each task changes at most three source files and adds at most three functions or five test cases.

## Verify

- Seam: open a real pair from the analog list and inspect its grids, checks, and distribution charts.
- Use the integrated `--pipeline-run` export interface documented in `earth-analogs`.
- Run the app-script tests, `npm --prefix app run build`, and `npm --prefix app run preview`.
- Check known cells, separate shared scales, monotonic distributions ending at 100%, 1,024 cells per curve, and all five source checks.
- Verify direct candidate-ID and numeric-index URLs. Missing grid data must leave the match and physical evidence usable.

## Decisions

- **Draw the distribution curves in plain SVG, with no chart library.** Two step lines per chart do not justify a dependency in the bundle. The browser computes them from the 1,024 cells of each published grid, so no data re-export was needed. Cost: axes and ticks are hand-written, and the curves are not computed in the export, which "My calls" planned. (2026-11-14)
- **Figure mode first.** The pair page then ships with data that exists today. Grid mode waited on a folder that has not arrived. Cost: no shared colour scale control, hover readout or crosshair until grid mode lands. (2026-11-13) (replaced 2026-11-14)
- **Use the integrated numeric grids, with no figure fallback.** Both datasets arrived and the app exports the required grids. (2026-11-14)
- The proposed offline curve export is replaced by the SVG component's browser calculation described above.

## My calls

- Use one slope domain and one elevation domain across the corresponding pair.
- Retain accessible measurement tables and explicit unavailable states.
- Keep the original completed tasks and their notes below. Mentions of figure mode describe the superseded plan.

## Tasks


- [x] Add the stable comparison route with pair loading, mode selection, and unavailable states. Verify it cannot substitute another candidate or a mismatched lunar tensor. Note, 14 Nov: the route has no mode selection, because only grid mode exists. An unknown candidate ID shows "This comparison is unavailable" on the preview.
- Superseded, 14 Nov: the pair page draws real grids, so no notebook figures are published. Original task: ~~Publish the notebook 36 pair and distribution figures with their run identity, and render figure mode with the score, supplied physical values, and check count. Verify the Haworth rank 2 pair against the notebook.~~
- [x] Adopt a verified pair-grid input contract and export one actual pair with units, source identity, shape, and curve points. Note, 14 Nov: Earth and Moon grids are exported for every published match (`earth/grids.bin`). No curve points are exported.
- [x] Render the four source grids using two shared physical scales and linked readouts. Verify known cells, orientation, units, and labelled limits.
- [x] Render the five supplied physical checks with accessible statuses, differences, and comparison bands. Verify the source rank stays unchanged.
- [x] Choose and record a chart library, then render slope and elevation distributions from real exported curves. Verify axes, sample counts, monotonicity, and accessible tabular values. Note, 14 Nov: no library. `DistributionChart.tsx` draws the curves in SVG from the pair's grids in the browser. On the preview, the Haworth `r32-c32` and Wadi Rum rank 2 pair gave median slopes 15.8 and 12.5 degrees and 90% slopes 18.4 and 26.7 degrees. The pipeline's checks say 15.83, 12.48, 18.40 and 26.65. Both curves rise only, end at 100%, and count 1,024 cells each.
- [x] Add the Earth readiness placeholder and pair-specific limitations. Run the real pair comparison walkthrough and production build in figure mode, then again when grid mode lands. Note, 14 Nov: there is no figure mode. The walkthrough ran once, in grid mode, on the production preview.


## Results

Current code uses `PairPage.tsx`, `TerrainCanvas.tsx`, and `DistributionChart.tsx` with no chart-library dependency.
On 2026-11-14 the app-script tests and production build pass in this checkout.
Numerical browser observations remain in the task notes. No fresh crosshair or chart walkthrough was performed on 14 Nov. The 15 Nov check below covers both.
Final acceptance and `Status: done` remain for review.

### Verification, 2026-11-15

Checked `8769b86` plus the local interaction fixes with `npm --prefix app run check:browser`.
The browser check verifies the shared cursor on all four grids, equal pair scales, both distribution charts, and the five-check table toggle. Checks remain readable when a terrain binary is truncated.
Automated accessibility and page-overflow checks pass at 1440 px and 375 px.
The production build and all 29 app-script tests pass. These results replace earlier pending local checks above.
Final feature acceptance remains for review.
