# Existing-data environmental pipeline

**Start here: [LATEST_RESULTS.md](outputs/LATEST_RESULTS.md).** It points to the latest successful real-data product, not historical readiness reports or synthetic tests.

**Default run:** compare the **real EDA already available**. It does not load a mission/equipment template, run unavailable operational checks, request downloads or use the synthetic fixture. It exports only populated, usable data products. Unsupported measurements remain counted in coverage; they are not invented, scored or passed.

This is a limited environmental **context comparison**, not a claim that a site passes operational requirements. The default reuses the existing exploratory policy without inventing new weights/limits. Full Stage 3 equipment adequacy remains separate and incomplete.

**Main target:** [outline Stage 3](../../outline.md#stage-3--environmental-and-equipment-suitability-engine)—evaluate the intended mission against applicable site conditions, equipment capabilities and requirements, reporting adequacy, margins, failures and uncertainty. **Required Stage 3 gaps first, then original research P1 → P2 → P3.**

This remains a **rule-based environmental companion**, not a trained environmental CNN. The original terrain CNN is unchanged. Its notebook/configuration/verified-artifact workflow is preserved; `prototype2` supplies the eligibility → scoring → recommendations separation.

## Steps 4-5: scoped rules and current EDA handoff

The normal run now also consumes the pinned applicable Dar_033-039 results through `evidence_rules_manifest.json`. It adds **`evidence_context/EVIDENCE_DECISIONS.md`**: real conditions -> actual configured checks -> all-candidate explanations, supported by a scoped rule register, source hashes, evidence-use checks and 12 hazard-inference boundaries per candidate. [Step 4/5 scope and verification](../research/STEP_4_5_PROTOTYPE.md).

- The register distinguishes conditional sourced requirement families, historical references, planetary baseline, evidence-use guards and actual exploratory policy values/bounds/weights. It does not adopt numeric physical safety limits.
- Default scores, filters and top-k are unchanged. The new global/orbital/historical/ROI-center data is **not** promoted to candidate-specific measurements or new score factors.
- **Evidence-use Failed is not a failed physical site.** It means a proposed inference is unsupported. Candidate operational conclusions from those sources remain Unknown.
- Existing root candidate-product CSVs retain their populated/no-placeholder contract. The **separate nested evidence annex** intentionally preserves source N/A values and explicit Unknown inference limits; they must not be filled to make a clean table.
- `explained_context_checks.csv` includes signed distances from the exploratory comparison thresholds in each metric's existing units. These are **not equipment operating margins**. Historical Apollo headroom remains configuration-specific and is not an actual new-mission margin.
- Mission/equipment inputs remain optional. No download, fabricated equipment profile or synthetic fixture is needed. Synthetic mode does not load this real-data annex. Older custom configurations without `evidence_rules_manifest` keep their original behavior.

## Structure and actual inputs

| File / stage | Role |
| --- | --- |
| [Dar_028](Dar_028_environment_pipeline.ipynb) | Real EDA → environmental comparison → factor explanations → support → separate operational gaps. Synthetic scenario is OFF by default. |
| `environment_engine.py` | Verified EDA loading, stage orchestration, explained scoring/reporting. Existing `evaluate()` API remains compatible. |
| `stage3_assessment.py` | Focused configured operating-margin models and applicability/gating checks—not another downloader or CNN. |
| `evidence_rules.py`, `evidence_rules_manifest.json` | Scoped register compilation, verified new EDA, evidence-use checks and candidate explanations; independent of optional operational assessment. |
| `../research/environment_rule_register.json` | Traceable Step 4 classifications, sources, applicability, inputs and consequences; physical limits remain unadopted. |
| `environment_experiment.json` | Pins real EDA and selects the existing `comparison_policy`. Consumed outputs are hash-checked; supporting Stage 3 exports remain under `stage3_evidence/`. The legacy evidence-only policy is preserved for `--evidence-only`. |
| `mission_profile_template.json` | Explicit `--stage3` readiness contract only. Not loaded by the normal comparison. |
| `diagnostic_policy.json` | Existing exploratory visibility/slope comparison policy, reused by default. Not an operational requirement set or calibrated model. |
| `tests/` | Existing gate/score contracts plus Stage 3 model/applicability checks using explicit synthetic fixtures. |
| `sample_data/synthetic_10_candidates.csv` | Ten explicitly fictional candidates, equipment demands and expected outcomes for an end-to-end software check. |
| `outputs/` | All **new** pipeline exports, generated sample inputs and verification evidence; split by run kind. |

Current candidate input is **21 purposively selected Dar_020 components**, not the CNN's patch IDs or physically validated base footprints. Thermal phase summaries, static visibility and support are retained. ShadowCam/CPR and historical battery/soil/radiation references remain qualified context—not independent local scores. Decisions and measured reasons are in [the proposal](../purposal.md#3-what-to-recommend).

## Run from the repository root

```cmd
REM DEFAULT: real existing EDA -> environmental comparison and top-k
.\.venv\Scripts\python.exe "darrel stuff\Pipeline_Proto\environment_engine.py"

REM OPTIONAL: full intermediate evidence under audit/ (can contain missing values)
.\.venv\Scripts\python.exe "darrel stuff\Pipeline_Proto\environment_engine.py" --audit

REM OPTIONAL: explicitly inspect missing Stage 3 mission/equipment inputs
.\.venv\Scripts\python.exe "darrel stuff\Pipeline_Proto\environment_engine.py" --stage3

REM OPTIONAL legacy readiness-only view; no environmental scores
.\.venv\Scripts\python.exe "darrel stuff\Pipeline_Proto\environment_engine.py" --evidence-only

REM Ten synthetic cases through the same five margin models and ranking functions
.\.venv\Scripts\python.exe "darrel stuff\Pipeline_Proto\environment_engine.py" --sample

REM Once a documented profile/evidence exists (not provided with this project)
.\.venv\Scripts\python.exe "darrel stuff\Pipeline_Proto\environment_engine.py" --mission-profile "darrel stuff\data\mission_profile.json"
```

All new runs stay inside **`darrel stuff/Pipeline_Proto/outputs/`**:

| Subfolder | Data and purpose |
| --- | --- |
| `environment_comparison/<run_id>/` | **Default:** real existing EDA, all-candidate comparison, top-k and factor/support explanations. |
| `evidence_only/<run_id>/` | Explicit `--evidence-only` legacy readiness view; operational gaps stay Unknown. |
| `diagnostic/<run_id>/` | Real pinned EDA with explicitly illustrative visibility/slope rules and scores. |
| `synthetic_demo/<run_id>/` | Fictional ten-case verification, including generated `sample_inputs/` and its mission profile. |

The seed sample stays in **`Pipeline_Proto/sample_data/`**, not the preprocessing data folder. Real EDA inputs remain read-only under `darrel stuff/data`. Historical pipeline runs under `data/processed/env_cnn_prototype/` are preserved, not moved/deleted. No new root `data/`, GPU, package or background download is needed.

**Normal use requires only the first command.** Older folders may still contain the former Unknown/empty readiness exports; they are historical. `LATEST_RESULTS.md` is updated only after a successful real-data product run—not by operational-readiness or synthetic test runs.

## What the default comparison actually uses

| Available factor | Coverage in the current 21 examples | Use |
| --- | ---: | --- |
| Median sunlight visibility | 21 | Existing context filter ≥0.5 and declared preference weight 1. |
| Median Earth visibility | 21 | Existing context filter ≥0.5 and declared preference weight 1. |
| 90th-percentile slope | 21 | Existing context filter ≤8°. **Not another score factor**, to avoid adding a second terrain weight. |
| Fixed-common thermal phase min/max/span | 5 | Retained with coverage/scope; not silently added to a 21-candidate composite. |
| Mini-RF CPR context | 19 | Context only, not a local geotechnical score. |
| ShadowCam radiance context | 3 | Context only, not a temperature/safety score. |

These thresholds and equal weights already existed in `diagnostic_policy.json`; they are **illustrative comparison settings**, not newly sourced or approved equipment limits. Score = the declared weighted mean of the bounded solar/Earth utilities, only after the configured context filters pass. Equal complete scores use candidate ID for stable ties.

`feature_usage.csv` exposes what is scored, filtered or context-only. Missing a declared factor withholds the score; the program never inserts zero, invents a factor, or silently renormalizes weights. Candidate selection already used related proxies, so the ordering is **not independent validation**. The 21 examples are not yet spatially matched CNN patches.

## Separate Stage 3 assessment: what a mission profile must supply

- Explicit Moon body, timezone-aware start/stop, crew count (zero explicitly means uncrewed), activities and selected equipment configuration.
- A **declared complete** applicable requirement list with unique ID, model kind, mandatory Boolean, source/reason and settings. No mandatory checks means no automatic pass.
- `candidate_inputs[candidate_id][requirement_id]`: a local-data `input_file`, body/start/stop, observed/modelled `basis`, and `support: "candidate_validated"`.
- Power/contact inputs additionally need `terrain_aware: true` and `time_model: "piecewise_constant"`. Thermal evidence must identify `quantity: "component_response_temperature"`, not Diviner surface tbol.
- Optional `soft_preferences` follow the existing explicit metric/unit/scope/direction/bounds/weight contract. No automatically fitted/correlation-derived weights.

**Applicability/support and inventory completeness are supplied declarations with traceable evidence, not independent certification by this code.** Bad schemas, impossible numbers, missing configured files, interval gaps/overlap and unit mismatches raise errors. Absent profile/evidence remains Unknown.

| Model kind | Supplied evidence / settings | Output |
| --- | --- | --- |
| `consumable` | One CSV row: `rate_kg_per_crew_day, recovery_fraction, available_kg, reserve_kg`. Actual crew/duration from profile. | kg margin = stock − reserve − crew-days × adopted rate × unrecovered fraction. Not total ECLSS adequacy by itself. |
| `power` | Exact contiguous window: `start_utc, stop_utc, generation_W, load_W`. Settings: usable/initial battery Wh, reserve Wh, charge/discharge efficiency. | Chronological finite-capacity reserve/shortfall margin. Future sunlight cannot erase an earlier failure. |
| `thermal` | Exact-window response envelopes: interval start/stop, `minimum_component_K, maximum_component_K`. Settings: minimum/maximum operating K. | Minimum cold/hot response margin, K. Surface phase averages cannot substitute. |
| `communications` | Exact-window intervals and explicit Boolean `contact_available`; maximum permitted outage hours. | Permitted minus longest modelled outage, h. Sphere-horizon samples cannot pass. |
| `capacity_demand` | One row: `quantity, unit, capacity, demand, reserve`; settings must match quantity/unit. | Explicit capability/limit minus demand/reserve, e.g. a supplied applicable protection or load case. No implicit dose/soil conversion. |

No source table is silently adopted as mission equipment or requirements. NASA reference loads are available for sensitivity, not default stocks, reserves, crew size or operating limits.

## Outputs and score boundary

- **Open `RUN_SUMMARY.md` first.** It explains the run basis, status counts and every table's purpose. `output_catalog.csv` supplies titles, row counts and explicit empty-result reasons. CSV files keep standard column headers, not decorative title lines that break their schema.
- **`environmental_rankings.csv`**: only candidates with complete comparable scores (**14 current rows**); no empty score cells. **`environmental_top_k.csv`**: top five. Neither is an operational ranking.
- **`candidate_status.csv`**: all **21** input candidates accounted for. **`excluded_candidates.csv`**: the other **seven**, with reasons instead of empty/fake scores.
- **`soft_preference_results.csv`**: **28** actual solar/Earth utility contributions for ranked candidates. **`hard_rule_results.csv`**: **63** supported context-filter comparisons.
- **`environment_evidence.csv`**: **100** existing qualified values with units, scope, support and source. The other **68** candidate/metric entries are unsupported; their coverage counts remain explicit, not filled with values.
- **`feature_usage.csv`**: coverage counts, filter/score participation, units/scope and why other real measurements are retained only as context.
- **`thermal_profiles.csv`**: **five** complete common-phase minimum/maximum/span profiles in K. These use existing thermal EDA, not assumed equipment temperatures or new score weights.
- An unavailable optional product is marked `omitted_empty` in the catalog, **not written as a header-only CSV**. A run with no rankable candidates still produces candidate-status/exclusion/coverage results and explicitly explains why.
- `report.json` and `provenance.json` retain configuration, source checksums and output lineage. `--audit` additionally retains full intermediate tables under `audit/`.

### Explicit operational mode only

`--stage3`, `--evidence-only`, `--mission-profile`, and the separately labelled synthetic test retain the operational/readiness exports: `candidate_assessments.csv`, `candidate_readiness.csv`, `requirement_readiness.csv`, `stage3_operational_checks.csv`, `stage3_preference_details.csv`, `stage3_top_k.csv` and their context/audit files. Unknowns and empty rankings can be correct **in those requested modes**. They are no longer default product outputs.

A known mandatory failure dominates Unknown; missing soft data withholds the aggregate rather than renormalizing weights. Stable ties use candidate ID. Diagnostic top-k is explicitly separate: **14 proxy passes / seven failures do not mean 14 operationally eligible bases**.

No equipment assessment is executed by the normal run. If you explicitly request Stage 3 with the current blank profile, all 21 operational states remain Unknown and no operational top-k is issued. Those mandatory checks have not been bypassed or converted into passes.

### Why the separate operational report remains Unknown

1. The optional Stage 3 template has no mission dates, crew, activities, selected equipment or complete applicable requirement inventory. Its operational checks remain Unknown when requested. It is not a dependency of the normal comparison.
2. Downloaded surface/orbital measurements do **not** supply equipment response, stocks, loads, reserves or approved limits. Existing measured context is useful but cannot make those mandatory checks pass.
3. The normal run does not export operational preference/readiness CSVs at all. Opting into an operational assessment can still produce Unknowns and empty operational rankings; that is a truthful result for that different question.

### What demonstrably works

| Experiment | Input | Working outcome |
| --- | --- | --- |
| **Default environmental comparison** | 21 real EDA components, 168 qualified metric rows | **14 scored context comparisons, 7 configured-filter exclusions, top 5**, with factor values/utilities and coverage explanations. |
| Explicit operational readiness only | Same real candidates; no mission/equipment profile | **210** readiness/check records; all 21 operationally Unknown. Not run by the default product. |
| Optional synthetic software test | **10 fictional rows**, only when explicitly requested | **2 pass, 6 fail, 2 Unknown** across five margin models; not used in the default run or notebook Run All. |

The sample covers insufficient stock, exhausted power, excessive cold, a long outage, inadequate support-load capacity, missing power, inappropriate surface-temperature evidence and failure dominating an additional Unknown. `sample_verification.csv` compares expected and actual outcomes **after** assessment; expected labels are never used as rule inputs. A complete fixture requirement inventory is not a complete real mission inventory.

Dar_028 now runs the real-data comparison only by default. Its synthetic test flag is explicitly False. The original 34 pipeline tests remain unchanged; additional available-data comparison tests cover independence from blank equipment inputs, score comparability and context-only factors. The Stage 3 export retains `stage3_status` as well as `gate_status`. This validates software behaviour, not lunar operational safety.

Open the [latest product](outputs/LATEST_RESULTS.md); the generated [verification summary](outputs/verification/VERIFICATION.md) records the checked run. Synthetic tests remain explicitly tagged and never replace the latest real-data product.

[Historical Stage 3 verification](../data/verification/golden_stage3_final/verification.json) retains the earlier Dar_028–031 execution and 222-test audit. New verification/output locations are described above; historical runs are not rewritten.

## Current Steps 4-5 verification

[Verification record](outputs/verification/step45/verification.json), [completion audit](outputs/verification/step45/completion_audit.json): **63 pipeline tests passed** (46 unchanged plus 17 new); Dar_028 executed eight code cells with zero saved errors; default/optional/legacy CLI modes checked. All nine original candidate-product CSVs are byte-identical to the pre-change real-data baseline. The new annex provides 27 compiled rule rows, eight evidence-use checks, 17 source tables, 21 explanation cards and 252 source-inference boundaries without adding score factors or operational passes. Mission/equipment remains optional; broader workflow Step 6 is deferred.

## Evidence and remaining work

The original-notebook re-check also executes Dar_032 (native maps/support) and the **existing local notebook 13** (strict/full-source terrain views), rather than duplicating it. Their pinned summaries are consumed under `stage3_evidence/native_support/` and `stage3_evidence/terrain_views/` as quality/context evidence, not new scores or requirement passes. See the [dataset/reuse table](../EDA/EDA_Notes.md#original-notebook-reuse-and-datasets--re-check-8-november-2026) and [executed results](../EDA/EDA_Results.md#15-original-notebook-reuse--executed-8-november-2026). No dated terrain-aware mission history generator was found in the reviewed original code. [Latest reuse verification](../data/verification/source_port_review/final_verification.json).

[Dar_029–031 results](../EDA/EDA_Results.md#14-golden-stage-3-revamp) and the [decision table](../purposal.md) control feature use. Needed next: actual mission/equipment/requirement inputs, applicable terrain-aware temporal and response evidence, and physical candidate/CNN-patch association. A new trained CNN would require an appropriate target, aligned data and independent validation; it is not created by adding optional environmental layers.
