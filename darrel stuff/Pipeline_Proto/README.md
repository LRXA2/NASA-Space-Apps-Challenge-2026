# Required Stage 3 pipeline

**Main target:** [outline Stage 3](../../outline.md#stage-3--environmental-and-equipment-suitability-engine)—evaluate the intended mission against applicable site conditions, equipment capabilities and requirements, reporting adequacy, margins, failures and uncertainty. **Required Stage 3 gaps first, then original research P1 → P2 → P3.**

This remains a **rule-based environmental companion**, not a trained environmental CNN. The original terrain CNN is unchanged. Its notebook/configuration/verified-artifact workflow is preserved; `prototype2` supplies the eligibility → scoring → recommendations separation.

## Structure and actual inputs

| File / stage | Role |
| --- | --- |
| [Dar_028](Dar_028_environment_pipeline.ipynb) | Readiness → baseline → explicit diagnostic experiment → inspection. Run All with the project kernel. |
| `environment_engine.py` | Verified EDA loading, stage orchestration, explained scoring/reporting. Existing `evaluate()` API remains compatible. |
| `stage3_assessment.py` | Focused configured operating-margin models and applicability/gating checks—not another downloader or CNN. |
| `environment_experiment.json` | Pins Dar_020/026/027 candidate evidence **and Dar_029–031 required Stage 3 audit, time/terrain and reference exports**. Consumed outputs are hash-checked and retained under `stage3_evidence/`. |
| `mission_profile_template.json` | Blank mission/crew/equipment/requirements contract. Null fields are intentionally missing, not defaults. |
| `diagnostic_policy.json` | Unapproved visibility/slope proxy demonstration only. Not an operational requirement set. |
| `tests/` | Existing gate/score contracts plus Stage 3 model/applicability checks using explicit synthetic fixtures. |

Current candidate input is **21 purposively selected Dar_020 components**, not the CNN's patch IDs or physically validated base footprints. Thermal phase summaries, static visibility and support are retained. ShadowCam/CPR and historical battery/soil/radiation references remain qualified context—not independent local scores. Decisions and measured reasons are in [the proposal](../purposal.md#3-what-to-recommend).

## Run from the repository root

```cmd
REM Blank-profile assessment: explicit required Stage 3 Unknowns, no operational ranks
.\.venv\Scripts\python.exe "darrel stuff\Pipeline_Proto\environment_engine.py"

REM Separate illustrative proxy experiment; does NOT pass Stage 3
.\.venv\Scripts\python.exe "darrel stuff\Pipeline_Proto\environment_engine.py" --policy "darrel stuff\Pipeline_Proto\diagnostic_policy.json"

REM Once a documented profile/evidence exists (not provided with this project)
.\.venv\Scripts\python.exe "darrel stuff\Pipeline_Proto\environment_engine.py" --mission-profile "darrel stuff\data\mission_profile.json"
```

Every run is isolated under **`darrel stuff/data/processed/env_cnn_prototype/`** (historical stage name retained). No root `data/`, previous-run deletion, GPU or new package is needed.

## What a mission profile must supply

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

- Existing candidate/evidence/static-support/thermal-support/context, hard-rule and diagnostic preference CSVs remain.
- **`stage3_operational_checks.csv`**: actual configured margins/units/reasons or specific Unknown input gaps.
- **`candidate_assessments.csv`**: separate `stage3_status`, mandatory pass/fail/unknown counts and `operational_preference_score`.
- **`stage3_top_k.csv`**: only candidates whose complete declared mandatory conditions pass and whose configured preference data are sufficient.
- `stage3_preference_details.csv`, `pipeline_stage_counts.csv`, `stage3_evidence/`, `report.json` and `provenance.json` preserve explanations and lineage.

A known mandatory failure dominates Unknown; missing soft data withholds the aggregate rather than renormalizing weights. Stable ties use candidate ID. Diagnostic top-k is explicitly separate: **14 proxy passes / seven failures do not mean 14 operationally eligible bases**.

With the current blank project profile, all 21 examples remain **Stage 3 Unknown**, and operational top-k is empty. Numerical model tests use fixtures only; no real mission margin or certified safe-site recommendation is claimed.

[Current verification](../data/verification/golden_stage3_final/verification.json): Dar_028–031 executed; direct consumed inputs/outputs checked; **222 relevant tests passed** (28 pipeline, 113 EDA/maintenance, 81 downloader). Existing tests are unchanged. All 210 current operational readiness records are Unknown for the blank profile; no proxy diagnostic pass becomes an operational pass.

## Evidence and remaining work

The original-notebook re-check also executes Dar_032 (native maps/support) and the **existing local notebook 13** (strict/full-source terrain views), rather than duplicating it. Their pinned summaries are consumed under `stage3_evidence/native_support/` and `stage3_evidence/terrain_views/` as quality/context evidence, not new scores or requirement passes. See the [dataset/reuse table](../EDA/EDA_Notes.md#original-notebook-reuse-and-datasets--re-check-8-november-2026) and [executed results](../EDA/EDA_Results.md#15-original-notebook-reuse--executed-8-november-2026). No dated terrain-aware mission history generator was found in the reviewed original code. [Latest reuse verification](../data/verification/source_port_review/final_verification.json).

[Dar_029–031 results](../EDA/EDA_Results.md#14-golden-stage-3-revamp) and the [decision table](../purposal.md) control feature use. Needed next: actual mission/equipment/requirement inputs, applicable terrain-aware temporal and response evidence, and physical candidate/CNN-patch association. A new trained CNN would require an appropriate target, aligned data and independent validation; it is not created by adding optional environmental layers.
