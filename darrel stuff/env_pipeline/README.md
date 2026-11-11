# Standalone Moon environmental pipeline

**Runtime: `env_pipeline.py` + `config.yml` + your input CSV.** No project imports, EDA readers, manifests, evidence sidecars, downloads or extra model files. Copy the script and YAML elsewhere and it still runs.

**12 November 2026:** the 17 measurement headers now use clearer English `snake_case`. CSV/template headers and YAML `column` mappings agree. Values, units, thresholds and multipliers did not change. ID/date fields remain stable. Output CSV abbreviations have also been expanded as documented below; archived snapshots are unchanged.

Eight categories: radiation, thermal, solar/illumination, dust, plasma/charging, UV, seismic and exosphere. No terrain or Earth-visibility score.

## Files and run

| File | Purpose |
| --- | --- |
| [env_pipeline.py](env_pipeline.py) | The only active runtime script. |
| [config.yml](config.yml) | Editable hard thresholds, preference bounds and multipliers. |
| [inputs/sites.csv](inputs/sites.csv) | Current 21-row input; numeric values and existing dates preserved, sidecar pointer removed. |
| [input_template.csv](input_template.csv) | Header-only input template. |
| [outputs/results.csv](outputs/results.csv) | Current results; one row per input row. |
| [tests/test_env_pipeline.py](tests/test_env_pipeline.py) | Standalone tests, including isolated execution outside the repository. |
| [legacy_2/](legacy_2/README.md) | The replaced project-integrated implementation and its original tests, preserved separately; never loaded by this script. |

Python 3.10+ and PyYAML are required. All other imports are Python standard library.

```powershell
python -m pip install PyYAML==6.0.3

python "darrel stuff/env_pipeline/env_pipeline.py" `
  --input "darrel stuff/env_pipeline/inputs/sites.csv" `
  --config "darrel stuff/env_pipeline/config.yml" `
  --output "darrel stuff/env_pipeline/outputs/results.csv"
```

From this folder the same command is simply:

```powershell
python env_pipeline.py --input inputs/sites.csv --output outputs/results.csv
```

`--config` defaults to `config.yml` beside the script. Existing outputs are protected; choose a new output path or explicitly use `--overwrite`. Inputs, YAML and script cannot be overwritten. Only the requested results CSV is created.

## YAML settings

The config declares all eight domains. Each domain contains its input metrics and settings:

| Setting | Meaning |
| --- | --- |
| `include_in_score` | Include this domain in the final aggregate. Set false explicitly for a context-only comparison scope; never drop missing domains selectively per candidate. |
| Domain `multiplier` | Relative importance of this domain in the final weighted average. |
| Metric `multiplier` | Relative importance of this metric within its domain. Not a physical-unit conversion. |
| `column`, `unit` | CSV field and its declared unit. Numbers must actually represent that quantity; the script does not verify the measurement source. |
| `role: score` | May have a preference and mandatory gate. |
| `role: context` | Retained in result details, but cannot determine hard gates or scores. |
| `hard_gate.operator` | `above_threshold` (>=), `below_threshold` (<=), or `between` (inclusive). Equality passes; the clearer names do not change comparison boundaries. |
| `hard_gate.threshold` | Threshold for `above_threshold`/`below_threshold`. `between` uses `lower` and `upper`. |
| `preference.direction` | `higher`, `lower` or `target_range`. |
| `preference.lower`, `upper` | Reference bounds mapping the metric to a 0-1 utility. Not automatically safety limits. |
| `preferred_lower`, `preferred_upper` | Utility-1 plateau for `target_range`; utility declines to zero at the outer bounds. |
| `requires_time_window` | If true, a missing requested UTC pair makes this metric unavailable for its configured gate/preference. Default false. |
| `evidence_family` | Shared-input identity; selected scored families must be distinct to prevent duplicated proxy weighting. |
| `priority` | Descriptive planning tag only; it does not silently become a numeric multiplier. |

Multipliers must be positive numbers. `null` means unconfigured, not zero and not an automatic pass. Unknown keys, duplicate YAML keys, unsafe object tags, invalid bounds and non-finite numbers fail clearly.

**Current multiplier values:** the metric multipliers are `1.0`, meaning neutral/equal weighting within each category; multipliers on context-only fields have no scoring effect. The category/domain multipliers are **null**, not 1.0, so relative importance across categories has not been adopted. A multiplier of 2 gives twice the relative contribution of a multiplier of 1 in the weighted average; it does not double the final score. Multipliers never relax hard gates.

**`priority: Highest`, `High`, etc.:** these are human-readable planning labels only. The script does not translate them to weights or thresholds, and changing a priority label alone cannot change a result. Use the domain `multiplier` to configure actual category weighting. Legacy `ge`/`le` aliases remain accepted for existing configs; new configs should use the readable operator names.

**Default config is deliberately unconfigured:** domain multipliers and the solar screening threshold are null; context measurements are not converted into local hazard scores. The current real-data run therefore has no final rankings. Configure defensible limits, utilities and included domains before expecting an aggregate. Setting a multiplier alone cannot turn orbital counters into dose or signed detector current into deposited mass.

Example **fictional settings only**, showing where to edit a selected metric:

```yaml
multiplier: 3.0             # domain importance; illustrative, not adopted
include_in_score: true
metrics:
  - column: median_sun_visibility_fraction
    unit: fraction
    role: score
    evidence_family: sun_visibility
    multiplier: 1.0
    hard_gate:
      operator: above_threshold
      threshold: 0.5       # arbitrary software example, not a NASA limit
    preference:
      direction: higher
      lower: 0.0
      upper: 1.0
```

## Input columns

Required: `id`, a unique nonempty assessment ID. `candidate_id` is an optional label. The supplied input retains both labels and its existing dates.

| Column | Meaning |
| --- | --- |
| `start_utc`, `stop_utc` | Optional requested period, inclusive start/exclusive stop. Omit both columns or leave both blank; supplying only one is an error. Supplied values need timezone offsets. |
| Measurement columns | Numeric values declared by the YAML, with units/statistics described below. Missing fields/cells remain missing, never zero-filled. |
| Other metadata | Allowed only when named in `metadata_columns`; copied into no measurement and never treated as a file to open. |

Without dates, `time_mode` is `unspecified`: only supplied numbers are evaluated. **The standalone script cannot infer source spans or recompute date-filtered summaries.** Different supplied periods rank separately; undated rows form a separate group. Row dates are labels supplied by the caller, not independently verified acquisition histories. Preparing comparable quantities/periods is the caller's responsibility.

The YAML can register different measurement columns without code changes. The following existing columns remain available in the current input; these descriptions explain their meaning, not a runtime dependency on their original producer:

| Input column | Meaning and units | Scope and limitation |
| --- | --- | --- |
| `median_sun_visibility_fraction` | Spatial median of solar-visibility fractions across the candidate's supported cells; 0-1. | Static candidate map summary, not requested-window sunlight continuity. |
| `median_visible_sky_fraction` | Median visible sky solid angle divided by 4*pi; dimensionless fraction. | Candidate radiation-geometry context, not transported dose or shielding efficiency. |
| `permanently_shadowed_cell_fraction` | Fraction of candidate cells classified as permanently shadowed; 0-1. | Static geometry, not a chronological shadow history. |
| `lowest_phase_median_temperature_kelvin` | Minimum of the supported fixed-common phase-product medians; K. | Candidate-associated point context, not an instantaneous minimum or equipment temperature. |
| `highest_phase_median_temperature_kelvin` | Maximum of those same phase-product medians; K. | Same comparable point cohort, not a chronological extreme over the requested dates. |
| `phase_median_temperature_range_kelvin` | Maximum minus minimum of those phase-product medians; K. | Not a continuous thermal-cycle amplitude. Complete profiles exist for five candidates. |
| `regional_reference_sun_visibility_fraction` | Fraction of model samples where the Sun clears the sampled horizon; 0-1. | 2020-2021 region-center reference, height 2m/radius 20km; not a candidate-local history. |
| `regional_reference_longest_shadow_sample_span_hours` | Longest observed first-to-last blocked-sample span; h. | Same regional reference; cadence and endpoint censoring remain explicit. Not guaranteed uninterrupted darkness. |
| `orbital_radiation_counter_median` | Median of supported daily selected-state CRaTER counter medians; counts/SEC record. | LRO orbital radiation context, not dose or a calibrated event rate. |
| `orbital_radiation_counter_maximum` | Largest reported supported daily maximum of that counter; counts/SEC record. | Descriptive observed extreme, not an adopted radiation hazard limit. |
| `median_solar_far_uv_irradiance_w_m2` | Median of complete daily-mean FUV band integrals, 115-180 nm; W/m2. | Shared 1-AU solar context, model-assisted/flare-removed; not candidate surface UV dose. |
| `median_spacecraft_ion_density_per_cm3` | Median of daily P1 full-ion-mode density medians; native cm^-3 descriptor. | Spacecraft observations with native quality==0 selection, not surface density. |
| `median_spacecraft_electron_density_per_cm3` | Median of daily P1 full-electron-mode density medians; native cm^-3 descriptor. | Kept separate from ion mode; not a local charging model. |
| `median_spacecraft_electric_potential_volts` | Median of daily P1 full-electron-mode spacecraft-potential medians; native V descriptor. | Spacecraft potential, not regolith surface voltage or discharge risk. |
| `historical_median_dust_detector_current_charges_per_second` | Median of historical daily signed, background-subtracted LDEX current medians; elementary charges/s. | Orbital 2013-2014 reference, not deposited mass, contamination or contemporary forecast. |
| `historical_median_vertical_seismic_rms_counts` | Median of historical Apollo S12 MHZ daily median-centred RMS values; counts. | 1973-1974 station reference, not peak ground acceleration, event rate or polar recurrence. |
| `historical_median_orbital_helium_density_per_cm3` | Median of historical daily LADEE NMS helium-abundance medians; native P/Cc. | Orbital 2013-2014 reference, not surface atmosphere. |

No counts-to-dose, current-to-deposition, spacecraft-to-surface potential or raw-counts-to-ground-acceleration conversion is invented. No nearest-site, region-center or global-value substitution is used to pass a candidate requirement.

## Where and how to obtain the input values

**These are offline preparation instructions, not runtime dependencies.** The existing `inputs/sites.csv` already contains the prepared values we have. To rebuild them or assess another site/period, obtain the source products below and calculate the same quantities before supplying the CSV. The script itself never downloads data, opens these products or follows the links.

### Labels and dates you supply yourself

- `id`: assign any unique assessment label, such as `site_001`.
- `candidate_id`: optionally supply your site/footprint label. It is a label, not a coordinate lookup performed by the script. Prepare a documented footprint/point outside the scorer.
- `start_utc`, `stop_utc`: optionally enter the requested analysis window. Use both, with a timezone, or omit both. These fields do not filter raw observations inside this script; prepare the measurements for the intended window yourself.
- Keep the original source, product/version, coordinates, quality filters, valid-day coverage and actual observation dates in your preparation notes. A numeric CSV cell alone does not establish local applicability.

### Source and preparation guide

| Input field(s) | Where to obtain the source | How to calculate the CSV value |
| --- | --- | --- |
| `median_sun_visibility_fraction` | [NASA LOLA polar illumination maps](https://pgda.gsfc.nasa.gov/products/69), average solar-illumination products. | Apply label scaling/fill masks, select the documented candidate cells and take their median. Supply a fraction, e.g. `0.52`, not `52`. This remains a long-period map summary. |
| `median_visible_sky_fraction` | The same [LOLA sky-visibility products](https://pgda.gsfc.nasa.gov/products/69). | Select the candidate's supported sky-solid-angle pixels, take the median in steradians, then divide by `4*pi`. Do not substitute a radiation dose or divide by `2*pi`. |
| `permanently_shadowed_cell_fraction` | The same [LOLA permanent-shadow products](https://pgda.gsfc.nasa.gov/products/69). | Count candidate cells classified as permanent shadow and divide by the supported candidate-cell count. Keep the grid, mask and footprint consistent. |
| `lowest_phase_median_temperature_kelvin`, `highest_phase_median_temperature_kelvin`, `phase_median_temperature_range_kelvin` | [LRO Diviner derived temperature products](https://pds-geosciences.wustl.edu/missions/lro/diviner.htm) and their labels, using the same documented phase-product cohort. | For candidate-associated points, calculate a median for each selected phase product. Only with the complete common cohort: take the lowest median, highest median and their difference. Do not replace these with raw instantaneous temperature minima/maxima. If the cohort is incomplete, leave the three values blank; our current input has only five complete profiles. |
| `regional_reference_sun_visibility_fraction`, `regional_reference_longest_shadow_sample_span_hours` | A regional horizon/illumination calculation using a documented lunar elevation model, Sun ephemerides and [NASA NAIF/SPICE kernels](https://naif.jpl.nasa.gov/naif/data.html). These are calculated values, not a ready-made pair of downloadable measurements. | To reproduce the present reference, use the same region center, 2020-2021 period, 2 m height, 20 km horizon radius and hourly sampling. Clear fraction = clear samples / recorded samples. For each blocked run, measure first-to-last sampled time and keep the longest span. Preserve gaps/censoring; it is not guaranteed continuous darkness. These remain regional reference values, not candidate-local measurements. |
| `orbital_radiation_counter_median`, `orbital_radiation_counter_maximum` | [LRO CRaTER archive](https://pds-ppi.igpp.ucla.edu/data/lro-crater/), secondary science (`SEC`) tables with their labels. | For the current project's selected-state cohort, retain `BIASCMD=1`, `CALLOW=0`, `CALHIGH=0`, all six `PROCDFLAG=1`, and finite nonnegative `GOOD`/`REJECT`/`TOTAL` counters. Compute each UTC day's `GOOD` median and maximum. The first CSV value is the median of valid daily medians; the second is the maximum of valid daily maxima. This cohort is a project selection, not complete instrument qualification. Preserve counts per SEC record; no dose conversion is implied. |
| `median_solar_far_uv_irradiance_w_m2` | [TIMED SEE Level 3 daily spectra](https://lasp.colorado.edu/see/data/daily-averages/level-3/), NetCDF products and README. | Use the complete supported 115-180 nm band. Integrate the daily spectral irradiance across the band using wavelength-bin widths, then take the median of valid daily band integrals. Result: W/m2. Retain model-assisted/flare-removed/1-AU scope; this is not a local surface UV reading. |
| `median_spacecraft_ion_density_per_cm3`, `median_spacecraft_electron_density_per_cm3`, `median_spacecraft_electric_potential_volts` | [THEMIS/ARTEMIS data access](https://themis.ssl.berkeley.edu/data_products/index.php?nlist=2&ntype=2_tha-2_thb-2_thc-2_thd-2_the): select `thb` / ESA L2 (ARTEMIS P1), not an arbitrary Earth-orbit plasma product. | Use `thb_peif_density`, `thb_peef_density` and `thb_peef_sc_pot`, respectively. Apply native fill/valid-range, unique-clock and quality==0 selection. Keep full-ion and full-electron modes separate. Compute daily record medians, then the median of valid daily medians. Preserve native density/potential units; spacecraft potential is not surface charging voltage. |
| `historical_median_dust_detector_current_charges_per_second` | [LADEE LDEX calibrated data](https://sbnarchive.psi.edu/pds4/ldex/ladee_ldex_20240411/data_calibrated/), `current/` tables plus paired XML labels. Existing local copies are under `D:\projects\NASA Dataset\datasets\D10\` and the earlier `darrel stuff/data/moon/eda_pilots/D10/` baseline. | Read native `CURRENT`, apply clock/fill handling, retain signed background-subtracted values, take daily medians and then the median across valid days. Unit: elementary charges/s. Do not insert impact-catalog counts or mass-deposition estimates into this field. |
| `historical_median_vertical_seismic_rms_counts` | [Apollo PSE archive](https://pds-geosciences.wustl.edu/missions/apollo/apollo_pse.htm): MiniSEED or equivalent GeoCSV with metadata, selecting station S12, location/mode `00`, channel `MHZ`. | Reproduce the project's daily median-centred RMS count statistic: for valid samples `x`, RMS = `sqrt(mean((x - median(x))^2))`, with the same trace/gap handling. Then take the median of supported daily RMS values. This is a project-defined count statistic, not a NASA ground-motion safety limit, event rate or acceleration measurement. |
| `historical_median_orbital_helium_density_per_cm3` | [LADEE NMS archive and calibrated collections](https://pds.nasa.gov/ds-view/pds/viewBundle.jsp?identifier=urn:nasa:pds:ladee_nms&version=2.0), helium abundance tables and labels. | Use `He_ABUNDANCE`; retain valid, unambiguous clocks and supported abundance values. Calculate daily medians, then their median. Native `P/Cc` means particles per cubic centimetre; no numerical unit conversion was made by renaming the header. Preserve orbital altitude/local-solar-time and uncertainty context; do not treat it as surface atmosphere. |

For all daily summaries, use equal weight per valid day, not an average pooled across unequal record counts. Missing days are not zero. Do not combine different instruments, versions, species or modes under one measurement name.

The present regional reference is 2020-2021, dust/helium references are 2013-2014, and the seismic reference is 1973-1974. These do **not** become 2023 observations because the CSV row contains 2023 requested dates. The `role: context` safeguards remain in YAML. Source summaries, quality masks and aggregation steps are preparation choices; changing them requires documenting the new meaning, not silently retaining an incompatible header.

### Where do thresholds and multipliers come from?

They are **configuration decisions, not another downloadable measurement**. Use a justified applicable screening requirement for a hard threshold, documented utility reference bounds for a preference, and explicit project priorities for multipliers. An observed maximum is not automatically a safety limit. Validate sensitivity to multiplier choices; do not label project weights as NASA weights. The existing null thresholds/multipliers remain null until those choices are made.

## Gates and score mathematics

- Any mandatory Failed -> Failed; otherwise any mandatory Unknown -> Unknown; all configured mandatory checks Passed -> Passed.
- No configured mandatory gates -> Unknown, not a vacuous pass.
- Missing selected soft values, missing preference bounds or missing multipliers withhold the aggregate; no zero substitution or weight redistribution.
- Only Passed candidates with complete selected domains receive final scores/ranks. Domain preferences may remain visible diagnostically.

```text
higher utility = clip((x - lower) / (upper - lower), 0, 1)
lower utility  = 1 - higher utility

domain_score = 100 * sum(metric_multiplier * utility) / sum(metric_multiplier)
habitability_score = sum(domain_multiplier * domain_score) / sum(domain_multiplier)
final_recommendation_score = habitability_score when eligible; otherwise blank
```

Changing all multipliers by the same factor does not change the normalized average; change their ratios to change priorities. Weights cannot offset a mandatory failure or Unknown. A score is an environmental preference, not a safety probability or proof of human habitability.

## Output columns

The script creates one CSV only; explanations are embedded as JSON strings inside CSV cells rather than separate audit files.

Readable output-header changes:

| Previous header | Current header | Meaning |
| --- | --- | --- |
| `rad_score` | `radiation_score` | Radiation-domain preference, 0-100 where configured and supported. |
| `rad_score_status` | `radiation_score_status` | Whether that domain is Scored, Unknown or Context_only. |
| `final_rec_score` | `final_recommendation_score` | Final gate-qualified recommendation score; blank when blocked. |
| `config_sha256` | `configuration_file_hash` | SHA-256 hash of the exact YAML file used; the hash algorithm/value is unchanged. |

The eight score columns are `radiation_score`, `thermal_score`, `solar_illumination_score`, `dust_score`, `plasma_charging_score`, `uv_score`, `seismic_score` and `exosphere_score`, with matching `_status` columns. This is an export-label change only; score calculations and internal assessment keys remain compatible.

| Output | Meaning |
| --- | --- |
| `id`, `candidate_id`, UTC fields | Input identity and optional requested dates. |
| Eight `*_score` / `*_score_status` pairs | Domain preferences from 0-100, higher preferred under the YAML; states `Scored`, `Unknown` or `Context_only`. |
| `habitability_score`, `final_recommendation_score` | Gate-qualified environmental weighted average and its ranking-facing copy; blank if blocked. |
| `hard_gate_status` | Passed / Failed / Unknown. |
| `rank` | Descending final score within the same date group; ties use assessment ID. Input row order is preserved. |
| `time_mode`, comparison UTC fields | `specified_window` with canonical UTC grouping dates, otherwise `unspecified` with blank comparison dates. No source dates are invented. |
| `score_scope`, `evidence_coverage`, `reason` | Included domains, supplied/required scoring-value count and withholding explanation. Coverage is not scientific confidence. |
| `hard_gate_details`, `score_details` | Per-measurement values, units, configured comparisons, utilities and multipliers. Context values stay descriptive. |
| `config_name`, `configuration_file_hash` | Name and exact YAML hash used for this result. |
| `operational_suitability` | Always `Not assessed`; mission/equipment qualification is outside this script. |

Blank scores are not zero. Severe environmental failures cannot be averaged away; no radiation limit or universal charging preference is inferred from a dataset's minimum/maximum.

## Validation

```powershell
python -m unittest discover -s "darrel stuff/env_pipeline/tests" -p "test_*.py" -v
```

27 standalone tests pass, including readable-operator boundaries, output-header mappings, legacy operator compatibility and executing a copy in an isolated temporary directory with only the script, YAML and CSV. The previous integrated test suite is preserved under `legacy_2/tests/`; it is not required by the standalone runtime. No scientific raw data, scoring mathematics or archive folders changed. With user approval, one existing test's CSV-key lookup was renamed mechanically; its assertion and expected score of 80 are unchanged.
