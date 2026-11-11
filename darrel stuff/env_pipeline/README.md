# Standalone Moon environmental pipeline

**Runtime: `env_pipeline.py` + `config.yml` + your input CSV.** No project imports, EDA readers, manifests, evidence sidecars, downloads or extra model files. Copy the script and YAML elsewhere and it still runs.

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
| [legacy/](legacy/README.md) | User-approved preservation of the replaced project-integrated implementation and unchanged tests; never loaded by this script. |

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
| `hard_gate.operator` | `ge` (>=), `le` (<=), or `between` (inclusive). |
| `hard_gate.threshold` | Threshold for `ge`/`le`. `between` uses `lower` and `upper`. |
| `preference.direction` | `higher`, `lower` or `target_range`. |
| `preference.lower`, `upper` | Reference bounds mapping the metric to a 0-1 utility. Not automatically safety limits. |
| `preferred_lower`, `preferred_upper` | Utility-1 plateau for `target_range`; utility declines to zero at the outer bounds. |
| `requires_time_window` | If true, a missing requested UTC pair makes this metric unavailable for its configured gate/preference. Default false. |
| `evidence_family` | Shared-input identity; selected scored families must be distinct to prevent duplicated proxy weighting. |
| `priority` | Descriptive planning tag only; it does not silently become a numeric multiplier. |

Multipliers must be positive numbers. `null` means unconfigured, not zero and not an automatic pass. Unknown keys, duplicate YAML keys, unsafe object tags, invalid bounds and non-finite numbers fail clearly.

**Default config is deliberately unconfigured:** domain multipliers and the solar screening threshold are null; context measurements are not converted into local hazard scores. The current real-data run therefore has no final rankings. Configure defensible limits, utilities and included domains before expecting an aggregate. Setting a multiplier alone cannot turn orbital counters into dose or signed detector current into deposited mass.

Example **fictional settings only**, showing where to edit a selected metric:

```yaml
multiplier: 3.0             # domain importance; illustrative, not adopted
include_in_score: true
metrics:
  - column: solar_visibility_median
    unit: fraction
    role: score
    evidence_family: sun_visibility
    multiplier: 1.0
    hard_gate:
      operator: ge
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
| `solar_visibility_median` | Spatial median of solar-visibility fractions across the candidate's supported cells; 0-1. | Static candidate map summary, not requested-window sunlight continuity. |
| `geometry_sky_visible_fraction_4pi` | Median visible sky solid angle divided by 4*pi; dimensionless fraction. | Candidate radiation-geometry context, not transported dose or shielding efficiency. |
| `geometry_psr_fraction_cells` | Fraction of candidate cells classified as permanently shadowed; 0-1. | Static geometry, not a chronological shadow history. |
| `thermal_phase_median_min_K` | Minimum of the supported fixed-common phase-product medians; K. | Candidate-associated point context, not an instantaneous minimum or equipment temperature. |
| `thermal_phase_median_max_K` | Maximum of those same phase-product medians; K. | Same comparable point cohort, not a chronological extreme over the requested dates. |
| `thermal_phase_median_span_K` | Maximum minus minimum of those phase-product medians; K. | Not a continuous thermal-cycle amplitude. Complete profiles exist for five candidates. |
| `reference_region_2020_2021_sun_clear_fraction` | Fraction of model samples where the Sun clears the sampled horizon; 0-1. | 2020-2021 region-center reference, height 2m/radius 20km; not a candidate-local history. |
| `reference_region_2020_2021_blocked_sample_span_h` | Longest observed first-to-last blocked-sample span; h. | Same regional reference; cadence and endpoint censoring remain explicit. Not guaranteed uninterrupted darkness. |
| `context_crater_counter_median` | Median of supported daily selected-state CRaTER counter medians; counts/SEC record. | LRO orbital radiation context, not dose or a calibrated event rate. |
| `context_crater_reported_daily_max` | Largest reported supported daily maximum of that counter; counts/SEC record. | Descriptive observed extreme, not an adopted radiation hazard limit. |
| `context_see_fuv_115_180_W_m2` | Median of complete daily-mean FUV band integrals, 115-180 nm; W/m2. | Shared 1-AU solar context, model-assisted/flare-removed; not candidate surface UV dose. |
| `context_p1_full_ion_density_cm3` | Median of daily P1 full-ion-mode density medians; native cm^-3 descriptor. | Spacecraft observations with native quality==0 selection, not surface density. |
| `context_p1_full_electron_density_cm3` | Median of daily P1 full-electron-mode density medians; native cm^-3 descriptor. | Kept separate from ion mode; not a local charging model. |
| `context_p1_spacecraft_potential_V` | Median of daily P1 full-electron-mode spacecraft-potential medians; native V descriptor. | Spacecraft potential, not regolith surface voltage or discharge risk. |
| `reference_ldex_current_e_per_s` | Median of historical daily signed, background-subtracted LDEX current medians; elementary charges/s. | Orbital 2013-2014 reference, not deposited mass, contamination or contemporary forecast. |
| `reference_apollo_s12_mhz_rms_counts` | Median of historical Apollo S12 MHZ daily median-centred RMS values; counts. | 1973-1974 station reference, not peak ground acceleration, event rate or polar recurrence. |
| `reference_nms_He_abundance_p_cc` | Median of historical daily LADEE NMS helium-abundance medians; native P/Cc. | Orbital 2013-2014 reference, not surface atmosphere. |

No counts-to-dose, current-to-deposition, spacecraft-to-surface potential or raw-counts-to-ground-acceleration conversion is invented. No nearest-site, region-center or global-value substitution is used to pass a candidate requirement.

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
final_rec_score = habitability_score when eligible; otherwise blank
```

Changing all multipliers by the same factor does not change the normalized average; change their ratios to change priorities. Weights cannot offset a mandatory failure or Unknown. A score is an environmental preference, not a safety probability or proof of human habitability.

## Output columns

The script creates one CSV only; explanations are embedded as JSON strings inside CSV cells rather than separate audit files.

| Output | Meaning |
| --- | --- |
| `id`, `candidate_id`, UTC fields | Input identity and optional requested dates. |
| Eight `*_score` / `*_score_status` pairs | Domain preferences from 0-100, higher preferred under the YAML; states `Scored`, `Unknown` or `Context_only`. |
| `habitability_score`, `final_rec_score` | Gate-qualified environmental weighted average and its ranking-facing copy; blank if blocked. |
| `hard_gate_status` | Passed / Failed / Unknown. |
| `rank` | Descending final score within the same date group; ties use assessment ID. Input row order is preserved. |
| `time_mode`, comparison UTC fields | `specified_window` with canonical UTC grouping dates, otherwise `unspecified` with blank comparison dates. No source dates are invented. |
| `score_scope`, `evidence_coverage`, `reason` | Included domains, supplied/required scoring-value count and withholding explanation. Coverage is not scientific confidence. |
| `hard_gate_details`, `score_details` | Per-measurement values, units, configured comparisons, utilities and multipliers. Context values stay descriptive. |
| `config_name`, `config_sha256` | Name and exact YAML hash used for this result. |
| `operational_suitability` | Always `Not assessed`; mission/equipment qualification is outside this script. |

Blank scores are not zero. Severe environmental failures cannot be averaged away; no radiation limit or universal charging preference is inferred from a dataset's minimum/maximum.

## Validation

```powershell
python -m unittest discover -s "darrel stuff/env_pipeline/tests" -p "test_*.py" -v
```

21 standalone tests pass, including executing a copy in an isolated temporary directory with only the script, YAML and CSV. The 51 prior tests remain unchanged under `legacy/tests/` and also pass after mechanical path updates in the preserved scripts. No scientific raw data or the separate `Pipeline_Proto` was changed.
