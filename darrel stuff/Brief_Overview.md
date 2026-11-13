# Moon environmental suitability

**Flow:** lunar conditions -> evidence-backed rules -> candidate assessment.

Evaluate whether an intended mission could operate at a selected Moon site. This workstream covers lunar environmental evidence and a standalone test comparison; no CNN integration or Mars work. Mission/equipment profiles are optional for the test comparison. Full operational suitability still requires applicable requirements, configuration and response evidence. Missing operational evidence is **Unknown**; the test pipeline can explicitly omit blank measurements in available-data mode.

## Start here

| Guide | Purpose |
| --- | --- |
| [Workflow](todo_workflow.md) | Steps 1-5 and what remains deferred. |
| [Research sources](research/Research_Notes.md) | Dataset priorities, NASA source evidence and applicability. |
| [EDA notes](EDA/EDA_Notes.md) | Environmental categories, analysis methods, scope and limitations. |
| [Test Pipeline](env_pipeline/legacy_1/README.md) | Archived prototype documentation; not the active scoring pipeline. |
| [Downloads](download_script/Download_Dataset_Instructions.md) | Existing-data and additive download commands. |
| [Main Pipeline](env_pipeline/README.md) | Main pipeline. Run this for the input/output for env suitably |

## Algorithm proposal

**Environmental-only pipeline:** [env_pipeline](env_pipeline/README.md) is one standalone Python script plus `config.yml`, using nine domain definitions without terrain scoring. Runtime reads only the supplied CSV and YAML, never EDA outputs or evidence sidecars. Its [current input](env_pipeline/inputs/sites.csv) is a 77-row measurement-level test fixture. `assumption_NASA_values` supplies project-assumed thresholds and weights, not official NASA limits. `available_data` mode and independent domain/scoring/gate toggles control participation. Earlier implementations are preserved under `env_pipeline/legacy_1/` and `env_pipeline/legacy_2/`.

[Feature decisions](purposal.md) separate usable measurements, reference-only evidence and deferred inputs. Research P1/P2/P3 tags are not hard/soft requirements or scoring weights.

Preference scores cannot compensate for failed or unknown evaluated hard gates. Skipping a blank in available-data mode is not evidence of physical safety.

The [science-based comparison](EDA/EDA_Notes.md#final-results-and-findings) covers candidate radiation-geometry/UV proxies, charging references and unweighted preference fronts in the archived prototype. Keep this evidence-based research separate from the active test mappings, avoid duplicate sunlight/UV weighting, and do not interpret plasma density as safety.

## Step 4-5 alignment check

- Compare handoff tables with their declared EDA source pins, schemas, units and scope before adopting them.
- Keep the archived context-comparison policy separate from the active standalone assumption policy; do not treat a missing operational profile as a safety pass.
- Validate missing-data, mode/toggle and gate-before-final-score behavior with targeted checks. See the [pipeline guide](env_pipeline/README.md) for the current workflow.

## EDA extensions

The following notebooks extend the environmental analysis scope. Keep their acquisition cohorts, quality policies and scientific applicability separate from software-test assumptions.

| Notebook | What is covered | Scope and limits |
| --- | --- | --- |
| [Dar_040: download and thermal review](EDA/Moon/Stage3_Requirements/Dar_040_download_refresh_thermal_quality.ipynb) | Review downloaded inputs and dated thermal-query products. | Qualify source flags and overlapping query support before constructing a temperature envelope. |
| [Dar_041: multi-year radiation](EDA/Moon/Stage3_Requirements/Dar_041_multiyear_radiation_quality.ipynb) | Analyse CRaTER and GOES histories separately by instrument/version; retain explicit primary sampling and thermal cohorts. | Preserve gaps and quality filters. Counts/flux are not local crew dose; a primary sample is not a complete event census. |
| [Dar_042: science-based indicators](EDA/Moon/Stage3_Requirements/Dar_042_lunar_science_indicators.ipynb) | Define sky-openness and UV exposure-opportunity proxies and plasma/charging reference context. | Relative indicators are not local radiation dose, UV intensity or surface voltage. Lower plasma density or more darkness is **not automatically safer**. |

**Effect on Steps 4-5:** source-quality guards, scoped handoffs and science preference views support evidence preparation. They do not automatically adopt active test thresholds/weights or establish operational suitability. Thermal comparison requires complete comparable profiles.

**Related analysis:** terrain, illumination, Apollo resources, seismic and impacts. Documentation and link/import maintenance are separate from scientific analysis. See [EDA Notes](EDA/EDA_Notes.md) for the category-level methods.

## Files and data

- `EDA/`: Earth/Moon notebooks and analysis helpers; `env_pipeline/`: active standalone scorer, config and input/output files.
- `env_pipeline/legacy_1/`: archived environmental comparison prototype; `env_pipeline/legacy_2/`: archived project-integrated implementation. Neither is imported by the active standalone script.
- Reusable EDA helpers are in `EDA/shared/`; Stage 3 scripts/configs are in the existing `EDA/Moon/Stage3_Requirements/` folder. Notebook locations and existing import names are unchanged. See [helper locations](EDA/EDA_Notes.md#python-helper-locations).
- `research/`: source register and scoped rules; `download_script/` and `download_script_addons/`: acquisition tools.
- `darrel stuff/.gitignore`: the single ignore file for this workstream; no nested ignore files are needed.
- Scientific data and EDA runs: `darrel stuff/data/`; additive downloads: `D:\projects\NASA Dataset`.
- Generated reports, source documents and provenance are preserved. EDA notebook conventions are consolidated in `EDA/EDA_Notes.md`; the former EDA guides/instructions are archived via `data/verification/latest_eda_notes_cleanup.txt`. Consolidated source-doc originals are recoverable via `data/verification/latest_docs_download_review.txt`.

**Code maintenance:** preserve modules used by notebooks, commands or tests, along with source data and historical provenance. Use the existing verification records to locate archived artifacts; maintenance is not scientific validation.
