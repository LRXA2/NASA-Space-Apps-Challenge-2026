# Moon environmental suitability

**Flow:** lunar conditions -> evidence-backed rules -> candidate results.

Evaluate whether an intended mission could operate at a selected Moon site. This workstream uses existing lunar data first; no CNN integration or Mars work. Mission/equipment profiles are optional for the default environmental comparison. Full operational suitability still requires applicable requirements, configuration and response evidence. Missing evidence is **Unknown**, never a pass.

## Start here

| Guide | Purpose |
| --- | --- |
| [Workflow](todo_workflow.md) | Steps 1-5 and what remains deferred. |
| [Research sources](research/Research_Notes.md) | Dataset priorities, NASA source evidence and applicability. |
| [EDA notes](EDA/EDA_Notes.md) | Environmental categories, steps taken, findings and limitations. |
| [Pipeline](Pipeline_Proto/README.md) | Run commands, actual outputs and verification. |
| [Downloads](download_script/Download_Dataset_Instructions.md) | Existing-data and additive download commands. |

## Algorithm proposal

[Feature decisions](purposal.md) separate usable measurements, reference-only evidence and deferred inputs. Research P1/P2/P3 tags are not hard/soft requirements or scoring weights.

The verified prototype compares 21 exploratory components: 14 context-ranked, seven excluded by configured filters, top five shown. These are **not 14 operationally approved sites**. Scores cannot compensate for failed or unknown mandatory safety conditions.

The [science-based comparison](EDA/EDA_Notes.md#final-results-and-findings) now adds candidate radiation-geometry/UV proxies, charging references and unweighted preference fronts using our EDA. It keeps the visibility score as a baseline, avoids duplicate sunlight/UV weighting, and does not rank plasma density as safety. [Open current options](Pipeline_Proto/outputs/LATEST_RESULTS.md).

## EDA added since the last commit

Compared with **`fca88dc` (9 November 2026, 08:23 SGT)**, three new notebooks extend the earlier analysis. All three have saved executions without errors.

| Notebook | What was added | Findings and limits |
| --- | --- | --- |
| [Dar_040: download and thermal review](EDA/Moon/Stage3_Requirements/Dar_040_download_refresh_thermal_quality.ipynb) | Checked newly downloaded inputs and expanded dated thermal checks from six products in one region to **812 across three regions**. | **Zero strict-quality rows** remain. More downloads did not establish a usable temperature envelope; query rows can overlap. |
| [Dar_041: multi-year radiation](EDA/Moon/Stage3_Requirements/Dar_041_multiyear_radiation_quality.ipynb) | Extended CRaTER from **494 to 1,091 dates / 94.1 million records**; GOES-16 from **495 to 524 dates**; added **791 GOES-19 dates** separately. Sampled **660,000 primary records from 33 monthly files**. | Only **10.48% / 10.82%** of GOES-16/19 channel/time bins meet the strict filter. Gaps and instrument/version differences remain explicit. Counts/flux are not local crew dose; primary samples are not a full event census. |
| [Dar_042: science-based indicators](EDA/Moon/Stage3_Requirements/Dar_042_lunar_science_indicators.ipynb) | Derived candidate sky-openness and UV exposure-opportunity proxies; added plasma/charging reference context. | Supports relative comparisons, not local radiation dose, UV intensity or surface voltage. Lower plasma density or more darkness is **not automatically safer**. |

**Effect on Steps 4-5:** the download/radiation extension feeds revised evidence guards and 39 scoped tables without changing the baseline filters/weights or granting safety passes. The separate science view identifies **two non-dominated trade-off options**, not two certified safe sites. Thermal comparison is withheld because only one filter-passing candidate has a complete comparable profile.

**Already in the commit:** earlier terrain, illumination, Apollo resource, seismic and impact EDA. Documentation consolidation and link/import cleanup are separate maintenance, not new scientific analysis. See [EDA Notes](EDA/EDA_Notes.md) for the category-level findings.

## Files and data

- `EDA/`: Earth/Moon notebooks and analysis helpers; `Pipeline_Proto/`: engine and its outputs.
- `research/`: source register and scoped rules; `download_script/` and `download_script_addons/`: acquisition tools.
- Scientific data and EDA runs: `darrel stuff/data/`; additive downloads: `D:\projects\NASA Dataset`.
- Generated reports, source documents and provenance are preserved. EDA notebook conventions are consolidated in `EDA/EDA_Notes.md`; the former EDA guides/instructions are archived via `data/verification/latest_eda_notes_cleanup.txt`. Consolidated source-doc originals are recoverable via `data/verification/latest_docs_download_review.txt`.

**Code cleanup:** all 24 active Python modules are retained because notebooks, commands or tests use them. Two obsolete one-off writers are archived, five unused imports removed and disposable runtime/bytecode files cleaned. Recovery and validation are indexed by `data/verification/latest_code_cleanup.txt`; scientific data, notebooks, tests and historical provenance remain intact.
