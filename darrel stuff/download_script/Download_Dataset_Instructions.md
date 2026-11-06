# Environmental Dataset Downloads

`download_environmental.py` inventories/downloads the **four P1 entries** in [Critical_Project_Dataset.md](../Critical_Project_Dataset.md), plus the original supporting inputs required by the Moon environmental EDA. The P1 entries span three dataset families:

1. **TerraClimate v1.1:** 2015–2024, `tmin tmax ppt ws srad`, for northern Arizona, Lanzarote and Atacama — 150 regional NetCDF subsets.
2. **TerraClimate expansion:** the same years/variables for Death Valley and Wadi Rum — 100 additional subsets.
3. **Diviner south-polar seasonal temperature:** tables and source labels only; the recorded collection has 144 tables and 144 XML labels. Live inventories determine available files.
4. **2016 south-polar illumination/visibility:** ten GeoTIFFs only, excluding north-polar maps and IMG/LBL originals.

The default now also restores **seven SDEM region archives**, **six selected LOLA Product 90 maps**, and the small source metadata/unit policy needed by the copied Moon notebooks. It does not collect other optional sources, reserve regions, WorldCover, OSM or Mars. It does not run EDA or convert data to Excel.

The entry point reuses the [original downloaders in root `/download scripts`](../../download%20scripts/README.md), leaving those files unchanged. `download_moon_support.py` supplies the missing SDEM selection/extraction and documented-unit restoration, reusing the original discovery, transfer and checksum routines. No OSM dataset is requested when reusing its generic byte/checksum helper.

Manifests and downloaded data default to **`darrel stuff/data/`**, independent of the terminal's current directory. Missing directories are created; matching existing files are checked and skipped using each handler's verification rules. Conflicting files are preserved and reported, not silently overwritten. The directory is excluded by [`darrel stuff/.gitignore`](../.gitignore).

## Setup

Use the project's **Python 3.12** environment, as used for the EDA verification. All commands below run from `darrel stuff/download_script`. From the project root, enter it with:

```cmd
cd "darrel stuff/download_script"
```

**Use `python`, not `.\.venv\Scripts\python.exe`.** The latter only works if a virtual environment actually exists inside this folder. An active `(.venv)` prompt can refer to an environment elsewhere; `python` uses the activated interpreter without assuming its location. Dry-run mode needs only Python's standard library.

This checkout's existing `.venv` is at the **repository root**, two folders above `download_script`. To use it explicitly without activation, this command has been verified from this folder:

```cmd
..\..\.venv\Scripts\python.exe download_environmental.py --dry-run
```

The same interpreter prefix can be used for the inventory, `--download`, dependency-install and test commands below instead of `python`.

If an environment is already active, keep using it. To create a new local environment instead, run `py -3 -m venv .venv`, then activate it with `.venv\Scripts\activate.bat` in Command Prompt or `.\.venv\Scripts\Activate.ps1` in PowerShell. After activation, install the download dependencies:

```cmd
python -m pip install requests beautifulsoup4 numpy scipy
```

The source files and tests stay in this script folder; inventories and downloaded data go to the sibling `darrel stuff/data/` folder.

## Start with a preview and inventory

### Download all required datasets immediately (skip preview)

From `darrel stuff/download_script`, run the same command as before. It checks the four P1 entries, skips verified completed files and restores the missing Moon support without requiring a separate command:

```cmd
..\..\.venv\Scripts\python.exe download_environmental.py --download
```

Downloads go to `darrel stuff/data/`. Source inventories, manifests and validation still run; only the separate preview step is skipped. The existing P1 collection is approximately **31.1 GB**. A source inventory checked on **6 November 2026** lists approximately **21.14 GB of additional SDEM/LOLA/support downloads**, plus further space for extracted archives. The live inventory prints the exact transfer size; extraction checks its own required space with a 1 GiB reserve. Verified existing files are not downloaded again. Do not use the old P1-only disk-space estimate for the full collection.

Support restoration downloads only these original dependencies:

| Input | Selection / purpose | Source |
| --- | --- | --- |
| SDEM terrain and quality archives | Leibnitz Beta Plateau, Malapert Massif, deGerlache–Kocher Massif, Haworth, Faustini Rim A, deGerlache Rim 2 and Connecting Ridge Extension. These preserve the original footprints, terrain and image-support evidence. | [PGDA Product 104](https://pgda.gsfc.nasa.gov/products/104), pinned [Zenodo record 17954508](https://zenodo.org/records/17954508). |
| LOLA context maps | Six exact `80S_40MPP_ADJ` products: elevation, effective resolution, elevation error, spot counts, slope and slope error. No point clouds, imagery or unrelated resolutions. | [PGDA Product 90](https://pgda.gsfc.nasa.gov/products/90). |
| Illumination documentation | Ten small PDS labels and the source README, without redownloading illumination rasters or their IMG originals. | [NASA PDS illumination archive](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/extras/illumination/). |
| Unit policy | Generates the JSON required by notebook 25 only after checking the labels' product IDs, units, descriptions and scale/offset values. Label URLs and SHA-256 evidence are retained; no guessed unit defaults. | The downloaded publisher labels. This JSON is supporting metadata, not another measurement dataset. |

Archives are checked against Zenodo's published MD5 and extracted with path, size and CRC checks. Existing extracted files are skipped only if their size/CRC match. All archive contents stay within the original seven region folders, with source archives retained. A compatible existing unit policy is preserved; a conflicting one causes an explicit error.

After restoration completes, run Moon preprocessing **05 → 06 → 13**, then EDA **25**. This supplies existing notebook prerequisites; it does **not** implement the new local-time/relationship TODO analyses.

### Optional preview and inventory

Inspect the exact commands offline, without network requests or filesystem writes:

```powershell
python download_environmental.py --dry-run
```

Create source inventories without downloading datasets, inspect their manifests and size estimates, then explicitly request transfers:

```powershell
python download_environmental.py
python download_environmental.py --download
```

Inventory mode still contacts the source servers and writes manifests. Diviner's recorded table inputs alone total approximately **30.74 GB**. Restore existing data where practical; review inventories and disk space before requesting the full collection.

For a smaller first inventory, select only the ten illumination products; inspect its manifest before adding `--download`:

```powershell
python download_environmental.py --datasets lunar-illumination
```

## Options

| Flag | Default | Behavior |
| --- | --- | --- |
| `--datasets NAME [NAME ...]` | All four P1 entries **plus Moon support** when omitted | Restrict a run to selected P1 entries: `earth-climate`, `earth-climate-expansion`, `lunar-temperature`, `lunar-illumination`. Explicit selections do not add support unless `--restore-moon-support` is also supplied. Duplicates are rejected. |
| `--restore-moon-support` | Included in the default full run | Optional shortcut to restore only Moon support, skipping the primary-data inventory. Can also add support to an explicit `--datasets` selection. |
| `--output PATH` | `darrel stuff/data` | Override the data root; dataset-specific subfolders are retained. Relative overrides resolve from the terminal's current directory. Missing directories are created before child execution; existing directories are reused. |
| `--download` | Off | Transfer selected files; otherwise inventory only. |
| `--dry-run` | Off | Print commands without child execution, network requests or writes, even when combined with `--download`. |
| `--timeout SECONDS` | `120` | Positive HTTP read timeout passed to each child. |
| `--attempts N` | `3` | Positive transfer-attempt count; maps to the illumination child's `--retries`. |
| `-h`, `--help` | — | Print help without contacting servers. |

Years, variables, lunar collections and formats remain fixed. Support restoration selects the original seven development regions, not the unopened reserves. Without `--download`, restoration writes inventories only; without `--dry-run`, those inventories require network access.

## Outputs and resuming

Default paths, relative to the **repository root**:

```text
darrel stuff/data/earth/terraclimate/                                  Original three Earth sites
darrel stuff/data/earth/environment_expansion/20261030/terraclimate/    Death Valley and Wadi Rum
darrel stuff/data/moon/diviner/seasonal/                               Temperature tables and labels
darrel stuff/data/moon/illumination_2016/                              GeoTIFFs and manifests
darrel stuff/data/moon/sdem/archives/                                  Original seven ZIPs and receipts
darrel stuff/data/moon/sdem/regions/                                   Extracted original region folders
darrel stuff/data/moon/lola_product90/large_area_dem/                   Six selected maps and receipts
darrel stuff/data/reference/environment-readiness-20261028/            Documented native_layer_units.json
darrel stuff/data/manifests/moon_support/                              Timestamped restore inventories/status
```

The expansion's `20261030` folder preserves the existing source layout; it is not a new acquisition date. The children record actual timestamps. Expansion subsets use `region_01` = Death Valley and `region_02` = Wadi Rum.

Each original downloader retains its manifest, receipt, validation and existing-file behavior. TerraClimate retries restart incomplete generated subsets; the lunar downloaders can resume partial transfers. A failed child stops subsequent jobs. Press Ctrl+C to interrupt, then rerun with the same options and output root. Do not run concurrent downloads into the same output folders.

The unit-policy folder's `20261028` date preserves the path expected by the copied notebook; source labels and current restore manifests provide the evidence. These local inputs serve the copies under `darrel stuff/EDA`, not the original project's pinned data folders. No original project source folders are changed.

TLS verification stays enabled. If a corporate/system certificate setup causes a certificate error, configure `REQUESTS_CA_BUNDLE` with a trusted CA bundle rather than disabling verification. A network/catalog failure is reported explicitly and leaves existing data intact.

## Offline tests

```powershell
python -B -m unittest discover -s tests -v
```

The tests mock child execution and make no source-server requests or dataset transfers.
