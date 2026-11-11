# Moon environmental pipeline — eight categories

**Updated 11 November 2026.** CSV -> Python -> results CSV. The active pipeline covers **radiation, thermal, solar/illumination, dust, plasma/charging, UV, seismic and exosphere**. No standalone terrain input or terrain score; no Earth-visibility, CNN, crew or equipment scoring. The older [Pipeline_Proto](../Pipeline_Proto/README.md) is unchanged.

## Open these files

| File | Purpose |
| --- | --- |
| [inputs/sites.csv](inputs/sites.csv) | **Current real input:** 21 candidates, 17 EDA-derived measurement columns plus five identity/evidence columns. |
| [inputs/column_guide.csv](inputs/column_guide.csv) | Meaning, units, scope, actual/reference dates and populated-row count for every measurement. |
| [inputs/evidence.json](inputs/evidence.json) | Per-row/per-metric support, source hashes, dates, association and uncertainty/interpretation boundaries. |
| [outputs/optional_time_dated/results.csv](outputs/optional_time_dated/results.csv) | Current dated eight-category output, including explicit time mode/comparison dates, every candidate and withholding reasons. |
| [input_template.csv](input_template.csv) | Header-only template for the current EDA-aligned schema. |
| [environmental_policy.json](environmental_policy.json) | Eight-domain registry and priority labels; numerical limits, utilities and weights remain unadopted. |
| [eda_sources.json](eda_sources.json) | Explicit accepted EDA run pins and field mappings; no automatic newest-run replacement. |
| [export_eda_input.py](export_eda_input.py) | Verifies accepted EDA output hashes, builds CSV/evidence/column guide and records export provenance. |
| [run_pipeline.py](run_pipeline.py) | Validates CSV/evidence, evaluates configured gates, computes permitted utilities and exports scores/audits. |

**The CSV is now populated from EDA, not just supplied with empty headers.** Fourteen measurement columns have values for all 21 candidates. Three thermal columns have values for five candidates only; the other 16 candidates lack a complete comparable phase-product point profile and remain blank with an explicit reason.

Numeric population is not local hazard qualification. `context_` columns describe shared requested-period observations; `reference_` columns describe explicitly historical/reference evidence. They cannot enter local hard gates or preference scores. Geometry/thermal point context has the same restriction.

## Run

From the repository root, with the existing environment and no new dependencies:

```powershell
# Score the current EDA-aligned input; choose a fresh output directory
.\.venv\Scripts\python.exe -B "darrel stuff/env_pipeline/run_pipeline.py" `
  --input "darrel stuff/env_pipeline/inputs/sites.csv" `
  --output "darrel stuff/env_pipeline/outputs/my_environment_run/results.csv"

# Rebuild input from pinned accepted EDA; sample first in a NEW directory
# Omitting BOTH dates uses each source series' own available span.
.\.venv\Scripts\python.exe -B "darrel stuff/env_pipeline/export_eda_input.py" `
  --limit 2 --output-dir "darrel stuff/env_pipeline/outputs/my_export_sample"

# Full export, with the requested June-November 2023 window
.\.venv\Scripts\python.exe -B "darrel stuff/env_pipeline/export_eda_input.py" `
  --start "2023-06-01T00:00:00Z" --stop "2023-12-01T00:00:00Z" `
  --output-dir "darrel stuff/env_pipeline/outputs/my_eda_input"

# Fictional eight-category software demo — NOT lunar recommendations
.\.venv\Scripts\python.exe -B "darrel stuff/env_pipeline/run_pipeline.py" `
  --input "darrel stuff/env_pipeline/examples/environment_only_sites.csv" `
  --policy "darrel stuff/env_pipeline/examples/environment_only_policy.json" `
  --output "darrel stuff/env_pipeline/outputs/my_environment_demo/results.csv"
```

Existing outputs/exports are protected unless `--overwrite` is explicitly supplied. The scorer cannot overwrite consumed inputs, evidence, policy or source code; the exporter protects accepted source/configuration files. Individual writes are atomic, not an all-files transaction. The final provenance JSON marks a completed export.

## Column meanings: environmental measurements

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

### Time and shared context

`start_utc` and `stop_utc` are **optional as a pair**. You may omit both CSV columns or leave both cells blank. If one date is supplied, the other is required. Supplied dates must be timezone-aware and ordered; start is inclusive and stop exclusive.

- **Both supplied:** the exporter selects radiation/UV/plasma observations in that requested window, preserving support and gaps. Existing dated behavior is unchanged.
- **Both omitted:** the exporter uses each series' own documented available span. It does not invent one common period. Historical references keep their historical spans; static products remain static.
- **Scoring an already prepared CSV without dates:** supplied numbers are not recomputed. Their documented evidence spans remain authoritative. Removing row dates does not turn a June-November summary into an all-years statistic; use the exporter to rebuild that statistic.
- Selected local time-dependent scoring inputs must have compatible evidence periods. Different source spans withhold the aggregate; different effective periods are never silently pooled into one ranking. Shared/historical context can retain different spans because it is not scored.

The exporter uses equal weight per valid day for daily-value medians. The CRaTER extreme is the maximum of reported supported daily maxima. Preserve each series' native daily-statistic meaning.

Historical dust/seismic/exosphere histories and modeled regional illumination have **their own dates** in `evidence.json` and the column guide. They are explicitly selected references, not fallback observations claimed to exist in 2023. For example, CRaTER has 153 supported days in the requested 183-day window; SEE FUV has 183. LDEX reference current has 166 supported days from 24 October 2013 through 18 April 2014, with gaps.

The same shared context can appear on several candidate rows for convenient reading; it is **one shared observation history, not independent site measurements**. The engine labels it `Context_only` and rejects its use in hard rules or scored preferences. Repeated context cannot manufacture differences between candidates.

Time has no separate weight. The exporter currently summarizes supplied daily EDA over a window; it does not manufacture finer cadence. Monthly/quarterly/yearly studies remain available upstream; calendar seasons are not lunar climate seasons.

## Input/evidence contract

Required CSV columns: `id`, `candidate_id`, `evidence_ref`. The template retains the two optional UTC columns for convenience.

| Identity/time column | Required? | Meaning |
| --- | --- | --- |
| `id` | Yes | Unique assessment-row ID. One candidate may have several rows with different IDs. |
| `candidate_id` | Yes | Exact documented site/footprint reference; no nearest-site substitution. |
| `start_utc` | Optional, with `stop_utc` | Requested inclusive UTC start, e.g. `2023-06-01T00:00:00Z`; not the first observed date of every source. |
| `stop_utc` | Optional, with `start_utc` | Requested exclusive UTC stop, e.g. `2023-12-01T00:00:00Z` includes November but not December. |
| `evidence_ref` | Column required | Evidence JSON path, relative to the CSV or absolute. Blank metadata gives Unknown; an explicitly named missing file is an error. |

- Measurement columns must be registered by the selected policy. Missing/blank values are not zero. Unknown headers, malformed/non-finite numbers, duplicate IDs/headers, ragged rows and incompatible quantities/units fail explicitly.

Evidence JSON uses `{"schema": 1, "rows": {"assessment_id": {"metric_id": { ... }}}}`. The exporter builds it automatically. Each feature records quantity/unit, Moon context, observed/modeled basis, scope, temporal support, source/hash and positive support. Candidate inputs require exact association and qualifying declarations. Context inputs require `usage: context` in policy, `quality: context_only`, recognised scope, and explicit `static_reference`, `requested_window`, `source_span` or `historical_reference` relation. Candidate-point/geometry context still requires the exact candidate ID. Omitting requested row dates never makes missing evidence dates acceptable for a time-dependent measurement.

Evidence exports retain actual/reference dates, valid days, expected days and interpretation limits. Missing thermal profiles carry a specific reason. Metadata is checked, not independently scientifically certified. A full evidence sidecar can serve several policies; unused metadata keys are not consumed and are listed in run provenance.

## Gates, scores and outputs

The active categories have planning priorities: radiation/thermal highest; solar/illumination high; dust/charging/UV medium; seismic evidence-dependent; exosphere context initially. These labels are **not numeric weights, NASA-prescribed rankings or substitutes for applicable mandatory requirements**.

The default policy remains unconfigured: no environmental limits or utility weights have been invented. Therefore all 21 real candidates currently have Unknown final assessments and blank aggregate scores. Having more numbers does not make their missing qualification disappear.

For an explicitly configured policy:

1. Any mandatory Failed -> Failed; otherwise any mandatory Unknown or an empty gate -> Unknown; all selected checks passed -> Passed.
2. Missing selected soft evidence withholds the aggregate, without zero filling or weight redistribution.
3. Only Passed candidates with complete selected scoring evidence receive final scores/ranks.
4. Context-only fields cannot determine local hard gates or enter preferences, even if numbers are present.

```text
higher-preferred utility = clip((x - lower) / (upper - lower), 0, 1)
lower-preferred utility  = 1 - higher-preferred utility

domain_score = 100 * sum(metric_weight * utility) / sum(metric_weight)
habitability_score = sum(domain_weight * domain_score) / sum(domain_weight)
final_rec_score = habitability_score only when eligible; otherwise blank
```

A `target_range` utility is also available: 1 on the preferred plateau, linear decline to 0 at outer bounds. No universal monotonic plasma/exosphere direction is adopted. Weights must be explicit positive JSON numbers; utility bounds/rationales/sources must be declared. Shared scored evidence families cannot be duplicated.

`habitability_score` is the requested label for an **environmental preference index**, not demonstrated human habitability or a safety probability. Both aggregate fields are withheld when gates do not pass. Individual supported domain preferences may remain visible diagnostically. Rank within the same policy, time mode and effective comparison period, score descending then assessment ID ascending. Preserve every input row.

Additional output time columns:

| Column | Meaning |
| --- | --- |
| `time_mode` | `specified_window` when both requested dates exist; `source_spans` when both are omitted. |
| `comparison_start_utc`, `comparison_stop_utc` | Canonical UTC window used to group comparable scored rows: requested dates if supplied, otherwise the common period of selected local window-based evidence. Blank for dateless static-only comparisons or unresolved periods. Not a common date range assigned to all contextual sources. |

The evidence audit's `evidence_start_utc`/`evidence_stop_utc` describe each contextual summary's actual/reference window; `valid_days` counts supported days and `expected_days` is its full calendar denominator. These dates can differ from the optional requested row window. See `inputs/column_guide.csv` for source-specific dates, units, scope and coverage. Its current contents describe the existing dated export, not a newly recomputed no-date run.

For `--output results.csv`, products are:

| Product | Contents |
| --- | --- |
| `results.csv` | IDs/period, `rad_score`, `thermal_score`, `solar_illumination_score`, `dust_score`, `plasma_charging_score`, `uv_score`, `seismic_score`, `exosphere_score`, their states, aggregate scores, gates, rank, coverage and reasons. **No terrain score.** |
| `results_hard_gates.csv` | Actual configured comparisons, limits/sources and statuses. |
| `results_domain_preferences.csv` | Selected utilities, weights and evidence states. |
| `results_environmental_evidence.csv` | Actual values/units, candidate/context scope, time relation, support and limitations. |
| `results_provenance.json` | Input/evidence/policy/code/helper hashes, CSV output hashes, policy snapshot and completion totals. |

The current [results](outputs/optional_time_dated/results.csv) and [evidence audit](outputs/optional_time_dated/results_environmental_evidence.csv) correspond to the unchanged dated `inputs/sites.csv`. A real two-row [no-requested-dates input](outputs/optional_time_sample/sites.csv) and its [results](outputs/optional_time_sample/results.csv) demonstrate source-specific spans. These are different summaries, not simultaneous histories. The fictional eight-category [demo results](outputs/environment_only_demo/results.csv) show a score of 80 for its passing case, with failure, Unknown and missing-soft cases withheld. Only solar/UV preferences are selected in that fictional test; its limits and weights are not scientific defaults.

## Dust datasets — already available

We already have **36 calibrated LDEX tables**: 34 under `D:\projects\NASA Dataset\datasets\D10\` (`current/`, `mass/`) and two earlier baseline tables under `darrel stuff/data/moon/eda_pilots/D10/`. [Dar_048](../EDA/Moon/Stage3_Requirements/Dar_048_dust_threshold_quality_time.ipynb) analysed current uncertainty, catalog quality/saturation classes, mass thresholds and time support. No duplicate download was needed for this integration.

Provider links:

- [LADEE LDEX archive](https://sbnarchive.psi.edu/pds4/ldex/ladee_ldex_20240411/).
- [Calibrated current and mass tables](https://sbnarchive.psi.edu/pds4/ldex/ladee_ldex_20240411/data_calibrated/): retain each table's paired XML label.
- [Derived products](https://sbnarchive.psi.edu/pds4/ldex/ladee_ldex_20240411/data_derived/): separate quantities, not interchangeable with surface deposition.
- [Instrument/data specification](https://sbnarchive.psi.edu/pds4/ldex/ladee_ldex_20240411/document/ldex_pds_sis_reve.pdf).

## Validation and compatibility

Sample-first checks preceded the 21-row export. Accepted tables were hash-verified; named daily-series summaries were independently replayed. All eight categories have represented EDA quantities, but only five candidates have complete comparable thermal point profiles. No raw datasets were moved or modified.

**Optional UTC validation:** 51 targeted tests pass. Missing date columns, blank dates, one-sided invalid windows, source-span export, missing evidence dates and noncontemporaneous input/ranking guards are covered. A real no-date sample preserves different source spans. The original 21-row dated assessment was rerun: every prior result column is unchanged; only explicit time-mode/comparison columns were added. Existing input dates were not erased and historical reports were not overwritten.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s "darrel stuff/env_pipeline/tests" -p "test_*.py" -v
```

Earlier nine-domain fixtures (`examples/sites.csv`, `examples/demo_policy.json`, `examples/evidence.json`) remain because existing compatibility tests use them; they are not the current input or recommendation policy. The default input template and native-data pipeline contain no standalone terrain field.

**Cleanup (11 November):** active outputs are limited to `optional_time_dated/` (current real results), `optional_time_sample/` (no-date sample) and `environment_only_demo/` (eight-category fictional demo). Eleven superseded run/snapshot folders and the unused former quantity policy were removed from the active layout after all 65 files were verified in `outputs/_archive/superseded_20261111.zip`. Its manifest and `outputs/_archive/cleanup_20261111.json` preserve checksums and restore paths. Inputs, pipeline code, source data and tests were not changed. The interrupted CSV update was not performed; the current input retains its explicit dates.

Scientific work still needed: adopt applicable environmental limits, defend selected utilities/weights, assess ranking sensitivity, and obtain qualified local evidence where the current data is only context. Mission/equipment suitability remains outside this environmental-only engine. See [EDA Notes](../EDA/EDA_Notes.md) and [Research Notes](../research/Research_Notes.md); the 64 Stage 4 proposals remain unadopted, not automatic numerical rules.
