# Environmental EDA ports

These notebooks copy the existing environmental preprocessing and analysis code into Darrel's workspace. **The source notebooks and original project folders are unchanged.**

- Raw inputs: `darrel stuff/data/`.
- Processed tables, rasters, figures and manifests: `darrel stuff/data/processed/` (the lunar support-view gallery uses `darrel stuff/data/reports/`).
- No automatic downloads, data substitutions, OSM analysis or CNN training.
- Notebooks are provided **without execution outputs**. This port does not claim processing or EDA is complete.

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

**Inspection snapshot — 5 November 2026:** 20 Diviner `.tab` files match their download-manifest sizes, with 20 XML labels and one `.part` transfer. All 20 completed tables are in the filename's `ls030` group, so they do not represent the full phase collection. The downloaded labels share the same six-field schema. Counts will change as downloading continues; matching file size alone does not validate the science.

There are currently **no illumination GeoTIFFs**, no local SDEM/LOLA supporting files, no processed Moon runs and no restored unit-policy JSON. Source-field checks can begin on completed files, but the full regional notebooks still need the [required inputs](#required-inputs). Do not count a `.part` file as data or interpret missing downloads as missing lunar observations.

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

Illumination products are **raster pixel bands plus coordinates**, not Diviner table columns. Their planned quantities are solar visibility, Earth visibility, permanent-shadow class and sky visibility. Notebook 25 uses three 60 m products (`85S`) plus the 240 m sky-view product (`65S`); the other downloaded resolutions are not extra independent observations. Actual TIFF metadata has not been checked locally because the files are absent. The original EDA uses fractions for visibility/shadow summaries and steradians for sky view, but the documented unit policy must be restored and checked rather than assuming units from filenames.

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

`environment_workflow.py` reuses the original `Run` implementation with a local output root and notebook path. It retains source hashes, output hashes and completion/failure records without changing the original shared code.

EDA setup defaults to the **latest completed local run** for each required stage. Set the explicit `*_RUN_ID` variables to pin runs. The selected paths and hashes are recorded; original-project data and partial/failed runs are not substituted. A missing input raises an error rather than producing made-up or silently reduced results.

For the EDA notebooks, run the final completion cell only after all preceding cells succeed. A stopped/failed analysis remains marked as running/incomplete. No saved historical plots are presented as results from the newly downloaded data.

Opening these notebooks does not process data. In particular, the complete Diviner preprocessing reads approximately **30.74 GB**; inspect a pilot only after its required labels and region files are available. Missing Moon dependencies do not prevent you from working through the Earth notebooks independently.
