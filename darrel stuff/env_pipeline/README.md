# Moon environmental pipeline

**Single active configuration: `config.yml` (`assumption_NASA_values`).** The alternative reference/test YAML files have been removed.

## One input CSV

Open and edit **[inputs/sites.csv](inputs/sites.csv)**. This is the single main pipeline input: 77 rows (**17 NASA-labelled, 30 synthetic and 30 dummy**) containing `id`, optional UTC window columns and the original measurement columns, including `median_visible_sky_fraction` and `median_earth_visibility_fraction`.

Most measurement cells are populated, with four intentional blanks **only in dummy rows**. All rows use the same fictional 2030-01-01 to 2030-01-09 requested window. The original seven NASA-labelled baselines and all synthetic scenarios use equally sized 1.2 km patches and the same map statistics. The ten additional NASA-labelled scenarios have assumed values, including geometry, without a measured footprint. These are controlled software fixtures, not verified NASA site assessments; static maps are not filtered to that future window. NASA labels identify a declared region, not a NASA-selected exact patch or approval of the assumed conditions.

NASA-labelled IDs cover the combined names in the [2022 announcement](https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/) and [2024 announcement](https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/). Shared names appear once. This is a dated declaration-name inventory, not a claim that all entries remain selected today or that differently named regions have disjoint geographical boundaries.

| ID | Declared region name | Announcement |
| --- | --- | --- |
| `nasa_001` | Leibnitz Beta Plateau | 2022 |
| `nasa_002` | Malapert Massif | 2022, 2024 |
| `nasa_003` | de Gerlache-Kocher Massif | 2022 |
| `nasa_004` | Haworth | 2022, 2024 |
| `nasa_005` | Faustini Rim A | 2022 |
| `nasa_006` | de Gerlache Rim 2 | 2022, 2024 |
| `nasa_007` | Connecting Ridge Extension | 2022 |
| `nasa_008` | Peak Near Shackleton | 2022 |
| `nasa_009` | Connecting Ridge | 2022 |
| `nasa_010` | de Gerlache Rim 1 | 2022 |
| `nasa_011` | Nobile Rim 1 | 2022, 2024 |
| `nasa_012` | Nobile Rim 2 | 2022, 2024 |
| `nasa_013` | Amundsen Rim | 2022 |
| `nasa_014` | Peak near Cabeus B | 2024 |
| `nasa_015` | Mons Mouton Plateau | 2024 |
| `nasa_016` | Mons Mouton | 2024 |
| `nasa_017` | Slater Plain | 2024 |

Synthetic IDs `001`-`007`, `008`-`014`, `015`-`021` and `022`-`028` are respectively east, west, north and south neighbours of baselines `nasa_001`-`nasa_007`; `029`-`030` are northeast neighbours of the first two. Offsets are 1,200 m on each applicable projected axis. Baseline lower-left coordinates are region-rectangle centres rounded down to the 1,200 m grid, using `region_bounds_m` in `EDA/Moon/Stage3_Requirements/stage3_acquired_config.json`. Each synthetic row shares its baseline's nongeometry test assumptions. These are EDA-informed project proposals, not evidence that NASA will use them; the scorer does not verify slope, landing access or resource suitability.

Additional NASA scenarios and randomized dummy values use Python `random.Random(20261112)`. NASA scenario ranges are assumed test ranges, not source measurements. Dummy ranges are broader to exercise both sides of configured gates while keeping fractions in 0-1, temperature span equal to high minus low, and sunlight duration within the 192-hour window. Dummy `001`-`010` retain controlled gate/boundary/toggle cases alongside randomized fields; blanks are Sun visibility (`005`), link margin (`006`), UV (`007`) and seismic (`008`). No generated values were tuned to improve NASA scores.

There is no separate domain-score input CSV. Domain scores are calculated by the pipeline; do not enter scores in place of physical measurements.

## Where and how to obtain the input values

**These are offline preparation instructions, not runtime dependencies.** The current `inputs/sites.csv` is a software fixture: its four map-geometry columns for `nasa_001`-`nasa_007` and all synthetic patches were extracted from native LOLA products, while their other values are test assumptions. All values for `nasa_008`-`nasa_017` and dummy rows are assumptions/randomized test inputs, apart from the explicitly blank dummy cells. To prepare real measurements for another site/period, obtain the source products below and calculate the declared quantities before supplying the CSV. Do not treat invented fixture values as source observations. The script itself never downloads data, opens these products or follows the links.

### Labels and dates you supply yourself

- `id`: assign any unique assessment label, such as `site_001`.
- `candidate_id`: optional metadata supported by the config, not a required column in the current input. It is a label, not a coordinate lookup performed by the script. Document the actual footprint/point separately.
- `start_utc`, `stop_utc`: optionally enter the requested analysis window. Use both, with a timezone, or omit both. These fields do not filter raw observations inside this script; prepare the measurements for the intended window yourself.
- Keep the original source, product/version, coordinates, quality filters, valid-day coverage and actual observation dates in your preparation notes. A numeric CSV cell alone does not establish local applicability.

### Source and preparation guide

| Input field(s) | Where to obtain the source | How to calculate the CSV value |
| --- | --- | --- |
| `median_sun_visibility_fraction` | [NASA LOLA polar illumination maps](https://pgda.gsfc.nasa.gov/products/69), average solar-illumination products. | Apply label scaling/fill masks, select the documented candidate cells and take their median. Supply a fraction, e.g. `0.52`, not `52`. This remains a long-period map summary. |
| `median_earth_visibility_fraction` | [NASA LOLA polar Earth-visibility maps](https://pgda.gsfc.nasa.gov/products/69), alongside the solar products. Local files: `darrel stuff/data/moon/illumination_2016/geotiff/south/earth_visibility/`. | Mask native fills before applying the paired label's scale/offset. Select the same documented footprint/support as the Sun/shadow summary and take the median Earth-disc visibility fraction, 0-1. Partial-disc visibility does not prove DSN/relay contact or a working RF link. |
| `window_continuous_sunlight_hours` | A candidate-local, time-resolved illumination calculation using a documented terrain/horizon model and [NAIF/SPICE ephemerides](https://naif.jpl.nasa.gov/naif/data.html), for the requested UTC window. This is a derived quantity, not a static-map lookup. | Under a documented visibility criterion, calculate the uninterrupted supported sunlight duration in the candidate window, in hours. Preserve cadence, gaps and boundary censoring. A sampled clear run alone does not prove continuous sunlight between samples; leave this field blank if continuity cannot be established. Do not multiply map-average visibility by window duration or substitute a regional reference. A valid supplied duration cannot exceed its requested window. |
| `window_minimum_link_margin_db` | A mission-specific, qualified RF link-budget calculation using the actual spacecraft/surface antenna, DSN or relay configuration, geometry, losses, noise, data rate and required receiver performance. It is not supplied by an Earth-visibility raster. | Evaluate available-minus-required link margin at the supported times/configurations across the requested candidate window; supply the qualified minimum in dB. Preserve outages and inadequate geometry/support; do not summarize only successful contacts to hide loss of service. Leave blank without the required engineering inputs. This field is ignored when the domain's hard gates are disabled. |
| `median_visible_sky_fraction` | The same [LOLA sky-visibility products](https://pgda.gsfc.nasa.gov/products/69). | Select the candidate's supported sky-solid-angle pixels, take the median in steradians, then divide by `4*pi`. Do not substitute a radiation dose or divide by `2*pi`. |
| `permanently_shadowed_cell_fraction` | The same [LOLA permanent-shadow products](https://pgda.gsfc.nasa.gov/products/69). | Count candidate cells classified as permanent shadow and divide by the supported candidate-cell count. Keep the grid, mask and footprint consistent. |
| `lowest_phase_median_temperature_kelvin`, `highest_phase_median_temperature_kelvin`, `phase_median_temperature_range_kelvin` | [LRO Diviner derived temperature products](https://pds-geosciences.wustl.edu/missions/lro/diviner.htm) and their labels, using the same documented phase-product cohort. | For candidate-associated points, calculate a median for each selected phase product. Only with the complete common cohort: take the lowest median, highest median and their difference. Do not replace these with raw instantaneous temperature minima/maxima. If the cohort is incomplete, leave the three values blank. A profile from a different EDA footprint/cohort does not automatically apply to the current 1.2 km patches. Current thermal test values are assumptions. |
| `regional_reference_sun_visibility_fraction`, `regional_reference_longest_shadow_sample_span_hours` | A regional horizon/illumination calculation using a documented lunar elevation model, Sun ephemerides and [NASA NAIF/SPICE kernels](https://naif.jpl.nasa.gov/naif/data.html). These are calculated values, not a ready-made pair of downloadable measurements. | To reproduce the earlier EDA reference, use the same region center, 2020-2021 period, 2 m height, 20 km horizon radius and hourly sampling. Clear fraction = clear samples / recorded samples. For each blocked run, measure first-to-last sampled time and keep the longest span. Preserve gaps/censoring; it is not guaranteed continuous darkness. These remain regional reference values, not candidate-local measurements. |
| `orbital_radiation_counter_median`, `orbital_radiation_counter_maximum` | [LRO CRaTER archive](https://pds-ppi.igpp.ucla.edu/data/lro-crater/), secondary science (`SEC`) tables with their labels. | For the current project's selected-state cohort, retain `BIASCMD=1`, `CALLOW=0`, `CALHIGH=0`, all six `PROCDFLAG=1`, and finite nonnegative `GOOD`/`REJECT`/`TOTAL` counters. Compute each UTC day's `GOOD` median and maximum. The first CSV value is the median of valid daily medians; the second is the maximum of valid daily maxima. This cohort is a project selection, not complete instrument qualification. Preserve counts per SEC record; no dose conversion is implied. |
| `median_solar_far_uv_irradiance_w_m2` | [TIMED SEE Level 3 daily spectra](https://lasp.colorado.edu/see/data/daily-averages/level-3/), NetCDF products and README. | Use the complete supported 115-180 nm band. Integrate the daily spectral irradiance across the band using wavelength-bin widths, then take the median of valid daily band integrals. Result: W/m2. Retain model-assisted/flare-removed/1-AU scope; this is not a local surface UV reading. |
| `median_spacecraft_ion_density_per_cm3`, `median_spacecraft_electron_density_per_cm3`, `median_spacecraft_electric_potential_volts` | [THEMIS/ARTEMIS data access](https://themis.ssl.berkeley.edu/data_products/index.php?nlist=2&ntype=2_tha-2_thb-2_thc-2_thd-2_the): select `thb` / ESA L2 (ARTEMIS P1), not an arbitrary Earth-orbit plasma product. | Use `thb_peif_density`, `thb_peef_density` and `thb_peef_sc_pot`, respectively. Apply native fill/valid-range, unique-clock and quality==0 selection. Keep full-ion and full-electron modes separate. Compute daily record medians, then the median of valid daily medians. Preserve native density/potential units; spacecraft potential is not surface charging voltage. |
| `historical_median_dust_detector_current_charges_per_second` | [LADEE LDEX calibrated data](https://sbnarchive.psi.edu/pds4/ldex/ladee_ldex_20240411/data_calibrated/), `current/` tables plus paired XML labels. Existing local copies are under `D:\projects\NASA Dataset\datasets\D10\` and the earlier `darrel stuff/data/moon/eda_pilots/D10/` baseline. | Read native `CURRENT`, apply clock/fill handling, retain signed background-subtracted values, take daily medians and then the median across valid days. Unit: elementary charges/s. Do not insert impact-catalog counts or mass-deposition estimates into this field. |
| `historical_median_vertical_seismic_rms_counts` | [Apollo PSE archive](https://pds-geosciences.wustl.edu/missions/apollo/apollo_pse.htm): MiniSEED or equivalent GeoCSV with metadata, selecting station S12, location/mode `00`, channel `MHZ`. | Reproduce the project's daily median-centred RMS count statistic: for valid samples `x`, RMS = `sqrt(mean((x - median(x))^2))`, with the same trace/gap handling. Then take the median of supported daily RMS values. This is a project-defined count statistic, not a NASA ground-motion safety limit, event rate or acceleration measurement. |
| `historical_median_orbital_helium_density_per_cm3` | [LADEE NMS archive and calibrated collections](https://pds.nasa.gov/ds-view/pds/viewBundle.jsp?identifier=urn:nasa:pds:ladee_nms&version=2.0), helium abundance tables and labels. | Use `He_ABUNDANCE`; retain valid, unambiguous clocks and supported abundance values. Calculate daily medians, then their median. Native `P/Cc` means particles per cubic centimetre; no numerical unit conversion was made by renaming the header. Preserve orbital altitude/local-solar-time and uncertainty context; do not treat it as surface atmosphere. |

For all daily summaries, use equal weight per valid day, not an average pooled across unequal record counts. Missing days are not zero. Do not combine different instruments, versions, species or modes under one measurement name.

The earlier regional model reference covers 2020-2021, dust/helium references cover 2013-2014, and the seismic reference covers 1973-1974. These do **not** become 2030 observations because the test CSV carries 2030 requested dates. Static product label acquisition dates are not a candidate-window chronology either. The active assumption policy uses fictional scoring mappings; it does not qualify these references as local hazard measurements. Source summaries, quality masks and aggregation steps are preparation choices; changing them requires documenting the new meaning, not silently retaining an incompatible header.

### Local data and EDA cross-checks

Paths below are relative to the repository root unless they start with `D:/`.
Use the original labels/README and quality flags along with the numeric files.

| Source family | Existing local source location | Relevant EDA cross-checks |
| --- | --- | --- |
| Sun/Earth/sky visibility and permanent shadow | `darrel stuff/data/moon/illumination_2016/`; documented region extents under `darrel stuff/data/moon/sdem/` | Dar020 candidate support, Dar021 preference sensitivity and Dar054 reference-point/time/footprint limits |
| Phase thermal | `darrel stuff/data/moon/diviner/`; additional model/reference files under `D:/projects/NASA Dataset/datasets/D20_PRP/` and `D28/` | Earlier Diviner phase/cohort analyses; Dar047 depth-specific historical thermal and Dar050 static polar model are different quantities, not replacements for missing phase profiles |
| Radiation | `D:/projects/NASA Dataset/datasets/D07/`, with earlier local support under `darrel stuff/data/moon/eda_pilots/` | Dar041, Dar043 and Dar049: instrument/cohort/time support and nonlocal dose limitations |
| Solar UV | `D:/projects/NASA Dataset/datasets/D09_SEE/` | Dar044 and Dar045: complete spectral-band support, quality and time coverage |
| Plasma / spacecraft potential | `D:/projects/NASA Dataset/datasets/D11_ESA/`; separate P2 context in `D11_P2/` | Dar044 and Dar046: full/reduced modes, clocks and native quality selection must not be pooled |
| Historical dust | `D:/projects/NASA Dataset/datasets/D10/` | Dar044 and Dar048: signed current, uncertainty and mass-threshold distinctions |
| Historical seismic | `D:/projects/NASA Dataset/datasets/D14_PSE/` | Dar044 and Dar053: S12 channel/mode, gap handling and raw-count/response distinctions |
| Historical exosphere | `D:/projects/NASA Dataset/datasets/D35/` | Dar044 and Dar051: species, uncertainty, orbital sampling and clock handling |

See [EDA notes](../EDA/EDA_Notes.md) and [research/source notes](../research/Research_Notes.md) for the accepted scopes. Cross-checking studies does not make different footprints, instruments, epochs or statistics interchangeable. Preserve original file/version, coordinates, masks, supported counts, actual dates and aggregation choices in preparation notes. The standalone scorer cannot verify that provenance from a numeric cell.

### Where do thresholds and multipliers come from?

They are **configuration decisions, not another downloadable measurement**. Use a justified applicable screening requirement for a hard threshold, documented utility reference bounds for a preference, and explicit project priorities for multipliers. An observed maximum is not automatically a safety limit. Validate sensitivity to multiplier choices; do not label project weights as NASA weights. The current `assumption_NASA_values` thresholds, preference directions/bounds and equal weights are explicitly project assumptions for testing, not sourced or adopted NASA safety requirements. Change them in `config.yml`; do not infer them from the fixture min/max.

## Run

From the repository root:

```powershell
python "darrel stuff/env_pipeline/env_pipeline.py" --output "darrel stuff/env_pipeline/outputs/results.csv" --overwrite
```

`inputs/sites.csv` is selected by default. The optional `--input` flag selects one replacement CSV, not additional input files. `config.yml` is configuration, not a second site-input CSV. Existing output files are protected; add `--overwrite` only when you want to replace the selected output.

## Simple output

The command-line default writes only enabled domain columns. With all nine domains enabled, it writes **13 columns**:

```text
ID, radiation, thermal, solar_illumination, dust, plasma_charging,
uv, seismic, exosphere, communications_geometry,
hard_gate_status, Fail Reason, final_habitability_score
```

`final_habitability_score` is always the final column. Domain and habitability scores
are on 0-100 and displayed to two decimal places (internal calculations retain
full precision). `Fail Reason` lists blocking gates with actual values, required
YAML limits and units, or explains missing required evidence/configuration. It is
blank when a final score is available; omitted measurements in available-data mode
are not themselves failures. Detailed export includes the same column alongside
the existing audit reasons. A final score
remains blank when an evaluated mandatory gate fails/is unknown or configuration
is incomplete. In available-data mode, blank measurements are omitted rather than
zero-filled; see the mode/toggles below.

With the current equal weights, the final score is the mean of the included,
available domain scores, not a sum or an extra hard-gate penalty. It uses unrounded
domain scores, so averaging the displayed two-decimal values can differ slightly.
Priority labels do not change weights; `multiplier` does. Turning off a domain's
hard gates does not remove its score: communications still contributes while
`enabled: true` and `include_in_score: true`, even when `hard_gates_enabled: false`.

For full audit details, explicitly request `--detailed`:

```powershell
python "darrel stuff/env_pipeline/env_pipeline.py" --output "darrel stuff/env_pipeline/outputs/results.csv" --detailed --overwrite
```

This still writes only the selected output CSV; it does not generate a duplicate.
`--compact` remains accepted as an explicit synonym for the simple default.
The Python `run()` API keeps its existing detailed default for compatibility;
pass `compact=True` to request the simple export directly.

## Pipeline flow (matching the code)

```text
config.yml + inputs/sites.csv
              |
              v
Validate configuration and input rows
              |
              v
For each site, evaluate measurements:
  - Hard gates: Passed / Failed / Unknown
  - Soft preferences: normalized utilities, 0-1
  - Context-only values: retained, not scored
              |
              v
Calculate enabled diagnostic domain scores, 0-100
              |
              v
Calculate comparison_preference_score from the mode-selected available domains
              |
              v
Check final eligibility:
  - Any mandatory failure -> no final score/rank
  - Any evaluated unknown gate or unconfigured selected score/weight -> no final score/rank
  - Enabled evaluated gates pass and mode-selected scoring is complete -> final score
              |
              v
Rank eligible sites within the same requested UTC window
              |
              v
Write one results CSV (full or --compact)
```

| Code entry point | Responsibility |
| --- | --- |
| `main()` | Select the single input, config, output path and export options. |
| `run()` | Load config/input, call the evaluator and write the results CSV. |
| `load_config()` / `validate_config()` | Validate settings and hash the YAML used. |
| `read_csv()` | Validate IDs, numeric inputs, declared physical bounds and optional UTC pairs. |
| `assess()` | Evaluate each site, calculate domain/aggregate scores, qualify final scores and assign ranks. |
| `hard_check()` / `gate_margin()` | Evaluate inclusive mandatory comparisons and signed distances from their limits. |
| `utility()` | Normalize the soft preference and apply its configured utility curve. |

Hard gates and preferences are evaluated inside the same per-site/domain loop.
**Gate-first eligibility** means a failed/unknown gate blocks the final recommendation;
it does not prevent diagnostic domain scores from being calculated.

```text
domain_score = 100 * sum(metric_weight * utility) / sum(metric_weights)
comparison_preference_score = sum(domain_weight * domain_score) / sum(domain_weights)
final_recommendation_score = comparison_preference_score only when eligible
```

With equal domain weights, the aggregate averages the domains actually included
for that row. Available-data mode explicitly renormalizes around missing
measurements; strict mode withholds the aggregate instead. The detailed output
records the actual per-row `score_scope`, coverage and normalized contributions.
`final_habitability_score` and `final_recommendation_score` receive the same eligible value.
Final ranks sort scores descending; equal scores use assessment ID as the tie-break.
Undated assessments form a separate group from dated ones, and input row order is
preserved in the output. `--compact` changes only the exported columns to ID plus
domain scores, gate status and the final habitability score, not the calculations or gate decisions.

## Pipeline mode and independent domain toggles

Current settings in `config.yml`:

```yaml
pipeline_mode: available_data  # strict | available_data

domains:
  communications_geometry:
    enabled: true
    include_in_score: true
    hard_gates_enabled: false
```

| Setting | Meaning |
| --- | --- |
| `enabled: false` | Disable the entire domain: no measurement evaluation, scores, weights or gates. Its simple-output column is omitted. |
| `include_in_score: false` | Exclude the domain from the aggregate, while leaving its enabled hard gates active. Diagnostic scores may still be shown. |
| `hard_gates_enabled: false` | Turn off only this domain's hard checks. Supplied scoring inputs still contribute when included. Gate-only measurements are ignored. |
| `pipeline_mode: strict` | A missing selected measurement blocks its domain/final score; missing required gate evidence is Unknown. |
| `pipeline_mode: available_data` | Omit blank measurements and renormalize metric/domain weights per row. Missing-only domains stay blank, but do not block otherwise supported final scoring. |

**Comms is currently enabled for scoring, with its hard gate off.** If two rows
have Earth-visibility data, comms contributes to those two. If a third has no
Earth-visibility data, its comms score stays blank and the aggregate uses its
other available domains. Missing/negative link-margin values do not block any
row while comms hard gates are off. Re-enable `hard_gates_enabled` to apply them.

In available-data mode, a missing measurement for an otherwise configured active
gate is recorded as `Skipped_missing`, not as a physical pass. Supplied values
are still checked against all enabled YAML hard gates. A known failure still
blocks the final score. Unconfigured limits/weights/preferences and missing
required dates for **supplied** measurements are not excused by this mode.

If every selected gate lacks data, eligibility stays Unknown. If all hard gates
are intentionally toggled off, available-data mode permits a preference-only
score when at least one complete included domain is available. A row with no
scoring data never receives an invented zero or final rank.

Missing mode/toggle settings preserve compatibility: `strict`, `enabled: true`
and `hard_gates_enabled: true`. Input columns do not need to change when toggling.
The same settings work for every domain. Detailed output records the mode, skipped
checks, actual score scope, coverage and normalized contributions. Simple output
keeps only ID, enabled domain scores, gate status, `Fail Reason` and the final score.

**Available-data scores may use different factors across rows.** Inspect the
scope/coverage in `--detailed` before treating them as like-for-like site comparisons.
This is an explicit test/comparison policy, not evidence of operational safety.

## Scoring behavior

The nine domains are radiation, thermal, solar illumination, dust, plasma/charging, UV, seismic, exosphere and communications geometry.

The active `config.yml` policy is **`assumption_NASA_values`**: project assumptions for testing NASA-site scenarios, **not official NASA values or safety limits**. All nine domain definitions retain complete preference bounds and equal domain weights of 1.0; all nine are currently enabled, with comms hard gates disabled. One score-bearing metric per domain avoids weighting multiple related proxies as independent evidence. Other fields are either gate-only or context-only. These fictional mappings must not be used to interpret orbital/reference quantities as local hazard, dose, surface charging or real habitability.

| Domain | Test soft preference (utility bounds) | Assumed hard gate |
| --- | --- | --- |
| Radiation | Lower orbital counter median, 0-100 counts/SEC record | Counter maximum <=7500 counts/SEC record |
| Thermal | Lower phase-median temperature span, 0-300 K | Lowest phase median >=40 K; highest <=300 K |
| Solar illumination | Higher median Sun visibility, 0-1 | Candidate-window continuous sunlight >=156 h |
| Dust | Signed detector current: outer bounds -1000 to 60000 charges/s; preferred plateau 0-10000 | Current between -1000 and 55000 charges/s |
| Plasma / charging | Spacecraft potential: outer bounds -20 to 15 V; preferred plateau -5 to 5 | Potential between -15 and 10 V |
| UV | Lower FUV irradiance, 0-0.06 W/m2 | Irradiance <=0.055 W/m2 |
| Seismic | Lower historical RMS, 0-20 counts | RMS <=15 counts |
| Exosphere | Helium abundance: outer bounds 0-20000 P/Cc; preferred plateau 1000-10000 | Abundance <=16000 P/Cc |
| Communications geometry | Higher median Earth visibility, 0-1 | Candidate-window minimum link margin >=0 dB |

Every bound, direction, plateau and gate above is an **assumption for exercising software**, not a NASA-certified environmental response. Equality passes. The sunlight gate requires the supplied UTC pair. The link gate also requires it when that gate is enabled. Final score is the equal-weight average of the mode-selected included domain scores after enabled gate eligibility is met; otherwise it stays blank. Domain diagnostics can still be shown when final eligibility is blocked.

- Known active-gate failure dominates Unknown. Failed or evaluated Unknown checks prevent final scores/ranks; `Skipped_missing` is not counted as a pass.
- Missing values are never zero-filled. Available-data mode explicitly omits them and renormalizes weights; strict mode does not.
- Higher/lower/target-range preferences normalize measurements; optional utility curves act after normalization.
- Domain scores are weighted metric utilities on 0-100. Final scoring requires mode-selected available domains and enabled gate eligibility.
- `comparison_preference_score` is diagnostic, not an operational approval or replacement for the final score.
- Simple output shows diagnostic domain scores, gate status, `Fail Reason` and the gate-qualified habitability score.

The script remains standalone: Python 3.10+, PyYAML, the selected YAML and one input CSV. It does not read source datasets, preparation scripts, notebooks or provenance sidecars at runtime.

