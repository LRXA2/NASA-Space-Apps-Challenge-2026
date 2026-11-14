# Moon environmental comparison prototype

**Flow:** lunar conditions -> evidence-backed rules -> candidate results.

The default run uses existing real EDA without a mission/equipment template, downloads, CNN or synthetic fixture. It is an explainable **environmental context comparison**, not demonstrated mission feasibility. [Workflow](../todo_workflow.md), [sources](../research/Research_Notes.md), [findings](../EDA/EDA_Notes.md) and [feature decisions](../purposal.md) define scope.

## Run

From the repository root in PowerShell:

```powershell
# Default real-data comparison
.\.venv\Scripts\python.exe "env_algo_task\Pipeline_Proto\environment_engine.py"

# Optional intermediate tables
.\.venv\Scripts\python.exe "env_algo_task\Pipeline_Proto\environment_engine.py" --audit

# Optional operational readiness using the explicitly blank input contract
.\.venv\Scripts\python.exe "env_algo_task\Pipeline_Proto\environment_engine.py" --stage3

# Optional actual mission profile; replace PATH with a documented profile
.\.venv\Scripts\python.exe "env_algo_task\Pipeline_Proto\environment_engine.py" --mission-profile PATH

# Optional, explicitly fictional software test; never a real recommendation
.\.venv\Scripts\python.exe "env_algo_task\Pipeline_Proto\environment_engine.py" --sample
```

`--evidence-only` retains the earlier readiness/evidence view; `--policy PATH` explicitly selects another policy. Normal execution does not load `mission_profile_template.json`. Dar_028 runs real data with its synthetic flag False.

## Inputs and modules

| File | Role |
| --- | --- |
| [Dar_028](Dar_028_environment_pipeline.ipynb) | Executable existing-data demonstration. |
| `environment_engine.py` | Verified loading, assessment orchestration, comparisons and exports. |
| `environment_experiment.json` | Pins accepted EDA outputs/configuration; source/output hashes are checked. |
| `diagnostic_policy.json` | Existing illustrative filters/preferences, not approved operational limits. |
| `helpers/evidence_rules.py`, `evidence_rules_manifest.json` | Scoped rule register, source tables, evidence-use checks and candidate explanations. |
| `helpers/science_comparison.py`, `../research/lunar_science_models.json` | Source-backed indicators, unweighted preference views, scope guards and common reference cases. |
| `helpers/temporal_context.py` | Validates monthly/quarterly EDA handoffs and writes historical time-context explanations; no added ranking weights. |
| `../research/environment_rule_register.json` | Traceable classifications, applicability, required inputs and consequences. |
| `helpers/stage3_assessment.py`, `mission_profile_template.json` | Separate opt-in capability/demand models and input contract. |
| `sample_data/`, `tests/` | Fictional verification inputs and protected software contracts. |
| `outputs/` | Generated comparison/readiness/test runs and provenance; source data is not moved here. |

EDA helper paths: [shared utilities/readers](../EDA/shared/) and [Stage 3 scripts/configs](../EDA/Moon/Stage3_Requirements/). Existing import names, notebook locations and the pipeline commands above are unchanged.

The pipeline's three support modules are grouped in [helpers/](helpers/). Its entry script, configs, notebook, tests and output locations remain unchanged. Workstream ignore rules are centralized in [../.gitignore](../.gitignore).

The candidate input is **21 purposively selected Dar_020 components**, not validated base footprints. Qualified source/cohort/spatial support is retained. Global/orbital, historical and region-center references stay context-only.

## Science-based environmental preferences

The default now also opens [science comparison](outputs/LATEST_RESULTS.md), based on [Dar_042 and its source contract](../research/lunar_science_models.json). It adds **six pinned EDA science tables** to the 39-table evidence bundle (45 total), while retaining the original baseline score/API/products.

- **Radiation:** candidate visible sky divided by **4*pi**, an explicitly geometric primary-particle openness indicator, not transported dose or shielding efficiency. Values above a 2*pi hemisphere are not clipped.
- **UV:** long-period direct-Sun visibility opportunity, not measured irradiance or UV dose. It shares the solar input and is not counted twice with sunlight as independent weighted evidence.
- **Plasma:** published charging regimes plus candidate sunlight/shadow/PSR context. Local voltage, discharge risk and operational protection remain Unknown; dark/plasma-poor is not automatically safer.
- **Thermal:** complete fixed-common phase-product median profiles, not equipment temperatures or instantaneous extremes.

Under `evidence_context/science/`, `science_preference_fronts.csv` and `science_preference_details.csv` show unweighted multi-objective fronts and lower/higher per-factor positions. These are relative context preferences, not safety ranks. Current exposure view: 14 comparable candidates and two first-front options. The thermal extension has one complete eligible candidate and 13 without comparable thermal data, so **no thermal winner is issued**. Seven candidates still fail the original context filters.

`SCIENCE_COMPARISON.md` explains the source-backed quantities, shared inputs, assumptions and options. `radiation_reference_scenarios.csv` retains 96 common published cases, not site-specific doses. `science_operational_requirements.csv` preserves 63 Unknown radiation/UV/plasma requirement rows. Other candidate sets receive explicit Unknown science indicators unless an exact associated profile exists; no nearest-site or global-value substitution.

The project-chosen Pareto directions are explicit in the model JSON, not NASA weights. A candidate dominates another only when no worse on every included objective and strictly better on at least one. Front 1 is not operational approval. Both views use the **live** context filters, including policy overrides; missing inputs are never imputed or dropped to produce a score.

## Default baseline results

Start with [LATEST_RESULTS.md](outputs/LATEST_RESULTS.md), which points to a successful real-data product. Each run includes a readable summary, output catalog, report and provenance.

| Product | Verified baseline result |
| --- | --- |
| `environmental_rankings.csv`, `environmental_top_k.csv` | 14 comparable context-ranked candidates; top five. Not operationally eligible sites. |
| `candidate_status.csv`, `excluded_candidates.csv` | All 21 inputs accounted for; seven configured-filter exclusions with reasons. |
| `hard_rule_results.csv` | 63 context-filter comparisons, not physical safety verdicts. |
| `soft_preference_results.csv` | 28 solar/Earth utility contributions; no missing-score renormalization. |
| `environment_evidence.csv`, `feature_usage.csv` | 100 qualified values; 68 unsupported candidate/metric entries counted, not fabricated or scored. |
| `thermal_profiles.csv` | Five full common-phase profiles in K, not component operating temperatures. |

The policy filters median solar/Earth visibility each >=0.5 and slope q90 <=8 degrees, then scores solar/Earth with equal weights of 1. These are **illustrative settings**, not NASA operational limits. Unsupported factors do not silently acquire a score. Empty optional products are catalogued `omitted_empty`, not written as header-only CSVs. No rankable candidates still produces truthful statuses/exclusions/coverage.

## Evidence and explanations

The separate `evidence_context/` annex includes:

- `rule_register.csv`: 29 scoped rule/evidence entries plus five actual policy entries (34 compiled rows).
- `source_catalog.csv` and `sources/`: 46 pinned EDA source tables with original units, scope and hashes, plus six science tables (**52 context tables total**). The latest seven temporal tables extend, not replace, the earlier bundle; repeated summaries of the same observations are not independent evidence.
- `evidence_use_checks.csv`: 14 checks about whether an inference is supported. **Evidence-use Failed is not a failed physical site.**
- `explained_context_checks.csv`: values, operators, thresholds and signed distances. These are exploratory threshold distances, **not equipment operating margins**.
- `candidate_inference_limits.csv`: 252 boundaries (12 hazard categories x 21 components), with operational conclusions Unknown.
- `EVIDENCE_DECISIONS.md`: all 21 candidate cards with values, exclusions, scores and inference limits.
- `TEMPORAL_CONTEXT.md`: historical monthly/quarterly radiation, UV and plasma contrasts, actual coverage and inference boundaries.

The annex intentionally preserves source N/A and Unknown, separately from the populated default candidate CSV contract. More radiation or thermal context does not become a candidate measurement or new weight by association. The new group exports dated thermal support/flags, regional support, instrument-separated file availability, job statuses and acquisition holds; availability remains distinct from the new row-level radiation analysis.

## Historical time-period extension

[Dar_043](../EDA/Moon/Stage3_Requirements/Dar_043_temporal_environment.ipynb) is executed, not just a notebook template. The manifest explicitly pins its accepted full run. The pipeline consumes seven tables: series catalog, daily context, monthly context, quarterly context, temporal support, cross-dataset span overlap and plasma file/cadence diagnostics. It checks source hashes, calendar windows, series identity, daily-to-period statistics and support totals before export.

- **101 series / 2,352 year-month rows / 856 quarter rows**; instruments, channels, versions, UV modes and plasma SSE-position strata remain distinct.
- **E14:** calendar/coverage handling passes only as an evidence-use check. **E15:** using non-overlapping historical UV and recent plasma/radiation for simultaneous correlation fails. **E16:** spacecraft plasma does not resolve local charging/hardware protection, which remains Unknown.
- Monthly/quarterly medians describe daily statistics, not pooled raw records. Partial periods, missing observations, valid days and GOES qualified seconds remain explicit. Plasma cadence is measured, not assumed from nominal metadata; its sample counts are not elapsed valid time.
- These are UTC calendar periods, **not lunar seasons or future mission-window forecasts**. No new hard safety threshold, soft weight, local UV/dose/voltage or operational pass is invented. The existing context rankings and science fronts are unchanged.

Start with `outputs/LATEST_RESULTS.md` -> **Historical time-period context**. Reproduce the EDA using `../EDA/Moon/Stage3_Requirements/stage3_temporal_eda.py` or Dar_043; the existing pipeline commands above remain unchanged. [Findings](../EDA/EDA_Notes.md#monthly-and-quarterly-comparisons--dar_043) | [Verification](../data/verification/latest_temporal_environment.txt).

## Optional operational assessment

Document body/time window, crew/tasks, equipment configuration, applicable requirement inventory, stocks/reserves, loads, chronological generation/storage, component response, contacts and relevant hazard protection. Each selected check needs units, source, applicability and a qualified model/input domain.

Existing models cover configured consumable stock, chronological power/storage, thermal operating windows, communications outages and load capacity where inputs suffice. A known mandatory failure dominates Unknown; all mandatory checks must pass before operational preferences/ranking. Missing soft evidence withholds the aggregate rather than reweighting other factors. Ties use candidate ID.

The blank profile produces **21 Unknown operational states and no operational top-k**. The optional ten-row fictional fixture produces **2 pass / 6 fail / 2 Unknown**; expected labels are checked only after assessment. Software fixture success is not lunar qualification.

## Current radiation/thermal handoff

[Dar_041 findings](../EDA/EDA_Notes.md#radiation) feed the annex: 1,091 CRaTER secondary dates, 524 GOES-16 dates, 791 GOES-19 dates, bounded samples from 33 primary files and 812 checked thermal queries. E10/E11/E12 enforce temporal support, instrument identity and sample scope. These checks do not change existing filters/weights, candidate metrics or operational eligibility. Missing thermal/primary qualification and local transported radiation dose remain explicit holds.

## Verification

**Time-period extension, 10 November 2026:** **191 EDA + 100 pipeline tests passed**. Dar_043 executed all three code cells and Dar_028 all ten, without saved errors. Independent raw UV/CDF checks agree with the exports; all nine prior candidate CSVs are byte-identical. The default now includes 52 context tables and 14 evidence-use checks, while the blank mission profile remains 21 Unknown with no operational top-k. Existing tests, 26 original rule objects and prior source pins were preserved. [Accepted runs and checks](../data/verification/latest_temporal_environment.txt).

**10 November 2026 EDA alignment check:** all **66 handoff tables** across default and optional audit/operational modes match the latest completed full EDA runs in values and structure. All 48 saved EDA notebooks have executed code cells and no saved errors, including the formerly uncredited legacy native-support notebook; this is execution evidence, not physical qualification.

**88 pipeline tests passed.** Fresh default, latest-rerun audit, blank operational-profile and all-excluded policy checks passed. The nine existing candidate-product CSVs remain byte-identical to the prior default run: 14 context-ranked / seven excluded, two science first-front options, no thermal winner, 63 Unknown science operational requirements and 21 Unknown candidates in blank-profile mode. Explicit production source pins, filters, weights and science-model definitions remain unchanged because the rerun data agrees; no automatic latest-run substitution was introduced. [Current alignment checks and accepted runs](../data/verification/latest_step45_eda_alignment.txt).

Earlier radiation extension: **116 targeted tests passed** (42 Step 3 EDA, 74 pipeline); Dar_041 executed five code cells and Dar_028 eight, both without saved errors. All nine candidate-product CSVs remain byte-identical to the earlier baseline; explicit blank-profile mode still returns 21 operational Unknown and no operational top-k. The late folder revisit found no new/changed job statuses beyond the selected snapshot. [Verification index](../data/verification/latest_radiation_step345.txt).

[Step 4/5 verification](outputs/verification/step45/verification.json) and [completion audit](outputs/verification/step45/completion_audit.json) record 63 passing pipeline tests (46 protected existing plus 17 added), eight executed Dar_028 code cells with no saved errors, checked CLI modes, 49 input/36 output hashes and all nine prior candidate products byte-identical. That is the completed baseline milestone, not a claim that every future configuration has been validated.

Radiation-extension checks and accepted runs are indexed by `../data/verification/latest_radiation_step345.txt`; the latest alignment recheck is linked above. Earlier documentation/download checks remain recoverable through `../data/verification/latest_docs_download_review.txt`. Historical run reports and provenance are preserved; the maintained `LATEST_RESULTS.md` pointer advances to the new real-data run. Updated source-document hashes belong to a new run, not retroactive edits to old manifests.

The science extension passed **139 targeted tests** (88 pipeline, nine science EDA, 42 retained Step 3 EDA). Dar_042 executed three code cells; Dar_028 executed nine, preserving its original eight cells and adding one science demonstration.

The science-layer verification index is `../data/verification/latest_lunar_science_layers.txt`. It records current targeted tests, source/output hashes, the executed notebooks and preservation of all nine original candidate-product CSVs. Historical runs remain unchanged; the maintained latest pointer advances.

## Remaining boundary

Steps 1-5 provide a bounded demonstration. Actual mission/equipment/limits and qualified local response remain optional inputs for this demo and necessary before operational suitability. Severe applicable hazards cannot be traded away by preferences. Broader Step 6 engineering/independent validation is deferred. No CNN association or trained model is part of this workstream.
