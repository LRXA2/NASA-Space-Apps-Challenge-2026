# Moon environmental pipeline

**Single active configuration: `config.yml` (`assumption_NASA_values`).** The alternative reference/test YAML files have been removed.

## One input CSV

Open and edit **[inputs/sites.csv](inputs/sites.csv)**. This is the single main pipeline input: 30 rows containing `id`, optional UTC window columns and the original measurement columns, including `median_visible_sky_fraction` and `median_earth_visibility_fraction`.

Most measurement cells are populated, with four intentional blanks **only in dummy rows**. NASA-labelled and synthetic scenarios use equally sized 1.2 km patches, the same statistics and the same fictional 2030-01-01 to 2030-01-09 requested window. These are controlled software fixtures, not verified NASA site assessments; static maps are not filtered to that future window. NASA labels identify a declared 2022 region, not a NASA-selected exact patch or approval of the assumed conditions.

There is no separate domain-score input CSV. Domain scores are calculated by the pipeline; do not enter scores in place of physical measurements.

## Run

From the repository root:

```powershell
python "darrel stuff/env_pipeline/env_pipeline.py" --output "darrel stuff/env_pipeline/outputs/results.csv" --overwrite
```

`inputs/sites.csv` is selected by default. The optional `--input` flag selects one replacement CSV, not additional input files. `config.yml` is configuration, not a second site-input CSV. Existing output files are protected; add `--overwrite` only when you want to replace the selected output.

## Simple output

The command-line default writes only enabled domain columns. With all nine domains enabled, it writes **12 columns**:

```text
ID, radiation, thermal, solar_illumination, dust, plasma_charging,
uv, seismic, exosphere, communications_geometry,
hard_gate_status, habitability_score
```

`habitability_score` is always the final column. Domain and habitability scores
are on 0-100 and displayed to two decimal places (internal calculations retain
full precision). Gate status explains failed/unknown eligibility. A final score
remains blank when an evaluated mandatory gate fails/is unknown or configuration
is incomplete. In available-data mode, blank measurements are omitted rather than
zero-filled; see the mode/toggles below.

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
`habitability_score` and `final_recommendation_score` receive the same eligible value.
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
keeps only ID, enabled domain scores, gate status and the final score.

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
- Simple output shows diagnostic domain scores, gate status and the gate-qualified habitability score.

The script remains standalone: Python 3.10+, PyYAML, the selected YAML and one input CSV. It does not read source datasets, preparation scripts, notebooks or provenance sidecars at runtime.

