# Moon proof-of-concept workflow

**Lunar conditions -> evidence-backed rules -> candidate assessment.**

Moon only, existing evidence first, no CNN. Mission/equipment profiles are optional for the software demonstration. The earlier Steps 1-5 prototype remains archived within its evidence scope. Stage 3-4 supplies subject EDA and requirement proposals; operational suitability is not certified. The active environmental-only Step 5 CSV engine uses explicit test assumptions while scientific policy adoption remains separate.

<a id="comprehensive-subject-eda-and-stage-4-completed-11-november-2026"></a>
## Comprehensive subject EDA and Stage 4

Dar_044 is the **combined initial screening baseline**, not a substitute for subject-by-subject EDA. Preserve its analysis artifacts and reuse its readers; do not just split its existing tables across notebooks and call that new analysis.

**Subject notebooks:** UV Dar_045; full ESA plasma Dar_046; depth-aware historical thermal Dar_047; dust Dar_048; radiation time/extremes Dar_049; native polar thermal model Dar_050; full exosphere Dar_051; neutron spectra Dar_052; three-axis seismic Dar_053; terrain/illumination Dar_054; operational/PDF/resource synthesis Dar_055. **Dar_056 defines the Stage 4 handoff:** conditional requirement proposals, source/field/outline crosswalks and Passed/Failed/Unknown semantics. [Methods and scope](EDA/EDA_Notes.md#expanded-subject-eda-and-time-windows---11-november-2026).

EDA scope does not imply that every archive record or PDF page is reviewed, or that local responses/capabilities are qualified. Full/sparse/experimental coverage, unresolved fields, source-quality holds and missing operational inputs must remain explicit. Test assumptions in `assumption_NASA_values` are not adopted mission limits or scientific weights.

**Time requirement:** UTC month, quarter, four-month term, half-year, calendar year, nonoverlapping two-year windows and DJF/MAM/JJA/SON calendar groups where timestamps support them. Include full denominators, gaps, partial windows and extrema. Both half-year and two-year comparisons are included; calendar "seasons" are not lunar seasons. Do not fabricate histories for static/cumulative maps or extend short historical missions.

### Stage 3 - subject EDA, cross-check and scope

- [x] Map new source/analysis fields to environmental subjects and existing EDA; record coverage gaps and unanalysed/unqualified dimensions in the final crosswalks.
- [x] Execute eleven dedicated subject studies; reuse and cross-check existing terrain/image/communications and other accepted analyses.
- [x] Analyse distributions, quality/missingness, time/extremes, depth/location/geometry and supported relationships. Include year-plus modern histories and two full model years where available; preserve short historical mission durations.
- [x] Compare with existing EDA and separate scope, clock-policy, sampling and unit differences rather than silently replacing old findings.
- [x] Publish per-subject/cross-subject conclusions with full/sparse/experimental coverage. Expand ESA/NMS/LEND and native LAMP/three-axis waveform coverage; do not infer unsupported seasons, local dose/charging or hazard rates.

### Stage 4 - traceable requirements proposal, not automatic pipeline adoption

- [x] Compile evidence and source/page-linked mission lessons into conditional hard, conditional soft and evidence-quality proposal rows.
- [x] Record quantity/units, evidence origin, scope, required inputs, source-specific logic, authority/adoption gaps and uncertainty. Missing operational quantities/limits remain unbound; research priorities are not weights.
- [x] Specify Passed/Failed/Unknown semantics, requirement selection and preference eligibility; preserve unsupported/non-monotonic directions and source-failure versus site-failure distinctions.
- [x] Review the existing-rule crosswalk and context/proposal readiness; keep the compiled artifacts outside the active register and pipeline.
- [x] Update the existing notes/overview, validate saved execution/output hashes/traceability and targeted tests, and preserve existing folders, protected tests and active pipeline behaviour.

**Step 5 pipeline:** [env_pipeline](env_pipeline/README.md) is a standalone Python script plus `config.yml`: one measurement CSV -> configured gates/preferences -> domain scores -> qualified final score -> one output CSV. It does not import project helpers or read EDA outputs, manifests or evidence sidecars. Earlier implementations are preserved in `env_pipeline/legacy_1/` and `env_pipeline/legacy_2/`. The active `assumption_NASA_values` policy has nine domain definitions, available-data/strict modes and independent domain, scoring and hard-gate toggles; its thresholds and weights are project test assumptions, not scientific defaults.

1. **Audit data:** inspect completed files, receipts, labels, dates, coverage and missing inputs. Freeze the selection while downloads continue. No EDA here.
2. **Extract NASA evidence:** record deployment strategies, resource budgets, usage, problems and conditional limits with exact source pages. Check a small sample before scaling; retain extraction holds.
3. **Analyze:** reuse existing notebooks, then extend environmental/operational EDA where the available data supports a decision. Preserve quality flags, gaps, spatial/time support and observed/modelled distinctions. Radiation studies should cover at least a year, preferably two where actually available.
4. **Define rules:** map evidence to applicable hard constraints, soft preferences and evidence-quality checks. Record source, units, applicability and uncertainty. Research priorities are not rule classifications or weights.
5. **Demonstrate:** run the single-input engine with the measurement-level fixture and explain configured checks, participation and limitations. Keep operational qualification separate. Available-data mode can skip blank measurements; evaluated Failed/Unknown hard gates still block final scores. Skipped checks are not evidence of physical safety.

**Deferred Step 6:** broader engineering/physical validation, independent validation and complete mission reconstruction. Targeted software checks are already part of Step 5, not deferred.

## Working guides

[Sources and extraction](research/Research_Notes.md) | [EDA steps and scope](EDA/EDA_Notes.md) | [Run the pipeline](env_pipeline/README.md).

Severe applicable radiation, thermal/power extremes, impacts, seismic and other hazards must not be traded away. Their presence does not justify inventing an exposure limit: quantity, duration, protection and applicable requirements must be established first.

**Radiation extension:** Step 3 covers row-level multi-year radiation quality and bounded primary sampling in Dar_041. E10/E11/E12 define evidence-use guards; research handoffs do not automatically change the standalone test policy or qualify safety. [Methods and limits](EDA/EDA_Notes.md#radiation).

**Science-layer extension:** Dar_042 defines candidate proxies and reference scenarios from EDA. E13 records source/model boundaries; unweighted research preference fronts remain separate from the active weighted test scorer. Missing local evidence and operational limits require qualification. [Comparison scope](EDA/EDA_Notes.md#final-results-and-findings).

**Time-period extension:** Dar_043 defines monthly/quarterly radiation, solar-UV and spacecraft-plasma analysis with quality, missingness, instrument identity and geometry/cadence support. E14-E16 guard calendar and source comparability. Calendar quarters are not lunar seasons; non-overlapping histories must not be correlated as simultaneous observations. No mission/equipment limit follows automatically from a time comparison. [Methods](EDA/EDA_Notes.md#monthly-and-quarterly-comparisons--dar_043).

**New-download Step 3 extension:** Dar_044 defines initial screening across environmental source families and source/page-linked PDF cases. Preserve full/sparse cohorts, instrument mode, clock ambiguity, historical location and model/measurement boundaries. Handoff adoption requires the appropriate support contracts rather than substituting raw/reference values for local safety evidence. [Methods and cohort scope](EDA/EDA_Notes.md#new-download-eda--executed-dar_044-11-november-2026).
