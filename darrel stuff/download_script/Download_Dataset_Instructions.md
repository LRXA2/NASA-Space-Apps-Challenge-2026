# Environmental data downloads

One guide for the existing-data downloader and additive downloads. Acquisition does not perform EDA, set equipment limits or establish suitability. See [source priorities](../research/Research_Notes.md) and [analysis scope](../EDA/EDA_Notes.md#scope-and-coverage).

## Choose the tool and destination

| Tool, relative to repository root | Default destination | Purpose |
| --- | --- | --- |
| `darrel stuff/download_script/download_environmental.py` | `darrel stuff/data/` | Core, Moon-support, bounded research and public-reference selections. |
| `darrel stuff/download_script_addons/download_script_addons.py` | `D:/projects/NASA Dataset` | Existing D07/D08/D11/D14/D15/D26/D27 plus eight native-file additions below. D20 GDS requests are disabled; existing inputs are preserved. |

Keep both source folders: the addon imports the shared transfer/validation utilities. Do not move sources/data or edit historical receipts just to match a document path.

## Commands

Run from the repository root in PowerShell. `--download` authorizes transfers. Without it, inventory/discovery can contact providers and write manifests; **`--dry-run` is the offline/no-write preview**.

```powershell
# Existing collections: safe offline preview
.\.venv\Scripts\python.exe "darrel stuff\download_script\download_environmental.py" --dry-run

# Bounded public references (battery/soil and other reference selections)
.\.venv\Scripts\python.exe "darrel stuff\download_script\download_environmental.py" --scope references --download --workers 4

# Core lunar temperature collection
.\.venv\Scripts\python.exe "darrel stuff\download_script\download_environmental.py" --datasets lunar-temperature --download

# Moon support from an already recorded inventory
.\.venv\Scripts\python.exe "darrel stuff\download_script\download_environmental.py" --scope moon-support --from-inventory latest --download

# Exact research selection; retain the supplied companion labels
.\.venv\Scripts\python.exe "darrel stuff\download_script\download_environmental.py" --datasets D14 D16 D28 --selections "darrel stuff\download_script\p1_research_eda_support.json" --download

# Separate Stage 3 public-reference mode
.\.venv\Scripts\python.exe "darrel stuff\download_script\download_environmental.py" --stage3-references --dry-run

# Additive fixed-date/seven-region plan: preview, bounded sample, then chosen full run
.\.venv\Scripts\python.exe "darrel stuff\download_script_addons\download_script_addons.py" --dry-run
.\.venv\Scripts\python.exe "darrel stuff\download_script_addons\download_script_addons.py" --sample --download
.\.venv\Scripts\python.exe "darrel stuff\download_script_addons\download_script_addons.py" --download --workers 4
```

Use `--help` for the current CLI. Change destination with `--output PATH`; addon `--baseline-root PATH` can reference existing collections. A pinned `--from-inventory PATH` preserves exact selections, not an exemption from current limits/integrity checks. Research `inventory.json` and Moon-support `run.json` are different schemas, not interchangeable.

## Moon environmental sources

The add-on reads published provider file listings and retrieves **native science files over HTTPS**, rather than automating browser clicks or saving NASA catalogue HTML. The existing transfer, receipt, source/hash verification, bounded retries and resume helpers are reused. The default destination remains **`D:\projects\NASA Dataset`**; no source folders or old data were moved.

| Selection key | Native selection | Time / spatial scope |
| --- | --- | --- |
| `D09_SEE` | TIMED SEE Level 3 daily NetCDF, latest published revision per date, README and matching release notes | Requested modern dates; solar-reference daily spectra with flare removal, not local UV dose. Distinct from the old SOLSTICE D09 files. |
| `D11_P2` | ARTEMIS P2 / THC merged CDF, latest version per monthly file | Requested modern dates; preserve field, ion and spacecraft-position identity separately from P1. |
| `D11_ESA` | THEMIS-B ESA Level 2 daily CDF | Requested modern dates; preserve native electron/ion distributions, modes and quality metadata. No surface-voltage inference. |
| `D20_PRP` | Diviner **south** PRP table with PDS3/PDS4 labels | Modelled annual thermal extrema/ice-stability reference, not dated D20 RDR observations. Native table is about **605 MB**; sample mode downloads labels only and explicitly defers the science payload. |
| `D32` | South-polar LAMP cumulative 240 m maps: albedo, brightness, data quality, error and exposure | Actual historical cumulative coverage, not forced into 2023-2026. Four spectral map families use their highest common published support version; sample uses one complete long-band family. Northern/monthly maps are excluded. |
| `D10` | LADEE LDEX calibrated current and mass tables with labels | Actual historical 2013-2014 mission; extends the existing small pilot, not a modern lunar dust history. |
| `D29` | LEND **RSCI** neutron spectra and time/position, with labels | Requested modern dates; no CHK housekeeping or raw EDR substitution. Other alternative reductions are not implicitly included. |
| `D35` | LADEE NMS derived species/orbit CSVs with labels | Actual historical 2013-2014 mission; extends the existing pilot, not recent lunar weather. |
| `D28` | Apollo 15/17 HFE **clean** tables, matching XML labels and bundle documentation | All published historical clean tables, preserving flags and mission-epoch time. No duplicate split/depth versions. Sample selects one complete table per mission. |
| `D14_PSE` | Apollo PSE MiniSEED MH1/MH2/MHZ motion, ATT timing, matching labels, Dataless SEED and StationXML response metadata | Default S12, **1973-01-01 inclusive to 1975-01-01 exclusive**; historical dates independent of modern selections. Latest listed revision per location/channel/day; missing days/channels are reported. Sample selects one available motion day plus response metadata. Existing `D14` metadata-only selection is unchanged. |

**D20 is disabled in the add-on:** it is absent from defaults, explicit `--datasets D20` fails before any network request, and unfinished legacy D20 jobs cannot restart a transfer. Previously downloaded D20 files and EDA are untouched. `D20_PRP` is a separate native model product and does not use the failing GDS URL. The original downloader remains read-only and retains its legacy interfaces.

**Dates:** default ongoing selections use **2023-06-01 inclusive to 2026-11-01 exclusive** (June 2023 through October 2026). This retains the previous November boundary; it does **not** silently include incomplete November observations. Override with `--start` / `--stop`. Use `--rolling-window --years 3` only to explicitly retain the earlier archive-limited rolling mode. Historical/static products keep their true scope; archive gaps remain explicit and are not fabricated into continuous coverage.

```powershell
# Full selected additions; no sample flag. Default destination is still the D drive.
.\.venv\Scripts\python.exe "darrel stuff\download_script_addons\download_script_addons.py" --datasets D09_SEE D11_P2 D11_ESA D20_PRP D32 D10 D29 D35 --download --workers 4

# Explicit date selection, if a different November endpoint is intended
.\.venv\Scripts\python.exe "darrel stuff\download_script_addons\download_script_addons.py" --datasets D09_SEE D11_P2 D11_ESA D29 --start 2023-06-01 --stop 2026-11-01 --download
```

The additions have new deterministic plan identities; old plans, checkpoints, science files and receipts are not rewritten. Same-source baseline files are referenced only after receipt/hash verification; matching filenames alone do not qualify for reuse. Native NetCDF/CDF readability and observational-label identity are checked in addition to transfer integrity. These are acquisition checks, not scientific quality qualification or operational passes.

**Sample validation:** use one bounded selection before a full transfer, inspect source gaps and receipt/hash identity, and distinguish reused baseline references from new files. The PRP sample contains labels only; its large science table needs an explicit full selection. Retain file/run limits and check disk capacity before scaling.

**Manual-download reporting:** each live run writes `manifests/addons/runs/<run>/manual_downloads.json` with exact failed file URLs when known, source-discovery holds and optional access-gated references. ChaSTE, RAMBHA-LP and ILSA use authorised [Chandrayaan-3 access](https://pradan.issdc.gov.in/ch3/); optional DFSAR uses [Chandrayaan-2 access](https://pradan.issdc.gov.in/ch2/). Keep native science, labels and quality/calibration documents, preserving actual mission dates. No login bypass is attempted. A failed automatic request is an acquisition hold, not proof that the dataset is unavailable.

### Automated Apollo additions

No manual file selection is needed for the public Apollo archives. The add-on discovers actual published files and companion labels, reuses receipt-verified baseline files, and retains the normal transfer limits, retries and resume checkpoints. Output stays under `D:\projects\NASA Dataset\datasets\D28\` and `datasets\D14_PSE\`, with the provider's subfolders retained.

```powershell
# Bounded first check: one heat-flow table per mission, one seismic day, and documentation/response metadata.
.\.venv\Scripts\python.exe "darrel stuff\download_script_addons\download_script_addons.py" --datasets D28 D14_PSE --sample --download --workers 2 --max-file-mib 16 --max-total-mib 32

# Full selected Apollo acquisition: all clean HFE tables and S12 seismic records for 1973-1974.
.\.venv\Scripts\python.exe "darrel stuff\download_script_addons\download_script_addons.py" --datasets D28 D14_PSE --download --workers 4

# Change only the historical seismic station/window; --apollo-stop is exclusive.
.\.venv\Scripts\python.exe "darrel stuff\download_script_addons\download_script_addons.py" --datasets D14_PSE --apollo-station s15 --apollo-start 1973-01-01 --apollo-stop 1975-01-01 --download
```

Waveforms are decoded and their network/station/location/channel headers checked against their filenames; response metadata is parsed and must contain instrument responses. These are readability/identity checks, not response correction or hazard qualification. ATT is retained for timing work and never substituted for ground-motion measurements. Both MHZ location modes are retained when published. Historical Earth-received timing, calibration/response epochs, coverage, deployment disturbances and HFE flags still require EDA before physical interpretation. Mini-RF remains the original downloader's `D30` global-mosaic selection and existing local coverage; no duplicate whole-volume radar acquisition is added here.

**Apollo sample validation:** check heat-flow numeric rows, MiniSEED channel identity and the matching motion-channel response metadata on a bounded sample. Review Dataless SEED/StationXML date handling explicitly; response availability alone does not qualify physical ground motion. Keep sample and full historical selections separate.

### Full-download readback

Read back each pinned full selection against its on-disk files, expected sizes and source receipts. Use explicit stratified checksum samples or a declared full rehash, and record which was performed. Inspect partial files separately. A labels-only PRP sample must not be reported as the full science payload.

| Source | Selected product types | Acquisition scope |
| --- | --- | --- |
| D09_SEE | Daily spectra and supporting documents | Requested modern dates; retain archive gaps and published revisions. |
| D11_P2 / D11_ESA | Monthly merged P2 / daily ESA CDFs | Keep spacecraft, native mode, version and actual time support separate. |
| D20_PRP / D32 | South PRP table/labels and LAMP map/support families | Static/model and cumulative historical scope, not a recent time series. |
| D10 / D35 | LADEE calibrated dust / derived exosphere products and labels | Historical mission dates and native instrument/species identity. |
| D29 | RSCI science tables and companion labels | Requested science dates; preserve instrument-state and archive support. |
| D28 | Clean HFE tables, labels and documentation | Historical Apollo 15/17 scope with native flags and sensor identity. |
| D14_PSE | S12 waveforms and response/timing metadata | Historical 1973-1974 selection; filenames do not prove gap-free within-file observations. |

**Completeness boundary:** compare the exact pinned selection rather than assuming the entire project archive is complete. Oversized CRaTER primary table/label pairs must remain explicit limit holds; do not silently raise the per-file cap or substitute secondary products. Existing acquisition files must retain their source identity.

D20 GDS stays explicitly disabled; unstarted legacy queries are not active transfers. D21-D24 require authorised access. Keep reference-rate extracts separate from their original PDFs and preserve access/manifest holds rather than inferring availability. Resolve Apollo and other PDF paths through `keep/` or `discard/` and relocation records; Earth-climate scope is separate from the Moon algorithm.

**Verification:** retain pinned run IDs, selected files, receipt/checksum scope and unresolved limits in acquisition manifests. Downloaded means acquired within the selection, not EDA-qualified or operationally adequate. [EDA preparation scope](../EDA/EDA_Notes.md#newly-acquired-inputs-and-pdf-leads).

## Selection and quality boundaries

- Addon default: fixed June 2023 start, archive-limited and capped through October 2026 (exclusive stop); explicit rolling mode remains available. Static/historical records are not forced into recent dates. Jobs are interleaved across datasets; primary CRaTER is sparse monthly, secondary is daily. Requested duration is not proof of acquired/qualified coverage.
- GOES platform/version/direction/energy support remains separate. Do not stitch GOES-16/19 as calibrated equivalent observations or convert flux to crew dose without transport/response evidence.
- Previously acquired Diviner D20 query products retain their original calibration/miscellaneous and geometry bounds (`qca=0`, `qmi=0`, `qge` permitted 0-12). The add-on no longer requests D20. Nonzero geometry flags are **not silently qualified**. Existing labels/temperature sentinels, true projected ROI and native observation identities still need validation before aggregation.
- ARTEMIS merged ion-plasma observations are not surface charging, ionization rate or crew dose. StationXML historical response epochs must match the waveform/channel; response metadata alone is not a waveform measurement.
- ShadowCam science products are unstretched numeric COGs, not browse images. Publisher/index gaps and no-observation results remain explicit, not zero hazard.
- D21-D24 remain KIV/login-required unless authorized access is provided. `--cookies PATH` accepts an existing Netscape cookie file; no login bypass. Keep credentials out of Git.
- `--selections PATH.json` can pin exact authorized HTTPS science/label groups and optional relative paths, sizes, md5/sha256. Do not substitute browse files for required numeric products.

## Limits, retry and resume

| Setting | Existing bounded research | Addon default |
| --- | --- | --- |
| Workers | 4 | 4 |
| Connection retries | Initial attempt + 3 extra | Initial attempt + 3 extra |
| Per-file cap | 512 MiB | 2,048 MiB |
| Per-dataset cap | 1,024 MiB | Explicit per-job/source selection |
| Per-run selected transfer cap | 8,192 MiB | 102,400 MiB |

Existing research defaults also select two primary groups and up to 12 listing pages per dataset. A group can include several companion files (R02 has 22). These are caps, not volume estimates; original full core collections and SDEM extraction are not bounded by research caps. Plan disk/extraction space. Known-size pools retain a 1 GiB free-space reserve.

Re-run the same selected command to resume: verified files are skipped; eligible failed transfers are retried. Receipts/source identity/checksums matter, not filename alone. Compatible partial ranges retain validated identity; never rename `.part` to claim completion. Permanent auth/checksum/schema failures remain logged rather than endlessly retried. Other jobs continue after failures.

Destination locks prevent competing writes. Remove a stale lock only after verifying its owner process is no longer live. TLS verification stays enabled; addon `--ca-bundle PATH` supports a trusted local CA bundle, not disabled certificate checking.

## Logs and diagnosis

Start with `error_log.txt` in the selected output root. It is a manifest/presence/size summary, not a new full checksum or availability audit. `errors.txt` may contain recovered retry warnings; inspect final JSON status before treating a warning as unresolved.

| Relative output path | Contents |
| --- | --- |
| `manifests/core/`, `moon_support/`, `eda_datasets/`, `environmental_runner/` | Existing plans, inventories, transfers, scope failures and diagnostics. Original climate manifests retain their compatibility paths. |
| `manifests/addons/plans/`, `discovery/` | Frozen requested selections and provider discovery evidence. |
| `manifests/addons/jobs/`, `runs/` | Exact job URLs/files/status and per-run coverage/results/debug/error logs. |
| `manifests/addons/runs/<run>/manual_downloads.json` | Exact automatic-acquisition holds plus optional authorised-access references; not an instruction to duplicate successful downloads. |
| `datasets/<ID>/...` | Addon science, labels, receipts and resumable partials. |

For a manual retry, retain the inventory's exact URL/destination, science labels and verification metadata. Existing manually supplied D27/D30 products are registered in place under `data/moon/eda_pilots/`; `data/manifests/file_relocations.json` resolves historical paths without rewriting old manifests. A `.xml.txt` may remain valid XML without renaming.

Existing downloader exit codes: 0 completed/planned selected work, 1 runtime/transfer failure, 2 unresolved research access/selection/byte limits, 130 interruption. Successful files are retained after a nonzero exit. Consult the individual addon result statuses rather than assuming every job succeeded.

## Safe maintenance

From repository root:

```powershell
# Preview disposable generated files only
.\.venv\Scripts\python.exe "darrel stuff\data_maintenance.py"

# Report missing selected files, no deletion
.\.venv\Scripts\python.exe "darrel stuff\data_maintenance.py" --report-only

# Apply only the conservative, receipt-aware generated-file cleanup
.\.venv\Scripts\python.exe "darrel stuff\data_maintenance.py" --apply
```

`--organize-manual` previews the narrowly registered manual moves; `--apply` performs verified/journalled moves. Do not prune science files, archives, labels, receipts, logs, generators, completed runs or resumable partials. Historical results/provenance are preserved; cleanup does not establish science validity.

## Verification

Downloader tests cover selection/receipt integrity, retry/resume, safe extraction, locks, access and concurrency. A successful small transfer is not archive completeness. New dataset evidence is accepted only after the [EDA workflow](../EDA/EDA_Notes.md#scope-and-coverage), not from a downloader success label alone.
