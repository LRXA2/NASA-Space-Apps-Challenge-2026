# Purpose

Support Moon base-location selection through environmental research and an explainable assessment of whether the **intended mission and selected equipment can operate there**. Earth evidence is supporting analog/reference material, not a substitute for lunar conditions.

# Objective and required Stage 3 target

Our controlling target is [outline Stage 3 — Environmental and Equipment Suitability Engine](../outline.md#stage-3--environmental-and-equipment-suitability-engine).

**Inputs:** planetary measurements/model estimates; mission duration/activities; crew requirements; equipment capabilities/limitations; environmental/operational safety requirements.

**Flow:** retrieve applicable site/period conditions → load equipment → define hard/soft requirements → compare capability with demand → calculate consumable/power/thermal/operational margins where parameters exist → explain failures/uncertainties → score preferences only after mandatory requirements pass.

**Output:** environmental suitability evidence, equipment adequacy, operating margins, failed requirements and uncertainty indicators. Missing evidence is **Unknown**, never an automatic pass.

The overall project also considers terrain and Earth analog selection, as stated in the [overview](../outline.md#1-project-overview). The active work here is Moon-focused. Original terrain CNN code remains unchanged.

# Priority

1. **Required Stage 3 first:** close Stage 3 evidence, configuration and response-model gaps.
2. **Original research P1:** use supporting research where it contributes; all 34 P1 rows remain traceable.
3. **P2/P3 additions:** follow their existing tags and a defined question. Extra data cannot substitute for missing required Stage 3 inputs.

The [proposal and decision table](purposal.md) is the single place for selected/reference-only/deferred/rejected pipeline contributions and reasons. [EDA results](EDA/EDA_Results.md#14-golden-stage-3-revamp) contains the measured findings; [EDA notes](EDA/EDA_Notes.md) is the work/notebook guide.

# Current state — 8 November 2026

| Area | Completed | Still required |
| --- | --- | --- |
| Data audit | Dar_029: 53 research entries, core + bounded selections; zero missing/size-mismatched selected files. | D21–D24 gated; D17/D25 unselected P2; project M-inputs are not universal downloadable datasets. No whole-archive checksum claim. |
| Required Stage 3 time/site EDA | Dar_030: local-hour/Ls coverage, held-out cyclic diagnostics, terrain-conditioned phase relationships and twelve-month sampled geometry. | Requested mission period, terrain-aware illumination/contact and validated support/response. |
| Original notebook reuse | All 36 original notebooks reviewed; Dar_032 and existing local 13 executed for seven regions. | No dated terrain-aware history generator found; full Earth/CNN replay needs additional sources/artifacts. [Reuse/dataset table](EDA/EDA_Notes.md#original-notebook-reuse-and-datasets--re-check-8-november-2026). |
| Crew/equipment references | Dar_031: sourced nominal load sensitivity; battery protocol, radiation scenario and soil-geometry envelopes; requirement-reference mapping. | Actual crew/equipment, applicable limits, stocks/reserves and local models. Reference data does not establish adequacy. |
| P1 evidence | Existing Dar_001–027 plus current audit/reference follow-up. Missing M-records receive schema/readiness EDA, not invented measurements. | Resolve applicable P1 gaps before optional feature promotion. |
| Pipeline | Dar_028 experiment workflow; conditional stock, storage, thermal, outage and capacity–demand models; separate diagnostic/operational results. | A complete applicable mission/equipment/requirements profile. Current operational candidates remain Unknown. |

S02 NASA-STD-3001 V2 F and S03 V1 C PDFs are acquired. S01 BVAD Rev2 has a documented official-source table extract; full local PDF retrieval returned HTTP 403. None supplies our mission configuration.

[Latest reuse verification](data/verification/source_port_review/final_verification.json): Dar_032 and existing notebook 13 executed across seven regions; Dar_028 re-executed with their pinned context tables. **225 relevant tests passed** (116 EDA/maintenance, 81 downloader, 28 pipeline). Operational top-k remains empty for the blank mission profile; diagnostic proxy results are not operational eligibility. Earlier runs retain their [historical verification](data/verification/golden_stage3_final/verification.json).

# Folder guide

| Folder | Purpose |
| --- | --- |
| **EDA/** | Earth/Moon notebooks, reusable analysis helpers, tests, work plan and measured results. New required Stage 3 notebooks are in `Moon/Stage3_Requirements/`. |
| **Pipeline_Proto/** | CNN-style notebook/configuration workflow, rule-based orchestration and focused Stage 3 margin models. Start with [README](Pipeline_Proto/README.md). |
| **download_script/** | One downloader; bounded discovery, threaded transfers, verified skips, retries and error logs. |
| **research/** | Original dataset register/workbook and P-tagged impact reasoning. |
| **data/** | Scientific downloads, receipts, manifests, EDA/pipeline outputs and verification. |

All data/output stays in **`darrel stuff/data/`**; repository-root `data/` remains absent. Legacy manifests are preserved in `data/legacy_root_data/`. Shared `data_maintenance.py` stays here because EDA/download code uses it.

Active helpers/tests are needed; fourteen retired one-time builders/migrations are recoverable from the [verified archive](data/verification/workspace_cleanup_20261108/retired_one_time_scripts.zip). No scientific source data or completed runs were discarded.

## Notebook organisation

Names remain `Dar_0xx_descriptive.ipynb`, unique across the workstream. Use `EDA/<planet>/<category>/` only when a category has more than two notebooks; smaller groups stay under the planet. Dar_029–032 form the required Stage 3 category. Existing notebook 13 is reused, not duplicated. Dar_028 stays with the pipeline experiment, not the EDA source notebooks.
