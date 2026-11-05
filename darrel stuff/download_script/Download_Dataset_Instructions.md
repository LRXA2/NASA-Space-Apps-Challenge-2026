# Environmental Dataset Downloads

`download_environmental.py` inventories/downloads only the **four P1 entries** in [project_dataset.md](../project_dataset.md), spanning three dataset families:

1. **TerraClimate v1.1:** 2015–2024, `tmin tmax ppt ws srad`, for northern Arizona, Lanzarote and Atacama — 150 regional NetCDF subsets.
2. **TerraClimate expansion:** the same years/variables for Death Valley and Wadi Rum — 100 additional subsets.
3. **Diviner south-polar seasonal temperature:** tables and source labels only; the recorded collection has 144 tables and 144 XML labels. Live inventories determine available files.
4. **2016 south-polar illumination/visibility:** ten GeoTIFFs only, excluding north-polar maps and IMG/LBL originals.

P2/P3 sources, LOLA Product 90, WorldCover, OSM and Mars are not included. This script does not process data or convert anything to Excel. It calls the [original downloaders](../../download%20scripts/README.md) without modifying them. Manifests and downloaded data default to **`darrel stuff/data/`**, independent of the terminal's current directory. The script creates this data directory, including missing parents, if it does not exist; an existing directory and its files are preserved. This directory is excluded by [`darrel stuff/.gitignore`](../.gitignore).

## Setup

Use Python 3.10 or newer. All commands below run from `darrel stuff/download_script`. From the project root, enter it with:

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

### Download all P1 datasets immediately (skip preview)

From `darrel stuff/download_script`, use the repository-root virtual environment to download all four P1 entries without a separate preview or inventory-only run:

```cmd
..\..\.venv\Scripts\python.exe download_environmental.py --download
```

Downloads go to `darrel stuff/data/`, which is created if missing. Source inventory, manifests and validation still run as part of downloading; only the separate preview step is skipped. Allow approximately **31.1 GB** for the datasets and **35–40 GB free space** for working headroom. P2/P3 and excluded datasets are not included.

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
| `--datasets NAME [NAME ...]` | All four P1 entries | Select `earth-climate`, `earth-climate-expansion`, `lunar-temperature`, and/or `lunar-illumination`. Duplicate selections are rejected. |
| `--output PATH` | `darrel stuff/data` | Override the data root; dataset-specific subfolders are retained. Relative overrides resolve from the terminal's current directory. Missing directories are created before child execution; existing directories are reused. |
| `--download` | Off | Transfer selected files; otherwise inventory only. |
| `--dry-run` | Off | Print commands without child execution, network requests or writes, even when combined with `--download`. |
| `--timeout SECONDS` | `120` | Positive HTTP read timeout passed to each child. |
| `--attempts N` | `3` | Positive transfer-attempt count; maps to the illumination child's `--retries`. |
| `-h`, `--help` | — | Print help without contacting servers. |

Years, variables, regions, lunar collection and formats are fixed to the P1 register rather than exposed as broader source selectors.

## Outputs and resuming

Default paths, relative to the **repository root**:

```text
darrel stuff/data/earth/terraclimate/                                  Original three Earth sites
darrel stuff/data/earth/environment_expansion/20261030/terraclimate/    Death Valley and Wadi Rum
darrel stuff/data/moon/diviner/seasonal/                               Temperature tables and labels
darrel stuff/data/moon/illumination_2016/                              GeoTIFFs and manifests
```

The expansion's `20261030` folder preserves the existing source layout; it is not a new acquisition date. The children record actual timestamps. Expansion subsets use `region_01` = Death Valley and `region_02` = Wadi Rum.

Each original downloader retains its manifest, receipt, validation and existing-file behavior. TerraClimate retries restart incomplete generated subsets; the lunar downloaders can resume partial transfers. A failed child stops subsequent jobs. Press Ctrl+C to interrupt, then rerun with the same options and output root. Do not run concurrent downloads into the same output folders.

These isolated downloads do **not** automatically populate the paths pinned by the original preprocessing notebooks. Restoring or integrating data with that pipeline is a separate step; no original project folders are changed by this setup.

## Offline tests

```powershell
python -B -m unittest discover -s tests -p test_download_environmental.py -v
```

The tests mock child execution and make no source-server requests or dataset transfers.
