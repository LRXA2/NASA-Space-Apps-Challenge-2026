# Lunar and Earth download scripts

These scripts inventory and download lunar and Earth source files. They do not crop regions, align rasters, convert Diviner tables, or calculate terrain features.

All commands below run in **PowerShell from the project root** (the folder containing `outline.md` and `download scripts`). Quote script paths because the folder name contains a space.

## Setup

Use Python 3.10 or newer. Create a virtual environment if you do not already have a working one:

```powershell
py -3 -m venv .venv
```

Install the two direct dependencies into that environment:

```powershell
.\.venv\Scripts\python.exe -m pip install requests beautifulsoup4
```

The examples invoke the environment's Python directly; activation is unnecessary. If an existing `.venv` reports `No Python at ...`, it points to a missing Python installation and needs to be recreated using an installed interpreter.

## Start with an inventory

Without `--download`, scripts contact the source websites and write local manifests, but do not transfer the dataset files. Inventory mode still requires internet access and may send file-size requests.

Use separate output directories so the scripts do not overwrite each other's manifests:

```powershell
.\.venv\Scripts\python.exe "download scripts/download_lola_product90.py" --output "data/raw/moon/lola_product90"
.\.venv\Scripts\python.exe "download scripts/download_diviner_south_polar.py" --output "data/raw/moon/diviner"
.\.venv\Scripts\python.exe "download scripts/download_lunar_illumination_2016.py" --output "data/raw/moon/illumination_2016"
```

Inspect the manifests and size estimates, then rerun the desired command with `--download` and any selection flags below. Relative output paths resolve from your terminal's current directory, not from the script's directory. Absolute paths such as `--output "D:/NASA/Moon/Diviner"` also work.

## LOLA Product 90: terrain and related layers

Script: [download_lola_product90.py](download_lola_product90.py). Source: [NASA PGDA Product 90](https://pgda.gsfc.nasa.gov/products/90).

Discovers supported links under the source's `/data/LOLA_20mpp/` path. Files are grouped into `large_area_dem`, `roughness`, `permanent_shadow`, `nac_images`, `point_clouds`, and `other`, using their filenames.

| Flag | Default | Behavior |
| --- | --- | --- |
| `-h`, `--help` | — | Print help and exit. |
| `--output PATH` | `NASA_LOLA_Product_90` | Directory for the inventory and downloads. |
| `--download` | Off | Transfer selected files. Without filters, selects all discovered files. |
| `--exclude-pointclouds` | Off | Exclude `.XYZI` point clouds. |
| `--match REGEX` | No filter | Case-insensitive regular expression searched against filenames. |
| `--limit N` | `0` | Select the first N matching files; `0` means unlimited. Negative values are rejected. |

Selection order: exclude point clouds, apply filename regex, then apply the limit. Files are ordered by category and filename. A limit counts files, not regions or complete sets of related layers.

**The manifest and printed inventory totals include all discovered files even when filters are supplied.** They are not a preview of just the filtered download. The script prints the selected count when downloading.

Download everything except the large point clouds:

```powershell
.\.venv\Scripts\python.exe "download scripts/download_lola_product90.py" --output "data/raw/moon/lola_product90" --exclude-pointclouds --download
```

Download only files whose names begin with `LPSR_` and end in `.tif`:

```powershell
.\.venv\Scripts\python.exe "download scripts/download_lola_product90.py" --output "data/raw/moon/lola_product90" --match '^LPSR_.*\.tif$' --download
```

For a transfer check, add `--limit 1` to a filtered command. This limits the number of files, not the size of the first file. Use actual filenames from the manifest to construct more specific filters.

Outputs:

- `download_manifest.csv`: filenames, categories, advertised sizes, estimated bytes, and URLs.
- `source_page_snapshot.html`: source catalog snapshot.
- `<category>/<filename>`: downloaded files.
- `failed_downloads.csv`: written if transfers fail.

The script does not check available disk space. Its source-size estimates are approximate, and some files may have no listed size. Point clouds are included unless explicitly excluded.

## Diviner: south-polar temperature products

Script: [download_diviner_south_polar.py](download_diviner_south_polar.py). Source: [NASA PDS Diviner derived PCP archive](https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_pcp/).

Downloads `.tab` data tables and `.xml`/`.lbl` metadata from three south-polar collections. These are source tables, not ready-to-use GeoTIFFs. Consult the accompanying labels before interpreting their fields and units.

| Flag | Default | Behavior |
| --- | --- | --- |
| `-h`, `--help` | — | Print help and exit. |
| `--output PATH` | `data/raw/moon/diviner` | Directory for the inventory and downloads. |
| `--collections NAME [NAME ...]` | All three | Choose `seasonal`, `local_time`, and/or `subsolar_longitude`, separated by spaces. |
| `--download` | Off | Transfer selected files. |
| `--metadata-only` | Off | Select only `.xml` and `.lbl` files. |
| `--match TEXT` | No filter | Case-insensitive literal substring of the filename; **not a regex**. |
| `--max-files N` | Unlimited | Select the first N matched files. Must be positive; `0` is invalid. |
| `--timeout SECONDS` | `45` | HTTP timeout. |
| `--attempts N` | `5` | Download attempts per file, with backoff. Use a positive integer. |

Collection paths are `seasonal/slon/pols/`, `diurnal/ltim/pols/`, and `diurnal/slon/pols/`, respectively. Selection preserves the requested collection order and sorts filenames within each collection; metadata/substring filters run before the file limit.

**The manifest includes all files in the requested collections, before filename, metadata, and count filters.** The terminal separately reports selected-file totals.

Download seasonal metadata first:

```powershell
.\.venv\Scripts\python.exe "download scripts/download_diviner_south_polar.py" --collections seasonal --metadata-only --download
```

Download seasonal files matching a shared filename substring, including matching labels:

```powershell
.\.venv\Scripts\python.exe "download scripts/download_diviner_south_polar.py" --collections seasonal --match 'ls030_slon01' --download
```

Check the current manifest for that substring before downloading. A file limit can separate a table from its labels, so omit `--max-files` when acquiring a complete matching set.

Select two collections and allow longer requests:

```powershell
.\.venv\Scripts\python.exe "download scripts/download_diviner_south_polar.py" --collections seasonal local_time --timeout 120 --attempts 5
```

This last command inventories only; add `--download` to transfer the selection.

Outputs:

- `download_manifest.csv`: collection, filename, bytes, GiB, and URL.
- `<collection>/<filename>`: downloaded tables and labels.
- Transfer failures are printed to the terminal; this script does not write a failure CSV.

## Lunar illumination: 2016 polar maps

Script: [download_lunar_illumination_2016.py](download_lunar_illumination_2016.py). Sources: [NASA PDS illumination archive](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/extras/illumination/) and [PGDA Product 69](https://pgda.gsfc.nasa.gov/products/69).

For each selected pole, the script expects ten maps: solar illumination, Earth visibility, and permanent shadow at each of the 65°/240 m, 75°/120 m, and 85°/60 m combinations, plus one 65°/240 m sky-visibility map. These latitude/resolution combinations are fixed in the script.

By default, it selects the south pole with original IMG/LBL pairs, existing PGDA GeoTIFFs, and one source README: **31 files**. It downloads the GeoTIFFs from PGDA; it does not convert the IMG files locally.

| Flag | Default | Behavior |
| --- | --- | --- |
| `-h`, `--help` | — | Print help and exit. |
| `--output PATH` | `LOLA_Illumination_2016` | Directory for manifests and downloads. |
| `--download` | Off | Transfer selected files. |
| `--hemisphere {south,both}` | `south` | Select the south pole or both poles. There is no north-only option. |
| `--skip-img` | Off | Exclude original IMG/LBL files and the source README. |
| `--skip-tif` | Off | Exclude PGDA GeoTIFFs. |
| `--timeout SECONDS` | `90` | HTTP read timeout; connection timeout is fixed at 20 seconds. |
| `--retries N` | `3` | Total transfer attempts per source URL, including the first attempt. Use a positive integer. |
| `--delay SECONDS` | `0.5` | Delay after each attempted file transfer; also contributes to retry backoff. Use a nonnegative number. |

Do not combine `--skip-img` and `--skip-tif`: the script rejects that combination. There are no filename, resolution, region, or file-count filters.

Download the default south-polar set:

```powershell
.\.venv\Scripts\python.exe "download scripts/download_lunar_illumination_2016.py" --output "data/raw/moon/illumination_2016" --download
```

Download south-polar GeoTIFFs only (10 files):

```powershell
.\.venv\Scripts\python.exe "download scripts/download_lunar_illumination_2016.py" --output "data/raw/moon/illumination_2016" --skip-img --download
```

Inventory both poles with all formats (61 files):

```powershell
.\.venv\Scripts\python.exe "download scripts/download_lunar_illumination_2016.py" --output "data/raw/moon/illumination_2016" --hemisphere both
```

Outputs:

- `manifests/download_manifest.csv`: selected products, URLs, relative paths, formats, resolutions, and size-check results.
- `manifests/pds_img_index.html` and, when GeoTIFFs are included, `manifests/pgda_product69_snapshot.html`: source snapshots.
- `original_pds/<hemisphere>/<category>/`: IMG/LBL pairs.
- `geotiff/<hemisphere>/<category>/`: GeoTIFFs.
- `documentation/readme_illumination_2016.txt`: included with originals.
- `manifests/completed_downloads.json`: successful transfer receipts.
- `manifests/failed_downloads.csv`: written if transfers fail.

## Interrupting, resuming, and checking results

Press **Ctrl+C** to stop. Rerun the same command with the same output directory and `--download` to resume. All three scripts download sequentially, keep incomplete transfers as `.part` files, and request a byte-range resume. If the server ignores the range request, they restart that file.

Existing-file handling differs:

| Script | When a completed file is skipped |
| --- | --- |
| LOLA Product 90 | Any existing file with a nonzero size. It does not verify that file against the source size. |
| Diviner | Its size matches the known remote size. Files with an unexpected or unknown size are reconsidered as partial transfers. |
| Illumination | Its size matches the known remote size, or, if that size is unknown, its URL and nonzero size match a saved completion receipt. |

These are size/existence checks, not checksum verification. The illumination script can fall back to the MIT mirror for originals and the source README; switching servers restarts the partial file from byte zero. GeoTIFFs have no mirror fallback.

Diviner and illumination check free space against known remaining file sizes. Unknown sizes are excluded, so the estimate may be incomplete. These checks also do not subtract existing partial-file bytes from the required space. Leave room for processing outputs separately.

Manifests are regenerated on each run. A failure CSV from an earlier run is not automatically removed after a later successful run; use the latest terminal result to interpret it.

## Troubleshooting and scope

- **Missing `requests` or `bs4`:** run the dependency-install command with the same Python interpreter used to launch the scripts.
- **No matching files:** inspect the manifest and check the filter syntax. LOLA's `--match` is regex; Diviner's is a literal substring. LOLA can finish with zero selected downloads, so check its selected count.
- **Timeouts:** Diviner and illumination expose `--timeout`; increase it for slow responses. LOLA's timeout and retry settings are fixed in its code.
- **Archive layout or expected-link errors:** the scripts depend on live source listings. Inspect the source page and error rather than guessing replacement URLs.
- **Diviner partial larger than listed size:** the script will not truncate it automatically. Inspect the affected file and move it aside before retrying if a fresh transfer is needed.
- **Multiple lunar regions:** none of these scripts accepts coordinates or a bounding box. Download the appropriate source products, then crop and process the chosen regions in a separate step. A filename filter is not a spatial crop.

To see the installed script's own flag reference without contacting the archives:

```powershell
.\.venv\Scripts\python.exe "download scripts/download_lola_product90.py" --help
.\.venv\Scripts\python.exe "download scripts/download_diviner_south_polar.py" --help
.\.venv\Scripts\python.exe "download scripts/download_lunar_illumination_2016.py" --help
```

## FABDEM V1-2: Earth elevation

Script: [download_fabdem.py](download_fabdem.py). Source: the [official Bristol archive catalog](https://data.bris.ac.uk/datasets/s5hqmjcdj8yo2ibzi9b4ew3sn/). This downloads **FABDEM**, not the original Copernicus DEM. Dependencies are the same: `requests` and `beautifulsoup4`.

FABDEM is distributed in ZIP bundles covering 10-degree blocks. Bounding-box selection downloads intersecting archive blocks in full; it does not crop rasters or guarantee that every point inside the box has a land tile. ZIPs remain compressed for a separate extraction step. The dataset uses [CC BY-NC-SA 4.0](https://research-information.bris.ac.uk/en/datasets/fabdem-v1-2/).

Run these examples from the project root using your working Python interpreter. The bounding box below is an **example area in the Atacama**, not a finalized project site selection.

Preview the selected archives and their exact catalog sizes:

```powershell
python "download scripts/download_fabdem.py" --bbox -69 -24 -68 -23
```

Download that selection:

```powershell
python "download scripts/download_fabdem.py" --bbox -69 -24 -68 -23 --download
```

Coordinates are **WEST SOUTH EAST NORTH**, in decimal degrees. Negative longitude means west; negative latitude means south. Repeat `--bbox` to select multiple areas; shared archives are selected once:

```powershell
python "download scripts/download_fabdem.py" --bbox -69 -24 -68 -23 --bbox -117 35 -116 36
```

The second box is another usage example, not a verified analog recommendation. To select a known archive by name instead:

```powershell
python "download scripts/download_fabdem.py" --archive S30W070-S20W060_FABDEM_V1-2.zip --download
```

| Flag | Default | Behavior |
| --- | --- | --- |
| `-h`, `--help` | — | Show usage without contacting the server. |
| `--bbox WEST SOUTH EAST NORTH` | None | Select archive blocks overlapping this box. Repeat for multiple boxes. Edge-only contact is excluded. |
| `--archive FILENAME` | None | Select an exact ZIP filename from the catalog. Repeat for multiple archives. |
| `--all` | Off | Explicitly select the entire catalog. Only use for an intentional global download. |
| `--output PATH` | `data/raw/earth/fabdem` | Root for archives and provenance files. |
| `--download` | Off | Transfer the selection; requires `--bbox`, `--archive`, or `--all`. |
| `--timeout SECONDS` | `90` | Positive HTTP read timeout; connection timeout is 20 seconds. |
| `--attempts N` | `3` | Positive number of transfer attempts per file. |

Choose one selection method: `--bbox`, `--archive`, or `--all`. With no selection flags, the script inventories the full catalog but cannot download it accidentally. Boxes crossing the date line must be split into two boxes, one on each side. `--bbox` is archive selection, not geographic clipping.

Each run stores a timestamped catalog snapshot, **selected-file** CSV manifest, and JSON run record under `manifests/`. The run record includes the selection, dataset/license references, transfer settings, failures, and completed-file SHA-256 hashes. Downloads go under `archives/`.

Ctrl+C preserves `.part` transfers. Rerun the same command to resume. If the server ignores Range, the current partial download restarts. Completed ZIPs are checked for exact size and ZIP CRC before being skipped; verification may take time for large archives. These checks detect accidental corruption, not publisher-authenticated provenance or scientific raster validity.

An existing invalid completed ZIP or invalid full-size partial is preserved and reported as a failure. Inspect it and move it aside before downloading a fresh copy. Do not run concurrent download commands against the same output directory. The disk-space estimate is conservative and does not subtract partial-file bytes; reserve extra space for later extraction.

Verification commands (local synthetic HTTP transfers only; no elevation downloads):

```powershell
python -m unittest discover -s "download scripts/tests" -v
python -m ruff check "download scripts/download_fabdem.py" "download scripts/tests/test_download_fabdem.py"
python -m pyright "download scripts/download_fabdem.py" "download scripts/tests/test_download_fabdem.py"
```

## ESA WorldCover 2021 v200: Earth land cover

Script: [download_worldcover.py](download_worldcover.py). Source: [ESA data access](https://esa-worldcover.org/en/data-access), using anonymous HTTPS access to the official S3 bucket. Requires `requests`; no AWS account or notebook is needed.

Preview the Map tiles for the same three candidate boxes used for FABDEM:

```powershell
python "download scripts/download_worldcover.py" --project-areas
```

Start the download yourself:

```powershell
python "download scripts/download_worldcover.py" --project-areas --download
```

`--project-areas` uses Northern Arizona `(-112.5, 35, -111, 36)`, Lanzarote `(-13.95, 28.8, -13.35, 29.3)`, and Atacama near San Pedro `(-68.6, -23.2, -67.8, -22.6)`. These are the candidate boxes, not the full 10-degree FABDEM archive footprints. Each intersecting WorldCover tile is downloaded in full on its own 3-degree grid.

For different areas, use repeated bounding boxes instead:

```powershell
python "download scripts/download_worldcover.py" --bbox -112.5 35 -111 36 --bbox -68.6 -23.2 -67.8 -22.6 --download
```

| Flag | Default | Behavior |
| --- | --- | --- |
| `-h`, `--help` | — | Show help without contacting the server. |
| `--project-areas` | Off | Select the three candidate boxes listed above. |
| `--bbox WEST SOUTH EAST NORTH` | None | Custom box in decimal degrees; repeat to select multiple areas. Split date-line crossings into two boxes. |
| `--output PATH` | `data/raw/earth/worldcover` | Root for maps, receipts and manifests. |
| `--download` | Off | Download selected tiles; otherwise save inventory only. |
| `--timeout SECONDS` | `90` | Positive HTTP read timeout; connection timeout is 20 seconds. |
| `--attempts N` | `3` | Positive number of transfer attempts per tile. |

Choose either `--project-areas` or `--bbox`. The script pins **2021 v200 Map**, approximately 10 m, EPSG:4326. It does not download the 2020 map, annual imagery composites, or InputQuality data. ESA lists InputQuality under its Terrascope access routes rather than the public map-download route used here.

Outputs:

- `v200/2021/map/*.tif`: categorical land-cover maps, not clipped or resampled.
- `v200/2021/map/*.tif.json`: source URL, expected bytes, ETag, local SHA-256 and verification time. Keep these receipts with the rasters.
- `manifests/`: timestamped S3 catalog pages, selected-file CSV, class legend, and JSON run status/provenance.

Interrupted files retain `.part` and `.part.json` files. Rerun the same command to resume; the saved URL, size and ETag must still match. Transfers use `If-Match` to avoid combining different source versions. Completed files are skipped only after their source receipt, size, TIFF header and local hash pass checks. ETags are source identifiers, **not assumed to be MD5 hashes**. Full raster decoding and spatial alignment are separate preprocessing steps.

If a file is corrupt or its receipt is missing/mismatched, it is preserved and reported as a failure. Inspect it and move the affected file/sidecars aside together before retrying a fresh download. Do not run simultaneous commands against the same output folder.

The source uses **CC BY 4.0**. Dataset DOI: `10.5281/zenodo.7254221`. Preserve attribution when publishing results. The shared official legend linked by ESA is recorded in each run; class 60 means **bare / sparse vegetation**, not guaranteed vegetation-free ground. Treat map values as categories; use nearest-neighbor resampling or documented class-area aggregation during later alignment, rather than averaging class codes.

## TerraClimate V1.1: Earth monthly climate

Script: [download_terraclimate.py](download_terraclimate.py). Uses the provider's historical THREDDS NetCDF Subset Service, documented on the [TerraClimate data page](https://www.climatologylab.org/terraclimate.html).

Install dependencies, then start the download:

```powershell
python -m pip install requests scipy
python "download scripts/download_terraclimate.py" --project-areas --download
```

Omit `--download` to save a catalog snapshot and request plan only. The defaults request **2015–2024**, five variables, and the same three candidate boxes as FABDEM/WorldCover: **150 regional files**. The server subsets the native approximately 4 km (1/24-degree) grid; it does not download global rasters. Returned cell centers can extend slightly beyond each box. Response sizes are unknown until the server generates them.

| Flag | Default | Behavior |
| --- | --- | --- |
| `--project-areas` | Off | Northern Arizona, Lanzarote, and Atacama near San Pedro; coordinates match the WorldCover section. |
| `--bbox WEST SOUTH EAST NORTH` | None | Repeat for custom boxes; mutually exclusive with `--project-areas`. Split date-line crossings. |
| `--start-year` / `--end-year` | `2015` / `2024` | Inclusive historical window; all requested source years must exist in the live catalog. |
| `--variables` | `tmin tmax ppt ws srad` | Space-separated subset of these five variables. |
| `--output` | `data/raw/earth/terraclimate` | Root for raw regional subsets, receipts, and manifests. |
| `--download` | Off | Fetch the planned NetCDF files. |
| `--timeout` | `120` | Positive read timeout in seconds; connection timeout is 20 seconds. |
| `--attempts` | `3` | Positive attempts per subset; failed transfers restart from zero. |
| `-h`, `--help` | — | Show help without network access. |

For example, one year of temperature for the three areas:

```powershell
python "download scripts/download_terraclimate.py" --project-areas --start-year 2024 --end-year 2024 --variables tmin tmax --download
```

[Variable definitions](https://www.climatologylab.org/terraclimate-variables.html): `tmin` and `tmax` are monthly averages of minimum/maximum air temperature (degrees C), `ppt` is monthly precipitation total (mm), `ws` is monthly wind speed (m/s), and `srad` is downward shortwave radiation (W/m²). These are monthly climate fields, not daily extremes or direct equivalents of lunar surface temperature. The ten-year window is an initial project choice, not a standard 30-year climate normal.

The downloaded classic NetCDF files retain original packed values, fill values, scale factors and offsets. Apply each variable's `scale_factor` and `add_offset` after masking missing data during later analysis. No notebook, local clipping, resampling, or climate aggregation is run here. V1.1 uses ERA5 temporal information and WorldClim spatial climatology; do not mix it with V1.0 as a continuous series.

Files go under `subsets/<area>/<bounds-hash>/`, with one year-variable `.nc` and `.nc.json` receipt. The script checks V1.1 metadata, all 12 monthly timestamps, grid spacing and geographic coverage, data dimensions, and the presence of valid land cells each month. Receipts include request parameters, catalog modification date, packing metadata, bytes, and SHA-256. Timestamped `manifests/*_run.json` files record planned requests and progress; keep them with the catalog snapshots and receipts. Source metadata reports CC0 1.0; retain dataset references when publishing.

Rerun the same command after interruption. Completed files are skipped only after matching their request/source receipt, local hash, and NetCDF validation. Partial requests restart because NCSS responses are generated dynamically. Existing completed files with missing/mismatched receipts are preserved and reported as errors; inspect and move those files and their sidecars aside before fetching replacements. A changed source catalog modification date also requires that explicit decision. Do not run two commands against the same output folder simultaneously.

## OpenStreetMap: support-zone roads and infrastructure

Script: [download_osm.py](download_osm.py). Downloads public [Geofabrik extracts](https://download.geofabrik.de/) in compact `.osm.pbf` format. Requires `requests` (already used by the other downloaders).

```powershell
python "download scripts/download_osm.py" --project-areas --download
```

Omit `--download` to fetch only source metadata/checksums and save a pinned selection. The project selection contains **Arizona, Canary Islands, Chile, and Bolivia** (about **889 MB** when checked on 27 October 2026). Bolivia is included because the Atacama box extends across the Chile–Bolivia border. These are full regional extracts, larger than the terrain boxes, so surrounding support-zone features remain available. No account is needed.

| Flag | Default | Behavior |
| --- | --- | --- |
| `--project-areas` | Off | Select all four extracts above. |
| `--regions NAME ...` | None | Alternative selection: `arizona`, `canary-islands`, `chile`, `bolivia`, `northern-california`, `jordan`. Mutually exclusive with `--project-areas`; the original four-region default is unchanged. |
| `--date YYMMDD` | Discover latest | Pin an available calendar date. Reject redirects or an existing selection for a different date. |
| `--chunk-bytes N` | Whole remaining file | Request bounded byte ranges when full transfers stall. Each returned range and body size is checked before continuing; full-file checksums still govern completion. |
| `--output PATH` | `data/raw/earth/osm` | Output root for extracts, receipts and manifests. |
| `--download` | Off | Download the pinned PBF extracts; otherwise plan only. |
| `--timeout SECONDS` | `120` | Positive HTTP read timeout; connection timeout is 20 seconds. |
| `--attempts N` | `3` | Positive transfer attempts per extract. |
| `-h`, `--help` | — | Show help without contacting Geofabrik. |

The first run resolves each `latest` URL to a dated extract, or requests the explicit `--date`, and saves `manifests/selection.json`, including publisher MD5, exact bytes, HTTP modification time, source pages and attribution. Different regions may have different snapshot dates. The URL date and HTTP modification time describe the extract, not a verified observation date for every mapped object; inspect replication metadata in the PBF during later processing.

The Death Valley/Wadi Rum expansion uses `--regions northern-california jordan --date 261025 --chunk-bytes 8388608 --output data/raw/earth/environment_expansion/20261030/osm --download`. Current provider polygons cover both rectangles; Northern California is the covering subextract for this Death Valley box. See the [source selection and historical-boundary qualification](../notebooks/diagnostics/environment-expansion-research-20261030/SOURCES.md). The earlier four-region selection and its saved data remain separate.

Subsequent runs reuse that saved selection rather than silently switching to newer daily files. Keep the selection file. For a deliberately newer snapshot or a different selection, use a new `--output` folder. Geofabrik does not retain every daily extract indefinitely; if a pinned URL expires before completion, plan a fresh snapshot in a new folder.

Outputs:

- `extracts/*.osm.pbf`: original compressed OSM data. Do not unzip these as ZIP archives.
- `extracts/*.osm.pbf.json`: pinned source and local SHA-256 receipt.
- `manifests/selection.json`: reusable source plan and publisher checksum text.
- `manifests/*_run.json`: per-run completion or interruption status.

Rerun the same command after interruption. `.part` downloads resume when the server supports Range; otherwise that file restarts. Exact byte count and publisher MD5 must match before a completed file is published. Verified completed files are skipped using their receipts, MD5 and SHA-256. Existing completed files with missing/mismatched receipts or corruption are preserved and reported; inspect and move the affected file/receipt aside before fetching a replacement. Do not run concurrent commands against the same output folder.

These checks verify transfer integrity; they do not decode every PBF object or establish mapping completeness. Later processing must extract relevant roads, settlements, buildings and facilities, clip to explicit support zones, and deduplicate overlapping country extracts by OSM object type and ID. No clipping, feature processing, or notebook is run by this downloader.

Use this data for **support-zone access and logistics**, separately from terrain CNN inputs. Mapped roads do not establish legal access or emergency readiness. Attribution: **© OpenStreetMap contributors; extracts by Geofabrik**. Source data is under [ODbL 1.0](https://www.openstreetmap.org/copyright); retain attribution and review its terms when distributing derived databases.
