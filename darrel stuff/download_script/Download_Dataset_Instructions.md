# Environmental data downloads

One guide for the existing-data downloader and additive downloads. Acquisition does not perform EDA, set equipment limits or establish suitability. See [source priorities](../research/Research_Notes.md) and [accepted findings](../EDA/EDA_Notes.md#scope-and-coverage).

## Choose the tool and destination

| Tool, relative to repository root | Default destination | Purpose |
| --- | --- | --- |
| `darrel stuff/download_script/download_environmental.py` | `darrel stuff/data/` | Core, Moon-support, bounded research and public-reference selections. |
| `darrel stuff/download_script_addons/download_script_addons.py` | `D:/projects/NASA Dataset` | Additional D07/D08/D11/D14/D15/D20/D26/D27 coverage without replacing existing inputs. |

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

# Additive three-year/seven-region plan: preview, bounded sample, then chosen full run
.\.venv\Scripts\python.exe "darrel stuff\download_script_addons\download_script_addons.py" --dry-run
.\.venv\Scripts\python.exe "darrel stuff\download_script_addons\download_script_addons.py" --sample --download
.\.venv\Scripts\python.exe "darrel stuff\download_script_addons\download_script_addons.py" --download --workers 4
```

Use `--help` for the current CLI. Change destination with `--output PATH`; addon `--baseline-root PATH` can reference existing collections. A pinned `--from-inventory PATH` preserves exact selections, not an exemption from current limits/integrity checks. Research `inventory.json` and Moon-support `run.json` are different schemas, not interchangeable.

## Selection and quality boundaries

- Addon default: rolling three-year desired selection, archive-limited and capped through October 2026 (exclusive stop). Static/historical records are not forced into recent dates. Jobs are interleaved across datasets; primary CRaTER is sparse monthly, secondary is daily. Requested duration is not proof of acquired/qualified coverage.
- GOES platform/version/direction/energy support remains separate. Do not stitch GOES-16/19 as calibrated equivalent observations or convert flux to crew dose without transport/response evidence.
- Diviner D20 queries are monthly/region/channel (3-9), count-first, preserving explicit calibration/miscellaneous and geometry bounds (`qca=0`, `qmi=0`, `qge` permitted 0-12). Nonzero geometry flags are **not silently qualified**. Validate labels/temperature sentinels, clip the true projected ROI and deduplicate native observation identities, not temperatures, before aggregation. Longitude envelopes can split at 0/360 degrees.
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
