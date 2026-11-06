# Environmental EDA ports

These notebooks copy the existing environmental preprocessing and analysis code into Darrel's workspace. **The source notebooks and original project folders are unchanged.**

- Raw inputs: `darrel stuff/data/`.
- Processed tables, rasters, figures and manifests: `darrel stuff/data/processed/` (the lunar support-view gallery uses `darrel stuff/data/reports/`).
- No automatic downloads, data substitutions, OSM analysis or CNN training.
- Earth notebooks now retain verified local execution outputs. Moon notebooks remain unexecuted beyond input preflight because supporting inputs are missing; this is not a claim that Moon EDA is complete.

## Verification status — 6 November 2026

| Check | Result |
| --- | --- |
| Earth 03 — original three sites | **Passed:** 150 source files processed into 150 native monthly exports and 1,800 regional monthly rows. |
| Earth 26 — two added sites | **Passed:** 100 source files processed into 100 native monthly exports and 1,200 regional monthly rows. |
| Earth 27 — five-site EDA | **Passed:** 3,000 monthly rows, five regional coverage records and 50 annual precipitation records checked. Both saved figures were inspected; notebook outputs are retained. |
| Earth output integrity | All 267 output hashes across the three completed runs matched their manifests. A separate two-file pilot tested normal and coastal missingness before the full runs. |
| Moon P1 downloads | **Passed bounded checks:** all 144 table/XML pairs match manifest sizes and XML table layouts; one record per product decoded successfully. All ten illumination maps match receipt sizes and expected lunar CRS/resolution, with readable sample windows. This is not a full 30 GB row-by-row audit or publisher-checksum verification. |
| Moon 05/06/13/25 execution | **Blocked:** the original seven SDEM region inputs, six selected LOLA files and documented unit-policy JSON are missing. Input setup was checked; the full regional processing/EDA was not run. |
| Existing processing tests | Six focused tests passed for Diviner parsing/missingness, packed-value decoding, raster crop/warp and lunar CRS handling. Existing tests were not changed. |

The P1 downloads are complete, but the original regional Moon EDA also needs its supporting inputs. Do not mark that EDA complete or replace missing footprints/units with guesses. Full processing details and selected run paths are recorded in [the verification report](../data/verification/20261105T175111061360Z/verification.json). The report and generated data stay local under the ignored `data/` directory.

## Run order

### Earth

| Notebook | Copied work |
| --- | --- |
| [03 — Climate preprocessing](Earth/03_earth_climate.ipynb) | Original notebook 03: decode the original three sites' 150 NetCDF files and build native monthly tables/regional summaries. |
| [26 — Climate expansion](Earth/26_earth_environment_expansion.ipynb) | Climate block from original notebook 26: the 100 Death Valley/Wadi Rum subsets, with the original boxes and aliases. OSM code is excluded. |
| [27 — Five-site environmental EDA](Earth/27_five_site_environment_eda.ipynb) | Original notebook 27's climate coverage, seasonality, spatial distributions and annual precipitation. This also covers the original notebook 25's Earth climate questions. |

### Moon

| Notebook | Copied work |
| --- | --- |
| [05 — Native environmental preprocessing](Moon/05_lunar_terrain_environment.ipynb) | Original notebook 05: use the seven original SDEM footprints, preserve terrain/quality support, and crop illumination/LOLA fields at native resolution. |
| [06 — Diviner preprocessing](Moon/06_diviner_temperature.ipynb) | Original notebook 06: XML-driven table reading, special values, lunar projection and regional native-cell exports. |
| [13 — Required terrain-support views](Moon/13_build_lunar_terrain_views.ipynb) | Original notebook 13: separate full-context and image-supported views required by the original environmental joint-coverage analysis. Not a new terrain study. |
| [25 — Lunar environmental EDA](Moon/25_environment_native_support_eda.ipynb) | Original notebook 25's illumination statistics, Diviner phase coverage and environmental/terrain co-availability. Earth and OSM sections are excluded. |

The original numerical calculations, masks, native-grid policies, physical units and declared cohorts are preserved. Path/configuration and provenance setup cells are adapted. Each copied code cell records its source notebook, cell index and original source hash in notebook metadata; unchanged analysis cells are marked explicitly.

## To be analysed (Moon data)

This plan is based on the copied Moon code, the downloaded Diviner XML labels and small source-row checks. **These are possible analyses, not completed findings.** “Copied” below means the calculation exists in a ported notebook; “To add” means it is not implemented there yet.

### Current data availability

**Inspection snapshot — 6 November 2026:** all **144 Diviner `.tab` files and 144 XML labels** are present and match their download-manifest sizes, with no partial table remaining. All labels share the same six-field/unit schema, and their declared layouts and a small record sample were checked. The **ten illumination GeoTIFFs** are also present and passed the receipt/header checks described above. These checks confirm file availability and bounded technical readability, not scientific accuracy of every observation.

There are still **no local SDEM/LOLA supporting files**, no processed Moon runs and no restored unit-policy JSON. Source-field checks are possible, but the full regional notebooks still need the [required inputs](#required-inputs). Missing supporting files must not be interpreted as missing lunar observations.

### Fields available for analysis

Diviner `.tab` files are fixed-width tables: the XML label supplies the field positions, units and special values.

| Field | Source / meaning | What it supports |
| --- | --- | --- |
| `clon`, `clat` | Raw native-cell centre longitude and latitude, in degrees. | Map temperatures, identify repeated cell centres and select observations within the original region footprints. |
| `ltim` | Raw lunar local time, in hours; not a calendar timestamp. | Explore temperature versus local time within the phase-composite data, retaining product/region identity. |
| `tbol` | Raw average bolometric brightness temperature, in K. | Temperature distributions, spatial contrasts, phase-bin comparisons and inspection of low-temperature rows. Not instantaneous or mission-time extremes. |
| `x`, `y` | Raw polar stereographic coordinates described as normalized by the mean lunar radius. | Coordinate-consistency investigation only after resolving that encoding. The existing processing does **not** treat them as metre coordinates. |
| `x_m`, `y_m` | Derived by notebook 06 from `clon`/`clat` using the original lunar projection. | Regional cropping and contextual lookup of georeferenced illumination/terrain layers. |
| `valid_temperature` | Derived after masking XML special values; requires finite, positive `tbol`. | Missing-value counts and valid-cell coverage. This is a validity check, **not** a retrieval-quality or uncertainty flag. |
| `seasonal_ls_bin`, `subsolar_longitude_bin` | Derived from the product filename, not extra raw table columns. | Group the original seasonal/solar-phase products. Do not interpret the IDs as chronological observations or assume equal-duration bins. |
| `source_product`; region identity | Product ID added by notebook 06; region comes from the selected SDEM footprint, output folder and summary table. | Trace results to source products and compare consistent regions/cohorts without pooling unrelated cells or bins. |

The inspected labels use `-9998` and `-9999` as special values. The parser masks these before analysis; they must not enter temperature statistics as physical values.

Illumination products are **raster pixel bands plus coordinates**, not Diviner table columns. Their quantities are solar visibility, Earth visibility, permanent-shadow class and sky visibility. Notebook 25 uses three 60 m products (`85S`) plus the 240 m sky-view product (`65S`); the other downloaded resolutions are not extra independent observations. All ten TIFFs have now been checked for readable windows, lunar CRS, grid resolution and packing metadata. They carry scale/offset values but **no embedded band-unit metadata**. The original EDA uses fractions for visibility/shadow summaries and steradians for sky view, so its documented unit policy must still be restored and checked rather than assuming units from filenames.

### Analysis to do

All items below remain pending local execution and input validation.

| Analysis | Fields / data needed | Code status and conditions |
| --- | --- | --- |
| **Coverage and missingness** — Which native cells have temperature data in each phase product? | `clon`, `clat`, `valid_temperature`, `source_product`, phase IDs. | **Copied: 06/25.** Separate missing observations from incomplete downloads. Use the union of observed centres; it cannot count cells absent from every product. |
| **Temperature by region and location** — How do spatial distributions differ? | `tbol`, coordinates and the original seven region footprints. | **Copied: 06/25** for regional statistics and per-bin quantiles. Temperature maps would be **to add**. Keep native support and missingness visible. |
| **Temperature across phase bins** — How do available-cell and fixed-cohort summaries differ? | `tbol`, phase IDs, `source_product`, repeated coordinates. | **Copied: 25.** Full comparison needs the complete collection. The original code checks 144 products and 17 common products; do not replace those cohorts with the currently downloaded subset. |
| **Low-temperature examples** — Where do the lowest valid source rows occur? | `tbol`, coordinates and product identity. | **Copied: 25**, retaining ten low-tail rows per region. These are low values within phase averages, not verified physical minima or safety thresholds. |
| **Temperature versus lunar local time** — What association appears within the composites? | `tbol`, `ltim`, phase IDs, coordinates and region identity. | **To add.** Control spatial/cohort differences and inspect local-time encoding/range first; do not call the result a dated heating/cooling time series. |
| **Illumination and shadow by region** — How do native distributions differ? | Decoded solar/Earth visibility, shadow class and sky-view pixels; region footprints and documented units. | **Copied: 05/25.** Requires the actual GeoTIFFs and unit policy. Preserve separate grids/quantities; means do not provide outage durations or delivered power. |
| **Joint data availability** — Where do thermal, illumination and terrain-support evidence coexist? | Observed Diviner centres, complete-common-product flags, four illumination lookups and the two terrain-support views. | **Copied: 13/25.** Requires all supporting inputs. Co-availability at a centre is not full-footprint coverage or simultaneous environmental conditions. |
| **Temperature versus illumination or terrain** — Are spatial patterns associated? | `tbol` joined to compatible illumination pixels, elevation/slope or support/quality layers. | **To add.** These explanatory associations are not calculated by the current availability checks. Match coordinates, native support and phase/time meaning; do not infer causation or mission suitability. |

**Not supported by the current Diviner columns alone:** calendar-date trends, continuous hot/cold exposure, radiation dose, dust concentration, subsurface temperature/depth, rock abundance, per-row temperature uncertainty or equipment limits. These require other evidence or datasets. `ltim` is not a date, and a mean illumination map cannot supply the longest continuous darkness interval.

## TODO — Moon environmental EDA

**Goal:** understand how the available lunar temperatures vary with local time and environmental context across the seven study regions. Both tasks below are **planned, not implemented or verified results**. Use the existing Moon datasets first; these TODOs do not request another download collection.

### 1. Temperature versus lunar local time

- [ ] **Analyse `tbol` against `ltim`, separated by region and solar-phase group.**

| Item | Details |
| --- | --- |
| Dataset used | Diviner seasonal bolometric-temperature tables and their XML labels in `darrel stuff/data/moon/diviner/seasonal/`. The seven SDEM footprints define the regions. |
| Fields needed | `tbol` (K), `ltim` (hours), `valid_temperature`, `clon`, `clat`, `source_product`, `seasonal_ls_bin` and `subsolar_longitude_bin`; retain region identity from each export folder. |
| Processed input | Notebook 06's `moon/<region>/native_240m/*.csv.gz` files inside a completed local `diviner_temperature` run. These already retain `ltim` and `tbol`; `regional_bin_summary.csv` alone is not sufficient. |
| Main notebook to modify | [25_environment_native_support_eda.ipynb](Moon/25_environment_native_support_eda.ipynb): extend the regional thermal-analysis loop, where `observations` is loaded, **before it is deleted**. Keep the existing coverage and phase-bin analyses. |
| Preprocessing notebook | [06_diviner_temperature.ipynb](Moon/06_diviner_temperature.ipynb): reuse its existing exports. Change it only if source-label checks reveal a genuine encoding/export issue; no new column is currently required. |

Planned steps:
1. Check the XML definition, special values and actual `ltim` distribution/range. Report unusable or missing local times rather than inventing values; retain only valid temperature/local-time pairs for this analysis.
2. Plot temperature against local time by region, with solar-phase groups visible. Treat local time as cyclic: the midnight boundary is not a large time separation.
3. Summarise local-time bins using counts, median temperature and 10th–90th percentiles. Show empty bins and uneven coverage rather than connecting unsupported intervals.
4. Compare the available-cell patterns with a consistent spatial cohort where feasible, so changing observation locations are not mistaken for a local-time effect.

**Planned outputs:** per-region plots and a summary CSV with region, phase group, local-time bin, valid-row count, distinct-cell count and temperature quantiles. These are composite-data associations, **not** a dated heating/cooling curve or measured duration of hot/cold exposure.

### 2. Temperature–illumination or temperature–terrain relationships

- [ ] **Calculate spatial associations between temperature and solar visibility/shadow, elevation or slope.** Start with temperature–solar visibility, then add terrain comparisons using the same matching rules.

| Item | Details |
| --- | --- |
| Temperature dataset | The same Diviner exports from notebook 06, retaining temperature, product/phase identity, local time and native-cell coordinates. |
| Illumination dataset | Existing 2016 maps in `darrel stuff/data/moon/illumination_2016/`. Start with `AVGVISIB_85S_060M_201608.TIF` (solar visibility) and `LPSR_85S_060M_201608.TIF` (permanent-shadow class). Use notebook 05's decoded regional crops and the documented unit policy, not raw packed pixel values. |
| Terrain dataset | The seven SDEM regions in `darrel stuff/data/moon/sdem/regions/`, processed into `elevation_m.tif` and `slope_deg.tif`. Notebook 13 provides separate `full_context` and `image_supported` views; do not pool those views as independent observations. The six LOLA maps remain prerequisites of notebook 05's current pipeline. |
| Main notebook to modify | [25_environment_native_support_eda.ipynb](Moon/25_environment_native_support_eda.ipynb): extend the existing regional thermal/joint-availability loop. Reuse `sample_native`, `illumination_paths`, `centers` and the terrain-view paths. |
| Supporting notebooks | [05_lunar_terrain_environment.ipynb](Moon/05_lunar_terrain_environment.ipynb) supplies decoded native illumination crops; [13_build_lunar_terrain_views.ipynb](Moon/13_build_lunar_terrain_views.ipynb) supplies terrain values and support views. Reuse these outputs rather than changing their grids or masks for a plot. |

Planned steps:
1. Sample each environmental raster's containing native pixel at the Diviner centre (`x_m`, `y_m`), reusing the current no-interpolation lookup. Preserve CRS checks and missing/support flags; this is centre-based context, not a matched 240 m footprint average.
2. Join those sampled values back to temperature observations using region plus native-cell coordinates, keeping product/phase and local time. Preserve the actual sampled elevation/slope values: the current terrain-availability boolean alone cannot measure a relationship.
3. Make temperature–solar-visibility, temperature–elevation and temperature–slope scatter/hexbin plots. Compare temperature distributions for shadow classes separately because shadow is categorical.
4. Report paired counts, missingness and descriptive correlations for continuous variables, separated by region and phase and checking local-time differences. Compare terrain views separately; do not treat repeated products at one cell or nearby pixels as independent evidence for significance.

**Planned outputs:** traceable paired-data tables, relationship plots and grouped summaries/correlations, with dataset, units, cohort and terrain view identified. Modeled illumination averages and Diviner phase averages are not simultaneous measurements; associations do **not** establish causation or base-site suitability.

### Implementation order and completion checks

- Finish support restoration, then run **05 → 06 → 13 → 25** successfully. Downloads alone do not produce the processed inputs.
- Add the two analysis sections to notebook **25**, before its final completion cell. Reuse the completed runs selected by its existing setup and record their provenance.
- Save new tables/figures under the existing analysis `OUT` directory (`darrel stuff/data/processed/analysis/moon_environment_eda/<run>/`), not in the original project folders.
- Extend notebook 25's final required-output checks when implementing the new outputs. Keep both TODO checkboxes open until the new cells execute and their units, joins, counts, missingness and plots have been checked.

## Before running

Use the same processing dependencies as the source notebooks. From the **repository root**, install them into the environment used by your notebook kernel:

```cmd
.venv\Scripts\python.exe -m pip install -r notebooks/requirements-processing.txt
```

The downloader-only environment does not necessarily contain pandas, matplotlib, rasterio, pyproj or the other analysis dependencies. Select the intended environment as the notebook kernel, then run cells in order.

### Required inputs

The Earth preprocessing uses the existing complete 150-file and 100-file download manifests under `data/earth/`, relative to `darrel stuff/`. The version, years, variables, boxes, receipts and hashes are checked as in the original processing.

Moon processing requires more than the P1 downloader's temperature/illumination products, because the original EDA also depends on the following supporting inputs:

- All **144 Diviner table/XML pairs** under `darrel stuff/data/moon/diviner/seasonal/`. A `.part` file is not a completed table. The original `FILE_LIMIT` pilot option remains; pilot outputs are not valid full inputs for notebook 25.
- All **ten illumination GeoTIFFs** under `darrel stuff/data/moon/illumination_2016/`.
- The **same seven SDEM region folders**, including their original elevation, image-count masks, quality layers and README files, under `darrel stuff/data/moon/sdem/regions/`. These establish the original region footprints; no alternate bounds are invented.
- The **six exact LOLA files** listed in notebook 05 under `darrel stuff/data/moon/lola_product90/large_area_dem/`.
- For notebook 25, restore the original documented unit policy to `darrel stuff/data/reference/environment-readiness-20261028/native_layer_units.json`. Its absence is an error, not permission to assume units.

The required supporting source files and unit policy are not silently downloaded, generated or replaced. Use the same original inputs to reproduce the original analysis. Historical product-selection equivalence does not establish byte-for-byte identity without the original archived checksums.

## Local processing and provenance

`environment_workflow.py` is a small **file/run-management helper**, not a dataset, model or scientific analysis. The notebooks still contain the actual processing and EDA calculations.

- **`LocalRun`:** reuses the original `Run` implementation but directs new runs to `darrel stuff/data/processed/`. It records input/output hashes, settings and completion/failure status. Original source files remain read-only.
- **`latest_completed_run`:** locates an explicitly pinned run or the latest completed local run for the required processing stage. It does not substitute partial runs or data from the original project folders.
- **`select_climate_manifest`:** selects a completed download manifest matching the original regions, bounding boxes, years and variables.

The data flow is: **downloaded source files → preprocessing notebooks → versioned processed runs → EDA notebooks → figures/tables and provenance**. This keeps repeated analyses traceable without changing the original shared code.

EDA setup defaults to the **latest completed local run** for each required stage. Set the explicit `*_RUN_ID` variables to pin runs. The selected paths and hashes are recorded; original-project data and partial/failed runs are not substituted. A missing input raises an error rather than producing made-up or silently reduced results.

For the EDA notebooks, run the final completion cell only after all preceding cells succeed. A stopped/failed analysis remains marked as running/incomplete. No saved historical plots are presented as results from the newly downloaded data.

Opening these notebooks does not process data. In particular, the complete Diviner preprocessing reads approximately **30.74 GB**; inspect a pilot only after its required labels and region files are available. Missing Moon dependencies do not prevent you from working through the Earth notebooks independently.
