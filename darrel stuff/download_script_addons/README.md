# Stage 3 / P1 download addons

**Purpose:** acquire extra environmental evidence for evaluating a Moon-base site's mission/equipment suitability. This is **additional coverage**, not a replacement for the original downloader or a second copy of its datasets.

- Script stays here: `darrel stuff/download_script_addons/download_script_addons.py`.
- New data, partials, source evidence, receipts and logs go to **`D:\projects\NASA Dataset`**. Missing directories are created.
- The original `download_script/download_environmental.py` is **unchanged**. Its transfer/checksum/resume utilities are imported read-only; keep both folders in the project.
- Default: seven study regions; latest available rolling **three years**, capped at **31 October 2026**. Each time-series source resolves its own actual latest date. Static/historical sources are not forced into recent dates.
- Four concurrent jobs, interleaved across datasets so a large thermal queue does not put every other P1 source last; one initial attempt **plus three retries** for connection loss/transient HTTP errors. Login, checksum, invalid-data and other permanent failures are logged, not endlessly retried. Other jobs continue.

## Start with a preview and inventory

Run from the repository root in PowerShell:

```powershell
# Offline preview: no network, no files/directories created.
.\.venv\Scripts\python.exe "darrel stuff\download_script_addons\download_script_addons.py" --dry-run

# Download all configured addons, skipping the preview.
.\.venv\Scripts\python.exe "darrel stuff\download_script_addons\download_script_addons.py" --download --workers 4 --connection-retries 3

# Optional live inventory only: pins sizes/URLs but does not transfer science files.
.\.venv\Scripts\python.exe "darrel stuff\download_script_addons\download_script_addons.py"
```

Live inventory **does contact providers**, generates bounded Diviner result tables on the provider, and can take a long time. Use `--dry-run` for an instant scope preview, or select a smaller scope with `--datasets D20`, `--datasets D07 D08 D11`, etc. Defaults are already configured; no coordinates/dates are needed in normal commands.

## What is additional?

| ID / category | Addon selection | Why / limits |
| --- | --- | --- |
| **D20 — thermal, Stage 3/P1** | All selected monthly Diviner RDR queries over the seven study envelopes, thermal channels **3–9**. Archive maximum is checked live; verified 8 November 2026: **15 June 2026**, so approximately **June 2023–June 2026**. | UTC, lunar local solar time, latitude/longitude, radiance, channel brightness temperature and quality flags support thermal/time/terrain EDA. Not bolometric temperature or component response. |
| **D07 — ionising radiation, Stage 3/P1** | CRaTER **daily derived secondary** tables and **one derived-primary day per available month**, plus labels, within the actual archive-limited rolling three-year window. | Primary daily files can exceed 600 MB, so the default selects the last available day/month (`--primary-days-per-month 1`), not the entire primary archive. Sparse primary days are not event-complete. Orbital detector observations are **not** local crew dose, shielding adequacy or equipment limits. |
| **D08 — energetic protons, Stage 3/P1** | GOES-16 and GOES-19 **SGPS five-minute** daily NetCDF products, within one shared family window ending at the latest available satellite date. | The retired platform bridges earlier dates rather than extending the window backwards. Event/quiet-time context; platform/version/quality remain separate. Not a stitched/calibrated lunar surface record. Overlapping satellites are distinct observations, not duplicate files. |
| **D11 — plasma / ionisation context** | ARTEMIS THB/P1 merged monthly CDF files covering the available rolling window. | Ion density, thermal speed/flow, magnetic field and spacecraft position. The verified merged product is ion-plasma context; electron parameters are not claimed merely because ESA can measure electrons. Explicit user-requested addition; original research **P2** tag is retained. Not regolith ionisation rate, surface charging, local plasma or absorbed dose. |
| **D14 — seismic interpretation, P1** | Official Apollo **StationXML response/epoch metadata** and companion PDS label. | Supports the waveform pilot already downloaded. Historical station data does not describe the south-polar sites or recent years. |
| **D15 — terrain/image context, P1** | ODE LROC calibrated NAC science image/label pilots: **up to two products per ROI / meridian segment / calendar-year intersection** with the rolling available window. | Additional geographically targeted imagery, not all NAC images. Bounding-box intersections still need footprint/quality validation in EDA. |
| **D26 — independent terrain context, P1** | ODE Kaguya **DTM Map v2** image/label pilots: up to two static tiles per ROI / meridian segment. | Replaces no SDEM terrain; adds study-overlapping alternatives to the original nonpolar pilot. Historical/static; no artificial recent timestamps. |
| **D27 — shadowed terrain context, P1** | ODE ShadowCam **unstretched 32-bit calibrated map radiance COG + XML** pilots with the same per-year/region budget. Window is anchored to the **publisher collection**, not an older search index. | Rejects stretched/browse images. Verified publisher coverage ends **30 September 2025**, but ODE only indexes through **30 September 2024**. The addon explicitly logs this remaining index gap; unindexed dates are **not** interpreted as no observations. Newer scene selection requires a verified spatial index or reviewed publisher URLs. Not a sunlight/contact continuity history. |

**Seven regions:** Leibnitz Beta Plateau, Malapert Massif, de Gerlache–Kocher Massif, Haworth, Faustini Rim A, de Gerlache Rim 2 and Connecting Ridge Extension. Projected boundaries come from the retained seven-region terrain preprocessing. The code preserves the original region IDs and spherical south-polar stereographic coordinates.

### Required Stage 3 / P1 coverage that is not downloaded again

Every run emits `coverage.json`, enumerating **all 34 original P1 rows**, plus the explicit plasma addition/gap. Static/aggregate/historical baseline sources **D01–D06, D13, D16, D19, D28, D31, D33 and D38** stay in the existing project data. A lightweight baseline-path report is included; directory presence **does not prove** applicability, full archive coverage or file integrity.

**D21 ChaSTE and D23 ILSA** remain login-gated. **D22 RAMBHA** is the separate, login-gated surface-plasma source; ARTEMIS is not a substitute. No authentication bypass is attempted. Other original gated sources remain with the original downloader, not duplicated here.

**M01/M02/M04/M05/M06/M07/M08/M09/M10/M13/M14** are project-specific test, mission/equipment, crew, safety, response, terrain/mobility, radiation-transport, power/illumination-history or operational inputs. They cannot be supplied by downloading orbital measurements. They remain explicit gaps; no invented mission profile, safety threshold, hard-rule pass or score is generated. **C01** is a baseline, not a time-varying acquisition.

## Resume, duplication and limits

- Repeat the same command to reuse the **frozen plan** and verified checkpoints. Complete Diviner queries are not regenerated when their local files remain verified.
- Source URL, exact byte count, validators and SHA-256 receipts identify completed files. Original data is checked read-only; matching source/hash evidence is recorded as a **reference**, not copied onto D:. Exact original Diviner query selections are also checked before generating fresh provider URLs. Filenames alone are never proof of identity.
- The default baseline root is `darrel stuff/data`. If the old datasets move, add `--baseline-root "E:\path\to\old\data"`. Keep that drive accessible while references are used. The addon does not relocate datasets or configure notebook/pipeline roots automatically.
- Streamed partials resume only when source identity/range validation permits. Conflicting existing files are preserved and reported; never silently overwritten. Detached terrain labels transfer before images.
- Diviner is tiled and queried monthly, **one thermal channel per job**, count-first, to stay below synchronous API limits. All channels 3–9 remain selected; splitting them avoids the provider's slow multi-channel query path and allows independent retries. Default quality maxima are **calibration 0, geometry 12, miscellaneous 0**; the latter explicitly admits some nonzero geometry flags. Raw flags stay in the tables; EDA must assess their meanings, temperature sentinels and coverage. Filters are never relaxed silently.
- Geographic envelopes can contain points outside a projected study rectangle. Use `in_region(lon, lat, REGIONS[id])` when preparing site-specific EDA. Shared query boundaries can repeat native observations; deduplicate native observation keys during EDA, not by identical temperature values. Do not claim exact CNN patch matching.
- Defaults: **2 GiB per file, 100 GiB per run, 1 GiB free-space reserve**. These are safety caps, **not a storage estimate**. A cap failure is logged and remains incomplete. Increase `--max-file-mib` / `--max-total-mib` explicitly if needed. Completed existing files do not consume a new transfer budget.
- `--max-jobs 1` limits only the current run. `--sample` creates a separate, deliberately incomplete test plan. Neither reports full-scope completion.
- Use `--refresh-plan` to recheck provider availability or retry failed discovery. Existing payloads are retained. Do not refresh while another instance is generating that same plan.
- Separate instances may process different `--datasets`. Job/file locks prevent simultaneous writes to the same output. An interrupted process may leave an `active.lock`/`.download.lock`; remove it **only after confirming its process is no longer running**.

Small examples:

```powershell
# Small real transfer test (Apollo response files, not a bulk archive).
.\.venv\Scripts\python.exe "darrel stuff\download_script_addons\download_script_addons.py" --datasets D14 --sample --download

# One narrow Diviner sample inside the study envelope; not all seven locations.
.\.venv\Scripts\python.exe "darrel stuff\download_script_addons\download_script_addons.py" --datasets D20 --sample --channels 9 --max-file-mib 8 --download
```

If your network needs an organisation trust bundle, supply `--ca-bundle "C:\path\trusted.pem"` or `REQUESTS_CA_BUNDLE`. TLS verification is never disabled. Existing `requests` and `beautifulsoup4` dependencies are reused; no new package installation is needed for downloading.

## Logs and provenance

Under **`D:\projects\NASA Dataset`**:

| Path | Contents |
| --- | --- |
| `datasets/<ID>/...` | Science files, companion labels, SHA receipts and resumable partials. |
| `manifests/addons/plans/` | Frozen source selection, resolved dates, seven region definitions and query jobs. |
| `manifests/addons/discovery/` | Official API/listing responses used for selection. |
| `manifests/addons/jobs/` | Per-job exact URLs, sizes, validators, receipts/references and completed state. |
| `manifests/addons/runs/<timestamp>/` | `debug.txt`, `errors.txt`, `error_log.txt`, `coverage.json`, `results.json`, `summary.json`. |
| **`error_log.txt`** | Latest run's missing/login/project-input/error index, source URLs and failed file URLs when pinned. Historical run logs are retained. |

`selection_complete` means the configured **bounded transfer selection** completed. It never certifies continuous observations, local environmental suitability, equipment adequacy or all Stage 3 requirements. Missing evidence remains **Unknown** in the suitability workflow.

## Official references

- [Diviner GDS query specification](https://oderest.rsl.wustl.edu/GDS_REST_V2.0.pdf) and [ODE product-query specification](https://oderest.rsl.wustl.edu/ODE_REST_V2.1.6.pdf).
- [CRaTER archive](https://pds-ppi.igpp.ucla.edu/data/lro-crater/).
- [NOAA SGPS products and caveats](https://www.ncei.noaa.gov/products/goes-r-space-environment-in-situ).
- [NASA THB_L2_MERGED description](https://cdaweb.gsfc.nasa.gov/cgi-bin/eval2.cgi?dataset=THB_L2_MERGED&index=sp_phys).
- [Apollo StationXML archive](https://pds-geosciences.wustl.edu/lunar/urn-nasa-pds-apollo_pse/data/xa/metadata/).
- [ShadowCam science archive/product formats](https://shadowcam.im-ldi.com/archive).

Test command: `.\.venv\Scripts\python.exe -B -m unittest discover -s "darrel stuff/download_script_addons/tests" -v`.

## Validation — 8 November 2026

- **41 addon tests + 81 original downloader tests passed.** The original downloader's SHA-256 stayed unchanged during this task.
- Live Diviner sample: **2,011 records**, **33 fields**, all channels **3–9**; labels/counts, channel and quality selection, sizes and SHA receipts checked. **1,964** observation centres lie inside the actual study rectangle, illustrating why the geographic envelope must be clipped before site EDA.
- Repeated all seven completed jobs with metadata/query/transfer functions forbidden: **seven verified skips**, no query regeneration or redownload.
- CRaTER: one secondary day downloaded; **86,400 × 194-byte records** agree with its label and file size. A deliberately low test cap rejected the 634 MB primary day while the secondary job still completed. Primary is configured, **not claimed live-transferred in this test**.
- GOES: both small satellite samples transferred and opened as NetCDF; each contains **288** five-minute time slots and the proton/quality variables. ARTEMIS: one CDF acquired with source/hash verification and readable ion-plasma metadata; no local ionisation-rate inference.
- Apollo StationXML parsed: **five stations, 37 channel epochs, 32 with response objects**. Response presence/applicability is not assumed for the other five or for every waveform epoch.
- LROC, Kaguya and ShadowCam science/label **inventories** checked live; their large image payloads were **not** downloaded for validation. ShadowCam publisher-versus-index lag is explicitly reported.
- Only small samples were transferred. **The full three-year/seven-region acquisition has not been started.** Detailed evidence is in `D:\projects\NASA Dataset\manifests\addons\verification\` and the referenced per-run manifests.
