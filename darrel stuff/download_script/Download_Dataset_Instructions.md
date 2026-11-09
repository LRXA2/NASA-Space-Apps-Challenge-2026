# Environmental dataset downloader

## Golden Stage 3 reference additions

**Priority:** Golden Stage 3 inputs/adequacy/margins first, then unchanged research P1/P2/P3 tags. The original research catalog and its defaults remain compatible; these extra public engineering references use a separate flag in the **same downloader**, with the same threaded transfers, verified skips, retry policy and error continuation:

```cmd
.\.venv\Scripts\python.exe "darrel stuff\download_script\download_environmental.py" --stage3-references --dry-run
.\.venv\Scripts\python.exe "darrel stuff\download_script\download_environmental.py" --stage3-references --download --workers 2
```

| ID | Public reference | Current local result | Role / limit |
| --- | --- | --- | --- |
| S01 | [NASA BVAD Rev2 (2022)](https://ntrs.nasa.gov/citations/20210024855) | Full PDF returned local HTTP 403. A manually curated, official-browser-verified Table 3-31 extract and provenance live in `data/reference/stage3/bvad_rev2/`. | Nominal crew-load reference/sensitivity, not our selected crew, supplies or equipment. Extract is not a publisher-provided CSV or a completed PDF download. |
| S02 | [NASA-STD-3001 V2 Rev F](https://standards.nasa.gov/standard/NASA/NASA-STD-3001_VOL_2) | PDF acquired with size/hash receipt under `data/reference/stage3/nasa_std_3001_v2_f/`. | Requirement reference and quantity/applicability mapping, not automatic adoption of operational limits. |
| S03 | [NASA-STD-3001 V1 Rev C](https://standards.nasa.gov/node/238) | Crew-health reference PDF acquired under `data/reference/stage3/nasa_std_3001_v1_c/`. | Companion source referenced by V2 protection requirements; no crew-specific limit is silently adopted. |

Local certificate validation initially failed; this execution used a PEM bundle exported from the operating system's already-trusted CA store. TLS verification was **not disabled**. If the same environment needs it, set `REQUESTS_CA_BUNDLE` to `darrel stuff/data/reference/stage3/system_trust_bundle.pem` before rerunning. This is a local trust configuration, not a replacement for checking source errors. HTTP 403 is logged and continued, not bypassed.

The [Golden audit](../EDA/EDA_Results.md#14-golden-stage-3-revamp) checks completed core plus bounded research/Moon support selections. D21–D24 remain KIV; D17/D25 are unselected P2. Missing mission duration, crew, equipment, response and requirement tables must be supplied/produced as project inputs—not fabricated by downloading unrelated archives.

Use **`download_environmental.py`** for core, Moon-support, research and reference selections. The root repository's `download scripts/` helpers are reused read-only; this is not a standalone script that can be moved out of the repository.

All data, partial files, receipts, manifests and logs default to **`darrel stuff/data/`**, created if missing and excluded by `darrel stuff/.gitignore`. Existing datasets are not moved or deleted.

## Start with a preview and inventory

### Download all, skipping the preview

From the **repository root** in Windows CMD:

```cmd
.\.venv\Scripts\python.exe "darrel stuff\download_script\download_environmental.py" --download --workers 4 --connection-retries 3
```

From **`darrel stuff\download_script`**:

```cmd
..\..\.venv\Scripts\python.exe download_environmental.py --download --workers 4 --connection-retries 3
```

If the repository environment is already activated, `python download_environmental.py ...` also works from this folder. The environment is at the **repository root**, not `download_script\.venv`.

**This means all configured selections, not complete copies of every archive.** Core environmental collections retain their original full selections. Research datasets remain bounded EDA subsets. Gated entries are logged as unresolved/KIV; an incomplete exit code does not mean all the other transfers stopped.

### Optional offline preview

```cmd
..\..\.venv\Scripts\python.exe download_environmental.py --dry-run
```

No network requests, downloads, extraction or filesystem writes. It prints the selected scopes and limits. Without either `--dry-run` or `--download`, the script contacts providers and saves inventories only.

## What the single file includes

| Scope / selector | Actual selection | Local data location |
| --- | --- | --- |
| `--scope all` (default) | Core collections + required Moon support, then 36 bounded research datasets and two reference datasets. Scopes run sequentially to avoid overlapping writes; files within each transfer phase run concurrently. | Existing paths below. |
| `--scope core` | TerraClimate v1.1 for five Earth sites, 2015-2024, `tmin/tmax/ppt/ws/srad` (250 year-variable requests); all south-polar seasonal Diviner products/labels; ten south-polar illumination GeoTIFFs; required Moon support. | `earth/terraclimate/`, `earth/environment_expansion/20261030/terraclimate/`, `moon/diviner/`, `moon/illumination_2016/`. |
| `--scope moon-support` | Original seven SDEM region archives, six selected 40 m LOLA maps, illumination labels/docs and documented unit policy. Active terrain/quality files are extracted with CRC/path checks; unused ancillary `LROC-NAC-maps`/`LROC-NAC-adjust` folders stay inside the original ZIPs. | `moon/sdem/`, `moon/lola_product90/`, existing illumination/reference paths. |
| `--scope research` | Original 36 Dxx selections plus R01/R02; bounded groups and byte limits. Not full archives or guaranteed coverage of all study regions. | Primarily `moon/eda_pilots/Dxx/`; known core products reuse existing paths. |
| `--scope references` | Only R01 battery experiments and R02 Apollo 15 soil-mechanics tables. | `reference/battery_tests/`, `reference/apollo15_soil/`. |

Selecting `--datasets` restricts the run. Core names are `earth-climate`, `earth-climate-expansion`, `lunar-temperature` and `lunar-illumination`. Dxx/Rxx IDs select bounded research/reference sources. **`--datasets lunar-temperature` is the full seasonal collection; `--datasets D01` is a bounded pilot.**

### Public reference data sources

| ID | Download source / content | Limits |
| --- | --- | --- |
| **R01** | [NASA PCoE section 5 Batteries](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/), using its published [battery ZIP mirror](https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip). About 200 MiB, one package. | Lab charge/discharge/impedance experiments, not our chosen battery specification or lunar qualification. ZIP stays unextracted. |
| **R02** | [Apollo 15 PDS4 soil-mechanics bundle](https://pds-geosciences.wustl.edu/missions/apollo/a15lsrp.htm): all six digitized runs (`011`-`016`), `.tab` numeric data, `.txt` headers/raw readings, PDS4 XML labels, dataset and instrument documentation. **22 files, 144,305 bytes** at the verified selection. | Historical non-polar reference. No thumbnails, obsolete FTP paths, Apollo 16 substitution or claim of site-specific mobility certification. |

PGDA illumination/terrain and NAIF kernels are already covered by D02-D06/D19; they are not duplicated under new IDs. Geant4 is simulation software, not a missing environmental dataset; it is not automatically installed/downloaded. OLTARIS requires account approval and remains KIV. Mission/equipment parameters and project-specific modeled outputs cannot be fabricated by a downloader.

## Threading, retries and failure behaviour

- **4 simultaneous files by default**, configurable with `--workers 1` through `--workers 16`. Each worker has its own HTTP session. More workers may increase provider throttling; start with 4.
- **One initial attempt + three retries = at most four attempts** per file transfer or discovery operation by default. Backoff is 5, 10 and 20 seconds. Metadata discovery has its own finite budget; restarting discovery can involve several requests.
- Connection loss, timeouts, incomplete bodies and typed transient HTTP responses (408/429/500/502/503/504) are retried. No hidden HTTP-adapter retry loop multiplies the transfer budget.
- Authentication/permission errors (401/403), missing URLs (404), TLS/certificate failures and validation/checksum errors are **logged, not endlessly retried**. Other files/datasets continue.
- `--connection-retries 0` means **no extra retries**. For compatibility, `--attempts N` means N total attempts when `--connection-retries` is absent; prefer `--connection-retries`. The public CLI continues after failed files/datasets by default.
- Per-destination `.download.lock` files prevent two workers/instances from writing the same file. Separate processes may work on different files/scopes; overlapping targets are logged as busy, never overwritten. A crash can leave a stale lock: inspect its PID and confirm no downloader is active before manually removing that specific lock.
- Ctrl+C stops subsequent work; completed files remain. Workers may need to finish an active request up to its timeout.

### Existing files and partial transfers

A filename alone is not proof of completion. Reuse checks size, source identity, publisher checksum where available and/or the saved local SHA-256 receipt. Earlier manifests are recognized where supported, with any new local hash baseline explicitly labelled **not publisher verification**. Conflicts are logged and preserved rather than overwritten.

Research partials resume only when their saved source identity/validators and HTTP range match. Moon support retains its existing receipt/resume/CRC rules. TerraClimate is a generated subset response: an interrupted subset is safely restarted, not blindly appended. An old partial without sufficient identity evidence is retained for investigation, not silently trusted.

Keep final receipts and manifests with the data. Keep `.eda-part.json` / `.part.json` identity sidecars while a transfer is incomplete; the downloader removes only matching redundant checkpoints after completion, retaining the final receipt. Do not copy only the `.part` file to another source/destination. Never disable TLS verification. If your environment uses a trusted custom CA, configure `REQUESTS_CA_BUNDLE` with that CA file.

The approved SDEM cleanup removed **7.65 GiB of redundant extracted ancillary files**, not the original ZIPs or active terrain/quality inputs. Future restores skip extracting those two folders; their full contents remain recoverable from the ZIPs. `*_extracted.json` distinguishes active `files` from `archive_only_files`. [Verification/recovery inventory](../data/verification/workspace_cleanup_20261108T113813117681Z/final_verification.json).

## Commands for specific work

All examples below run from `darrel stuff\download_script`:

```cmd
REM New reference datasets only
..\..\.venv\Scripts\python.exe download_environmental.py --scope references --download --workers 4

REM Small bounded research selection only; does not redownload full core collections
..\..\.venv\Scripts\python.exe download_environmental.py --datasets D13 D31 --files-per-dataset 1 --download --workers 2

REM Full original temperature collection only
..\..\.venv\Scripts\python.exe download_environmental.py --datasets lunar-temperature --download --workers 4

REM Required Moon support only
..\..\.venv\Scripts\python.exe download_environmental.py --scope moon-support --download --workers 4

REM Moon support: reuse a previous exact selection if the catalogue is unavailable
..\..\.venv\Scripts\python.exe download_environmental.py --scope moon-support --from-inventory latest --download --workers 4

REM All selected data, using a previous Moon-support inventory
..\..\.venv\Scripts\python.exe download_environmental.py --download --moon-support-inventory latest --workers 4

REM Additional research P1 notebook input files (not substituted for primary pilots)
..\..\.venv\Scripts\python.exe download_environmental.py --datasets D14 D16 D28 --selections p1_research_eda_support.json --download --workers 3

REM Reuse an exact research/reference inventory without source rediscovery
..\..\.venv\Scripts\python.exe download_environmental.py --scope research --from-inventory "..\data\manifests\eda_datasets\RUN_ID\inventory.json" --download --workers 4
```

Replace `RUN_ID` with a real folder printed by the script. A pinned inventory preserves exact URLs/paths/selections; it does not waive current size limits, checksums or receipt checks. The full core collection runner recreates its request plan and checks existing files; research `inventory.json` and Moon `run.json` have different schemas and are not interchangeable.

### Bounded research limits

Defaults: **2 primary groups per dataset, 512 MiB per file, 1,024 MiB per dataset and 8,192 MiB across research selections**, up to 12 listing pages per source. A group includes its companion labels. R01 is one ZIP group; R02 is one group containing all 22 small files. Existing files are verified, not blindly redownloaded; pending transfers must fit the chosen limits. Source selection/validation can still fail even when an item fits the byte budget.

Use `--files-per-dataset`, `--max-file-mib`, `--max-dataset-mib`, `--max-total-mib` and `--pages-per-dataset` to change these explicit bounds. These limits **do not truncate the original full core collections** or cap SDEM extraction. Plan sufficient disk space: core datasets/archives can require many GB, with additional extraction space. Known-size transfer pools retain a 1 GiB free-space reserve; generated TerraClimate response sizes are not known in advance.

### Login and exact product selections

**D21 ChaSTE, D22 RAMBHA-LP, D23 ILSA and D24 DFSAR remain KIV/login_required** by default. The tool does not log in or bypass access controls. An optional `--cookies PATH` accepts an existing authorized Netscape cookie file; cookie contents are never written to manifests. Keep credentials out of Git.

`--selections FILE.json` retains the existing override format: dataset IDs map to a `scope` and `groups` of explicit HTTPS science/label file objects. Optional fields are `filename`, `relative_path`, `size_bytes`, `md5` and `sha256`.

```json
{
  "D15": {
    "scope": "Example schema only: exact authorized calibrated product and label",
    "groups": [[
      {"url": "https://ARCHIVE_HOST/PRODUCT.img"},
      {"url": "https://ARCHIVE_HOST/PRODUCT.xml", "metadata": true}
    ]]
  }
}
```

The example URLs above are placeholders, not download sources. D15 retains migrated PDS discovery; D27 retains unstretched float32 TIFF checks; D26 retains detached-label validation. Known validation-policy corrections preserve compatible partial bytes only when source identity remains identical. No browse image is substituted for a required numeric science product.

## Logs and resuming failures

**Start with `darrel stuff/data/error_log.txt`.** The public downloader refreshes this root-level summary after inventory/download runs (never during `--dry-run`). It lists missing or size-mismatched selected files, recorded transfer failures, gated/byte-limited datasets and their source/product URLs. It distinguishes a bounded-selection limitation or failed manifest write from missing data. This is an offline manifest/presence/size check, not a new checksum or online availability audit.

Under `darrel stuff/data/manifests/`:

- `core/<collection>/<run>/debug.txt` and `errors.txt`: per-file core diagnostics. Climate request/results remain in their original `earth/.../manifests/*_run.json` locations for notebook compatibility.
- `moon_support/<run>/run.json`, `debug.txt`, `errors.txt`: transfers, extraction, missing regions and unit-policy readiness.
- `eda_datasets/<run>/inventory.json`, `download.json`, `debug.txt`, `errors.txt`: URLs, sizes, exclusions, transfer outcomes, source errors and gated entries.
- `environmental_runner/<run>/errors.txt`: failed child scopes; later selected scopes still run.

`errors.txt` also includes recoverable retry warnings. Check the final JSON statuses to distinguish an eventually successful retry from an unresolved file. Re-run the same command or use a pinned inventory: verified files are skipped and failed eligible files are retried. For manual downloads, use the **exact URL and destination in the inventory**, retain labels and verification metadata, and do not rename a `.part` file to claim success.

Exit codes: **0** selected work completed/planned, **1** transfer/runtime failure, **2** unresolved research selection/access/byte-limit entries, **130** interrupted. Core failure does not suppress subsequent research work, and a nonzero code does not delete successful downloads.

### Manually supplied D27/D30

The five supplied ShadowCam/Mini-RF image and label files were [registered in place](../data/manifests/eda_datasets/20261107T182412585915Z/inventory.json) with local integrity receipts, not publisher-checksum claims. They now reside in `data/moon/eda_pilots/D27/manual_M013049982S/` and `D30/manual_global_cpr_128ppd/`, with their receipts. A [relocation journal](../data/manifests/file_relocations.json) resolves historical inventory paths for the notebooks, downloader destinations and missing-data report; no large duplicate copies or historical manifest rewrites are needed. The `.xml.txt` is still parsed as XML without renaming. Dar_026/027 explicitly pin this inventory; older Dar_008 pilot inputs remain unchanged. Complete here means the selected manual products—not full archives or proven site suitability. [Executed results](../EDA/EDA_Results.md#13-manual-shadowcam-and-mini-rf-incorporation).

The shared maintenance command `--organize-manual` previews these exact registered moves; add `--apply` to perform/resume them. It checks receipts/hashes, refuses conflicting targets, journals before moving and verifies hashes afterward. Source/label/receipt bytes are preserved; historical receipt identities deliberately retain their original acquisition paths.

## Generated-file cleanup

Completed transfers discard redundant `.part.json` identity metadata only when the final file and matching receipt exist and no resumable `.part` remains. Manifest writes use unique temporary files and remove their own temporary on failure. Local analysis runs discard unchanged, unreferenced CSV/plot/array intermediates only after a **failed** run; provenance, errors and cleanup receipts remain. The seven execution scripts under `data/verification/` clean their owned IPython/Jupyter runtime folders at exit after kernel shutdown; active runtime state is preserved.

**Never automatically prune source data, archives, receipts, logs, generators, completed runs or resumable partial downloads.** To inspect existing disposable files, run from the repository root:

```cmd
REM Preview only; no changes
.\.venv\Scripts\python.exe "darrel stuff\data_maintenance.py"

REM Apply only the conservative cleanup and refresh the missing-data report
.\.venv\Scripts\python.exe "darrel stuff\data_maintenance.py" --apply

REM Refresh error_log.txt without deleting anything
.\.venv\Scripts\python.exe "darrel stuff\data_maintenance.py" --report-only
```

`data/cleanup_log.json` records the most recent applied cleanup. Failed-run `cleanup.json` files retain individual deletion records without rewriting historical provenance. Nonidentical stale `.tmp` snapshots are preserved for investigation rather than guessed disposable.

## Verification

Offline tests cover selection preservation, source/receipt checks, safe extraction, partial/range recovery, login handling, concurrency, destination locks and exact retry limits. A real R02 sample transferred all 22 files (144,305 bytes) under `data/verification/unified_live_sample/`; labels, hashes and skip-on-rerun were checked. These downloader checks are separate from the subsequent R01/R02 analysis recorded in EDA results; a successful sample is not a full-archive completeness claim.

See [EDA results](../EDA/EDA_Results.md) for how public reference data differs from mission/equipment inputs. This downloader does not perform EDA, assign equipment limits or generate transport/power simulations.
