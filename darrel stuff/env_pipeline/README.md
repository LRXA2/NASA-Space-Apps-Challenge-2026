# Moon environmental CSV pipeline

**Implemented: 11 November 2026.** Standalone environmental-only Step 5 software. The scientific scoring policy is **not yet calibrated or adopted**. The existing [Pipeline_Proto](../Pipeline_Proto/README.md) remains unchanged.

**One CSV row per site/time window -> `run_pipeline.py` -> results CSV with domain scores, hard status, final recommendation score and rank.** No CNN, equipment, crew or Earth-visibility scoring. No downloads, automatic local-data inference or hidden missing-value substitution.

## Run

From the repository root, using the existing environment (no new dependencies):

```powershell
# Fictional six-row software demo; NOT lunar recommendations
.\.venv\Scripts\python.exe -B "darrel stuff/env_pipeline/run_pipeline.py" `
  --input "darrel stuff/env_pipeline/examples/sites.csv" `
  --policy "darrel stuff/env_pipeline/examples/demo_policy.json" `
  --output "darrel stuff/env_pipeline/outputs/my_demo/results.csv"

# Your environmental CSV; default policy deliberately leaves screening Unknown
.\.venv\Scripts\python.exe -B "darrel stuff/env_pipeline/run_pipeline.py" `
  --input "sites.csv" `
  --output "darrel stuff/env_pipeline/outputs/my_assessment/results.csv"

# Explicit project-configured policy
.\.venv\Scripts\python.exe -B "darrel stuff/env_pipeline/run_pipeline.py" `
  --input "sites.csv" --policy "my_policy.json" `
  --output "darrel stuff/env_pipeline/outputs/my_configured_run/results.csv"
```

Choose a new output path per run. Existing outputs are protected unless `--overwrite` is explicitly supplied; inputs, policy, evidence and source code cannot be overwritten even with that flag. Individual files are written atomically; the final provenance JSON marks a completed export, not an all-files transaction.

## Files

| File | Purpose |
| --- | --- |
| [run_pipeline.py](run_pipeline.py) | CSV validation, evidence checks, gates, utilities, domain aggregation, ranking and audit exports. |
| [environmental_policy.json](environmental_policy.json) | Unconfigured Moon-only metric registry and priority labels. No numerical limits, weights or normalization invented. |
| [input_template.csv](input_template.csv) | Header-only wide CSV template; add your assessment rows. |
| [examples/sites.csv](examples/sites.csv) | Fictional pass/fail/Unknown/missing-soft/tie/second-period cases. |
| [examples/evidence.json](examples/evidence.json) | Fictional per-row, per-metric evidence metadata. |
| [examples/demo_policy.json](examples/demo_policy.json) | Arbitrary two-domain test policy; not a scientific default. |
| [tests/test_run_pipeline.py](tests/test_run_pipeline.py) | Targeted software tests. |
| `outputs/` | Generated results and local verification; ignored through the central `darrel stuff/.gitignore`. |

## Input: `sites.csv`

Rows contain **raw environmental features, not precomputed scores**. The user-facing input is a CSV; the evidence sidecar supplies metadata that cannot safely fit into a bare number.

Required columns:

| Column | Meaning |
| --- | --- |
| `id` | Unique assessment-row ID. |
| `candidate_id` | Site/footprint identity, also matched in the supplied evidence metadata. The same candidate may have several rows with different periods/IDs. Geometry must be established upstream; this script does not independently resolve a footprint. |
| `start_utc`, `stop_utc` | Timezone-aware requested period, inclusive start/exclusive stop. |
| `evidence_ref` | Path to an evidence JSON, relative to the input CSV or absolute. Blank metadata means Unknown, never Passed. An explicitly named missing file is an error. |

Optional measurement columns are declared by the selected policy. Missing columns and blank cells remain missing evidence. Duplicate IDs/headers, ragged CSV rows, non-finite/malformed measurements, incompatible units and unregistered columns are explicit errors.

Default registry:

| Domain / priority | Input columns | Units / support |
| --- | --- | --- |
| Radiation / Highest | `rad_dose_rate_uGy_h` | Absorbed dose rate, uGy/h; exact requested window. Not crew effective dose. |
| UV / Medium | `uv_fuv_irradiance_W_m2` | 115-180 nm irradiance, W/m2; exact window. |
| Solar/illumination / High | `solar_visibility_median`, `longest_darkness_h` | Spatial median visibility fraction (static); longest continuous darkness in h (window). Sampled blocked spans cannot silently become continuous darkness. |
| Terrain / High | `slope_q90_deg` | Spatial 90th-percentile slope, degrees; static. |
| Thermal / Highest | `surface_temp_min_K`, `surface_temp_max_K` | Surface-temperature extrema, K; window, not equipment response. |
| Plasma/charging / Medium | `surface_potential_abs_p95_V` | 95th-percentile absolute surface potential, V; window, not spacecraft potential. |
| Dust / Medium | `dust_deposition_mg_m2_day` | Mean surface deposition, mg/m2/day; window, not detector counts/current. |
| Seismic / Evidence-dependent | `peak_ground_accel_m_s2` | Qualified peak ground acceleration, m/s2; window. |
| Exosphere / Context initially | `surface_He_density_cm3` | Mean surface helium number density, 1/cm3; window, not orbital density copied to the ground. |

These quantities are a **schema**, not a claim that our current datasets provide every field. A custom policy can register different well-defined metrics without relabeling counts as dose, orbital context as local data, or surface brightness as irradiance. Priority labels are not numeric weights and are not NASA-prescribed rankings.

CSV example excerpt, **fictional**:

```csv
id,candidate_id,start_utc,stop_utc,evidence_ref,solar_visibility_median,slope_q90_deg
A_pass,fictional_site_A_pass,2023-06-01T00:00:00Z,2023-07-01T00:00:00Z,evidence.json,0.8,2
```

### Evidence JSON

One sidecar can serve all CSV rows. Its `rows` object maps assessment IDs to metric IDs. For example, this excerpt supplies one fictional static metric:

```json
{
  "schema": 1,
  "rows": {
    "A_pass": {
      "solar_visibility_median": {
        "body": "Moon",
        "candidate_id": "fictional_site_A_pass",
        "scope": "candidate",
        "basis": "synthetic",
        "quality": "qualified",
        "unit": "fraction",
        "quantity": "spatial_median_sun_visibility",
        "temporal_support": "static",
        "support_count": 1,
        "source": "Fictional software fixture, not observed Moon data"
      }
    }
  }
}
```

Real policies accept `basis: observed` or `modeled`; **synthetic is accepted only in `synthetic_demo` mode**. Each numeric feature needs matching quantity/units, a nonempty source, a positive integer support count, a qualifying quality declaration and this Moon candidate's association. Window-supported evidence also needs matching `start_utc` and `stop_utc`. Static features do not become chronological histories merely because the row selects dates.

Global/regional/orbital evidence stays Unknown for local scoring; wrong scope is not a physical site failure. Supplied metadata is checked, **not independently scientifically certified**. Source statements alone do not validate a response model. Provenance hashes the input CSV, policy, evidence JSON, engine/helper source and generated CSVs; it does not independently reread every upstream dataset named inside a source statement.

## Policy, priorities and hard gates

The default `environmental_policy.json` deliberately has no mandatory limits, no utilities and no numeric weights. All domains are declared, with scoring unresolved. Thus its result is **Unknown with blank aggregate scores**, not a safe-site ranking. The registry is not a calibrated nine-domain algorithm.

To configure a real comparison, explicitly select `mode: exploratory` or `environmental`, define applicable mandatory rules, and configure the selected domains. Each hard rule needs a metric, `ge`/`le` operator, limit, rationale and authority/source. A null limit remains Unknown. Declare non-scored domains with `scored: false` and no preferences consistently across every candidate; do not drop missing domains selectively.

- Any mandatory Failed -> **Failed**.
- Otherwise any mandatory Unknown, or no configured mandatory rules -> **Unknown**.
- All selected mandatory rules Passed -> **Passed**.
- Only Passed candidates with complete selected soft inputs receive aggregate scores/ranks.
- Evidence-use rejection is not proof that the physical site fails.
- Thresholds are project environmental screens, not universal operational safety limits. The largest value in a dataset does not automatically define a hazardous threshold.

Radiation/thermal have the highest planning priority; illumination/terrain follow; dust/charging/UV remain important; seismic priority depends on applicable evidence; exosphere starts as context. **Any domain can carry an applicable mandatory constraint regardless of this ordering.** Weight is not hazard severity. A high-importance hazard with no local estimate remains Unknown rather than acquiring a fabricated number.

## Scoring mathematics

For a supported metric `x` and explicit utility bounds `L < U`:

```text
higher preferred: u = clip((x - L) / (U - L), 0, 1)
lower preferred:  u = 1 - clip((x - L) / (U - L), 0, 1)
```

`target_range` is also supported: utility is 1 between `preferred_lower` and `preferred_upper`, declines linearly to 0 at `lower`/`upper`, and is clipped outside. Require `lower < preferred_lower <= preferred_upper < upper`. Do not assume a monotonic plasma/exosphere benefit.

```text
domain_score[k] = 100 * sum(metric_weight[k,j] * utility[k,j])
                        / sum(metric_weight[k,j])

habitability_score = sum(domain_weight[k] * domain_score[k])
                     / sum(domain_weight[k])

final_rec_score = habitability_score, only when mandatory gates Passed
                  and every selected domain is complete; otherwise blank.
```

- `habitability_score` is the requested label for **environmental preference**, not demonstrated habitability or safety probability. It too is withheld when gates do not pass.
- `final_rec_score` is the ranking-facing copy, not a second independent judgment or another average of the same inputs.
- Domain weights and metric weights must be positive JSON numbers; unresolved domain weights may be null and withhold the aggregate. Metric preferences need bounds, direction, weight, rationale and source.
- Missing selected soft evidence withholds the aggregate; no zero filling or weight redistribution.
- Related proxies must share `evidence_family`. The validator rejects repeatedly scored families, including duplicated sunlight proxies. Correct family declarations and physical dependencies still require scientific review.
- Individual supported domain preferences may be shown diagnostically even when another gate blocks the final score.
- Rank descending score within **identical UTC periods under this policy**, breaking ties by assessment ID. Different months/years are not silently pooled into one site ranking. Input row order is preserved.

Time is not a weighted domain. This scorer evaluates already prepared period features; it **does not yet compute monthly/quarterly aggregates from raw observations**. Use the existing EDA temporal summaries upstream and preserve gaps, cadence, extremes, censoring and calendar labels. Calendar seasons are not lunar climate seasons.

## Outputs

For `--output results.csv`, the script writes:

| File | Contents |
| --- | --- |
| `results.csv` | Every input assessment, nine domain scores/states, `habitability_score`, hard status, `final_rec_score`, rank, scope, coverage and reasons. |
| `results_hard_gates.csv` | Each mandatory comparison, actual value, threshold/source and Passed/Failed/Unknown. |
| `results_domain_preferences.csv` | Selected metric utilities, weights and evidence support. |
| `results_environmental_evidence.csv` | All registered metric observations, units, scope, basis, source and support/Unknown reason. |
| `results_provenance.json` | Completion record, mode, input/output hashes, policy snapshot and status totals. |

Main domain fields: `rad_score`, `uv_score`, `solar_illumination_score`, `terrain_score`, `thermal_score`, `plasma_charging_score`, `dust_score`, `seismic_score`, `exosphere_score`. Each has a matching `_status`: `Scored`, `Unknown` or `Context_only`. Scores are 0-100, higher meaning preferred under the policy, not higher hazard. Blank is not zero. Coverage is supported/required distinct configured metrics, not a safety confidence estimate.

### Executed verification

The fictional demo uses only solar visibility and terrain with equal weights and an arbitrary slope gate. This is **not** the default or a nine-domain lunar scoring claim:

```csv
id,terrain_score,solar_illumination_score,habitability_score,hard_gate_status,final_rec_score,rank
A_pass,80,80,80,Passed,80,1
B_fail,10,90,,Failed,,
C_unknown,,70,,Unknown,,
D_missing_soft,70,,,Passed,,
E_other_period,80,80,80,Passed,80,1
F_tie,80,80,80,Passed,80,2
```

The original small run is saved under `outputs/demo/`. A separate bounded check under `outputs/existing_eda/` exported the **21 existing candidates' static solar/slope features** from two hash-verified accepted EDA tables. All 21 correctly remain Unknown/unranked under the unconfigured real policy. It did not manufacture local radiation/UV/charging or period-specific illumination. The preparation provenance records those source tables.

Run local tests:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s "darrel stuff/env_pipeline/tests" -p "test_*.py" -v
```

## Existing evidence and remaining scientific work

- [EDA Notes](../EDA/EDA_Notes.md): eleven executed subject studies and existing-EDA checks.
- [Research Notes](../research/Research_Notes.md): sources, applicability and inference boundaries.
- [Workflow](../todo_workflow.md): Stage 3-4 completion and separate Step 5 work.
- The 64 Stage 4 proposals remain **unadopted**: 15 conditional hard, 11 conditional soft and 38 evidence guards. They are not automatically active rules, numeric weights or independent observations.
- Raw additive downloads remain at `D:\projects\NASA Dataset`; existing local data and accepted EDA remain under `darrel stuff/data/`. No datasets were moved.

Next scientific step: map the supported site/time quantities, define defensible utilities and applicable limits, agree explicit weights, and check ranking sensitivity. Existing evidence does not yet support a qualified nine-domain local score for every candidate. Mission/equipment qualification remains outside this environmental-only pipeline.
