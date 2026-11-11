# Moon environmental pipeline

**Single active configuration: `config.yml` (`assumption_NASA_values`).** The alternative reference/test YAML files have been removed.

## One input CSV

Open and edit **[inputs/sites.csv](inputs/sites.csv)**. This is the single main pipeline input: 30 rows containing `id`, optional UTC window columns and the original measurement columns, including `median_visible_sky_fraction` and `median_earth_visibility_fraction`.

Most measurement cells are populated. Four intentional blanks exercise missing-data behavior. Previously available map values were retained; missing values were filled with arbitrary, deterministic test measurements. **The completed rows are software fixtures, not verified NASA site assessments. All requested dates are fictional.** NASA-region IDs identify the original location group, not NASA endorsement of the invented values.

There is no separate domain-score input CSV. Domain scores are calculated by the pipeline; do not enter scores in place of physical measurements.

## Run

From the repository root:

```powershell
python "darrel stuff/env_pipeline/env_pipeline.py" --output "darrel stuff/env_pipeline/outputs/results.csv" --overwrite
```

`inputs/sites.csv` is selected by default. The optional `--input` flag selects one replacement CSV, not additional input files. `config.yml` is configuration, not a second site-input CSV. Existing output files are protected; add `--overwrite` only when you want to replace the selected output.

## Simple output

The command-line default writes **12 columns**:

```text
ID, radiation, thermal, solar_illumination, dust, plasma_charging,
uv, seismic, exosphere, communications_geometry,
hard_gate_status, habitability_score
```

`habitability_score` is always the final column. Domain and habitability scores
are on 0-100 and displayed to two decimal places (internal calculations retain
full precision). Gate status explains failed/unknown eligibility. A final score
remains blank when mandatory gates fail/are unknown or selected scoring inputs
are incomplete; blanks are not replaced with zero.

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
Calculate nine diagnostic domain scores, 0-100
              |
              v
Calculate comparison_preference_score when selected domains are complete
              |
              v
Check final eligibility:
  - Any mandatory failure -> no final score/rank
  - Any unknown gate or incomplete selected score/weight -> no final score/rank
  - All mandatory gates pass and scoring is complete -> final score
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

With the current equal domain weights, a complete aggregate is the average of all
nine domain scores. Missing selected inputs are not silently dropped or reweighted.
`habitability_score` and `final_recommendation_score` receive the same eligible value.
Final ranks sort scores descending; equal scores use assessment ID as the tie-break.
Undated assessments form a separate group from dated ones, and input row order is
preserved in the output. `--compact` changes only the exported columns to ID plus
domain scores, gate status and the final habitability score, not the calculations or gate decisions.

## Scoring behavior

The nine domains are radiation, thermal, solar illumination, dust, plasma/charging, UV, seismic, exosphere and communications geometry.

The active `config.yml` policy is **`assumption_NASA_values`**: project assumptions for testing NASA-site scenarios, **not official NASA values or safety limits**. All nine domains have complete preference bounds and equal domain weights of 1.0. One score-bearing metric per domain avoids weighting multiple related proxies as independent evidence. Other fields are either gate-only or context-only. These fictional mappings must not be used to interpret orbital/reference quantities as local hazard, dose, surface charging or real habitability.

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

Every bound, direction, plateau and gate above is an **assumption for exercising software**, not a NASA-certified environmental response. Equality passes. The sunlight and link gates require the supplied UTC pair. Final score is the equal-weight average of all nine complete domain scores only after all mandatory gates pass; otherwise it stays blank. Domain diagnostics can still be shown when final eligibility is blocked.

- Known mandatory failure dominates Unknown. Failed or Unknown mandatory gates prevent final scores/ranks.
- Missing values are not zero-filled by the runtime or silently reweighted.
- Higher/lower/target-range preferences normalize measurements; optional utility curves act after normalization.
- Domain scores are weighted metric utilities on 0-100. A final score requires complete selected domains and passing mandatory gates.
- `comparison_preference_score` is diagnostic, not an operational approval or replacement for the final score.
- Simple output shows diagnostic domain scores, gate status and the gate-qualified habitability score.

The script remains standalone: Python 3.10+, PyYAML, the selected YAML and one input CSV. It does not read source datasets, preparation scripts, notebooks or provenance sidecars at runtime.

## Current assumption-policy validation

The 30-row fixture evaluates to 15 Passed, 13 Failed and 2 Unknown, with 15 final ranks. Checked all ten gate boundaries, missing-data states, nine domain score ranges, contribution totals and isolated execution with the default input. Existing result files are not automatically refreshed by editing the YAML; rerun the command above to replace them.

Of 44 directly relevant existing tests, 41 pass. Three still require the previous unconfigured policy (null multipliers, one solar gate or its former metric placement); they conflict with the explicitly approved assumed-threshold policy and were left unchanged. No test files or input/output CSVs were changed for this policy update.
