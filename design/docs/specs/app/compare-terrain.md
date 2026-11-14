# Compare lunar and Earth terrain

Needs: earth-analogs
Due: 2026-11-15

## Goal

Inspect why one returned Earth patch is a useful or weak terrain analog for the selected lunar query.
Show the actual grids, five physical checks, and terrain distributions beside the similarity score. See [shared context](area.md#shared-context).

The page has two modes. **Figure mode** shows the pipeline's own PNG figures and works with notebook 36 alone. **Grid mode** draws numeric grids and needs the `terrain_learning_readiness` folder. Build figure mode first.

## Done when

- A pair URL resolves to one verified lunar query and one Earth candidate from the selected retrieval result.
- Figure mode: the page shows that pair's source figure (`example_<n>_rank_<r>.png`) and its distribution figure, each labelled as a static figure from the named run. It offers no hover readout or crosshair.
- Figure mode still shows the cosine score, the supplied physical values and differences, and the check count beside the figure.
- Grid mode: both sides use the source terrain grids belonging to that retrieval run, with 32-by-32 cells and the stated 960 m extent.
- Grid mode: four canvases show lunar slope, Earth slope, lunar relative elevation, and Earth relative elevation. Slope panels share a degree scale. Elevation panels share a separate metre scale.
- Heights remain in physical units. Display scaling never stretches one patch independently to make the terrain look more alike.
- A linked crosshair and labelled readout show the same raster row and column in both patches, with values and units. This is a normalized raster comparison, not spatial co-location.
- The five checks show source Moon/Earth values, differences, comparison bands, units, and in-band flags. They do not alter retrieval ranking.
- Slope and relative-elevation cumulative distribution curves use the actual pair grids, have labelled axes, and agree with known source summaries.
- The page keeps model limitations visible, labels the grids' original orientation, and shows Earth simulation readiness as not computed.
- A pair with no grids uses figure mode. A pair with no grids and no figure shows explicit unavailable sections. Neither mode falls back to another candidate's data or unrelated lunar tensors.
- A production browser walkthrough checks a real pair, a misleading high-score match when available, copied links, shared scales, and missing pair data.

## Out of scope

- New similarity scoring, changing physical tolerances, automatic terrain alignment, rescaling heights, or deriving a readiness score.
- Claims that corresponding screen cells are matching geographic points or predicted rover routes.

## Constraints

- Reuse the existing terrain canvas and binary decoder where their declared format matches the pair grids.
- Grid mode requires source-identifiable Earth and lunar grids from the retrieval run's dataset. PNGs cannot supply numeric readouts or distribution curves, so figure mode shows neither.
- Do not read values off a figure. In figure mode, every number on the page comes from a CSV or the notebook's saved table.
- Take both sides of a pair from the similarity dataset (`terrain_learning_readiness`), whose tensors hold relative elevation and slope for Moon and Earth patches. Do not mix in Hanxi's tensor for the Moon side.
- Keep slope and elevation scales separate because their units differ. Preserve raw physical values alongside quantized display values where comparisons require them.
- Account for the model's rotation/reflection averaging in the explanation. Displayed rasters retain their source orientation unless a documented transform is supplied.
- Explain checks as exploratory physical comparisons, not engineering safety limits. Keep the original source rank.
- Each task changes at most three files and adds at most three functions or five test cases.

## Verify

- Seam: export source-identifiable pair grids and inspect the actual comparison route in the browser.
- Add pair-grid support to the analog export interface established by `earth-analogs`. Document its received input contract before running it.
- Reuse the exporter unit-check command and `npm --prefix app run build` / `npm --prefix app run preview` from the preceding specs.
- Verify one cell and the min/max range on each side, separate shared scale domains, CDF endpoints and monotonicity, original rank, and all five supplied check records.
- Reopen the pair URL after a build and confirm missing grids leave the results list usable.

## Decisions

- **Draw the distribution curves in plain SVG, with no chart library.** Two step lines per chart do not justify a dependency in the bundle. The browser computes them from the 1,024 cells of each published grid, so no data re-export was needed. Cost: axes and ticks are hand-written, and the curves are not computed in the export, which "My calls" planned. (2026-11-14)
- **Figure mode first.** The pair page then ships with data that exists today. Grid mode waited on a folder that has not arrived. Cost: no shared colour scale control, hover readout or crosshair until grid mode lands. (2026-11-13)
- **Open:** Gareth asked Aarron for the `terrain_learning_readiness` folder on 13 Nov. It should hold the tensors for both bodies. Verify its channel order, units and patch IDs before grid mode uses it.
- **Open:** Notebook 36's figures are saved inside the notebook in Git. The PNG files are on Aarron's machine. Ask for the report folder. Extract the embedded images only if it does not arrive.

## My calls

- Compute empirical distributions during offline export, retaining the original units and sample count. The browser only renders the supplied curves.
- Use one slope colour domain across the slope pair and one elevation domain across the elevation pair.
- Include an accessible measurement table even when interactive charts or canvases are unavailable.

## Tasks

- [x] Add the stable comparison route with pair loading, mode selection, and unavailable states. Verify it cannot substitute another candidate or a mismatched lunar tensor. Note, 14 Nov: the route has no mode selection, because only grid mode exists. An unknown candidate ID shows "This comparison is unavailable" on the preview.
- Superseded, 14 Nov: the pair page draws real grids, so no notebook figures are published. Original task: ~~Publish the notebook 36 pair and distribution figures with their run identity, and render figure mode with the score, supplied physical values, and check count. Verify the Haworth rank 2 pair against the notebook.~~
- [x] Adopt a verified pair-grid input contract and export one actual pair with units, source identity, shape, and curve points. Note, 14 Nov: Earth and Moon grids are exported for every published match (`earth/grids.bin`). No curve points are exported.
- [x] Render the four source grids using two shared physical scales and linked readouts. Verify known cells, orientation, units, and labelled limits.
- [x] Render the five supplied physical checks with accessible statuses, differences, and comparison bands. Verify the source rank stays unchanged.
- [x] Choose and record a chart library, then render slope and elevation distributions from real exported curves. Verify axes, sample counts, monotonicity, and accessible tabular values. Note, 14 Nov: no library. `DistributionChart.tsx` draws the curves in SVG from the pair's grids in the browser. On the preview, the Haworth `r32-c32` and Wadi Rum rank 2 pair gave median slopes 15.8 and 12.5 degrees and 90% slopes 18.4 and 26.7 degrees. The pipeline's checks say 15.83, 12.48, 18.40 and 26.65. Both curves rise only, end at 100%, and count 1,024 cells each.
- [x] Add the Earth readiness placeholder and pair-specific limitations. Run the real pair comparison walkthrough and production build in figure mode, then again when grid mode lands. Note, 14 Nov: there is no figure mode. The walkthrough ran once, in grid mode, on the production preview.
