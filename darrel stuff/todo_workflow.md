# Moon proof-of-concept workflow

**Lunar conditions -> evidence-backed rules -> candidate results.**

Moon only, existing data first, no CNN. Mission/equipment profiles are optional in the default comparison. The earlier Steps 1-5 prototype remains bounded by its evidence scope. The expanded Stage 3-4 EDA/proposal work below is **complete within declared source/analysis scopes**; operational suitability is not certified. A separate environmental-only Step 5 CSV engine is now implemented, with scientific policy adoption still pending.

## Comprehensive subject EDA and Stage 4 (completed 11 November 2026)

Dar_044 is the **combined initial screening baseline**, not the requested final subject-by-subject EDA. Preserve its executed results and reuse its readers; do not just split its existing tables across notebooks and call that new analysis.

**Executed subjects:** UV Dar_045; full ESA plasma Dar_046; depth-aware historical thermal Dar_047; dust Dar_048; radiation time/extremes Dar_049; native polar thermal model Dar_050; full exosphere Dar_051; full selected neutron spectra Dar_052; three-axis seismic Dar_053; two model years of terrain/illumination Dar_054; operational/PDF/resource synthesis Dar_055. **Dar_056 completes the Stage 4 handoff:** 64 unadopted proposal rows, source/field/outline crosswalks, cross-subject findings and Passed/Failed/Unknown semantics. [Findings and exact scope](EDA/EDA_Notes.md#expanded-subject-eda-and-time-windows---11-november-2026) | [Validation](data/verification/latest_subject_eda.txt).

Completion does not mean every archive record or PDF page was reviewed, or that local responses/capabilities are qualified. Full/sparse/experimental coverage, unresolved fields, source-quality holds and missing operational inputs remain explicit in the handoff. No mission profile, current limit or weight was invented.

**Time requirement:** UTC month, quarter, four-month term, half-year, calendar year, nonoverlapping two-year windows and DJF/MAM/JJA/SON calendar groups where timestamps support them. Include full denominators, gaps, partial windows and extrema. Both half-year and two-year comparisons are included; calendar "seasons" are not lunar seasons. Do not fabricate histories for static/cumulative maps or extend short historical missions.

### Stage 3 — subject EDA, cross-check and base conclusions

- [x] Map new source/analysis fields to environmental subjects and existing EDA; record coverage gaps and unanalysed/unqualified dimensions in the final crosswalks.
- [x] Execute eleven dedicated subject studies; reuse and cross-check existing terrain/image/communications and other accepted analyses.
- [x] Analyse distributions, quality/missingness, time/extremes, depth/location/geometry and supported relationships. Include year-plus modern histories and two full model years where available; preserve short historical mission durations.
- [x] Compare with existing EDA and separate scope, clock-policy, sampling and unit differences rather than silently replacing old findings.
- [x] Publish per-subject/cross-subject conclusions with full/sparse/experimental coverage. Expand ESA/NMS/LEND and native LAMP/three-axis waveform coverage; do not infer unsupported seasons, local dose/charging or hazard rates.

### Stage 4 — traceable requirements proposal, not live pipeline changes

- [x] Compile findings and source/page-linked mission lessons into 15 conditional hard, 11 conditional soft and 38 evidence-quality proposal rows.
- [x] Record quantity/units, evidence origin, scope, required inputs, source-specific logic, authority/adoption gaps and uncertainty. Missing operational quantities/limits remain unbound; research priorities are not weights.
- [x] Specify Passed/Failed/Unknown semantics, requirement selection and preference eligibility; preserve unsupported/non-monotonic directions and source-failure versus site-failure distinctions.
- [x] Review the existing-rule crosswalk and context/proposal readiness; keep the compiled artifacts outside the active register and pipeline.
- [x] Update the existing notes/overview, validate saved execution/output hashes/traceability and targeted tests, and preserve existing folders, protected tests and active pipeline behaviour.

**Step 5 follow-up (11 November):** the user authorised a separate [env_pipeline](env_pipeline/README.md). Its CSV engine implements evidence validation, hard gates, domain utilities and final ranking. The default policy invents no limits or weights; all 21 existing candidate rows remain Unknown/unranked in the bounded check. Fictional fixtures demonstrate scoring separately. Scientific policy calibration/adoption and full site-local data mapping remain pending; the existing prototype engine, scoring, source pins and outputs are unchanged.

1. **Audit data:** inspect completed files, receipts, labels, dates, coverage and missing inputs. Freeze the selection while downloads continue. No EDA here.
2. **Extract NASA evidence:** record deployment strategies, resource budgets, usage, problems and conditional limits with exact source pages. Check a small sample before scaling; retain extraction holds.
3. **Analyze:** reuse existing notebooks, then extend environmental/operational EDA where the available data supports a decision. Preserve quality flags, gaps, spatial/time support and observed/modelled distinctions. Radiation studies should cover at least a year, preferably two where actually available.
4. **Define rules:** map evidence to applicable hard constraints, soft preferences and evidence-quality checks. Record source, units, applicability and uncertainty. Research priorities are not rule classifications or weights.
5. **Demonstrate:** run the existing-data engine and show conditions, explained checks, candidate comparisons and limitations. Keep optional operational assessments separate. Missing mandatory evidence remains Unknown; failed/unknown mandatory conditions cannot be offset by a preference score.

**Deferred Step 6:** broader engineering/physical validation, independent validation and complete mission reconstruction. Targeted software checks are already part of Step 5, not deferred.

## Working guides

[Sources and extraction](research/Research_Notes.md) | [EDA steps and findings](EDA/EDA_Notes.md) | [Run the prototype](Pipeline_Proto/README.md).

Severe applicable radiation, thermal/power extremes, impacts, seismic and other hazards must not be traded away. Their presence does not justify inventing an exposure limit: quantity, duration, protection and applicable requirements must be established first.

**9 November radiation extension:** Step 3 now includes row-level multi-year radiation quality and bounded primary sampling in Dar_041. Steps 4-5 add E10/E11/E12 and consume 39 scoped tables without changing scores or inventing operational passes. [Measured scope, holds and verification](EDA/EDA_Notes.md#radiation).

**Science-layer extension:** Dar_042 reuses existing EDA to derive explicit candidate proxies and reference scenarios. Step 4 adds E13 source/model boundaries; Step 5 adds unweighted science preference fronts alongside the baseline, with missing evidence and operational limits still Unknown. [Current findings](EDA/EDA_Notes.md#final-results-and-findings).

**Time-period extension (10 November 2026):** Step 3 executes Dar_043 monthly/quarterly radiation, solar-UV and spacecraft-plasma analysis with quality, missingness, instrument identity and geometry/cadence support. Step 4 adds E14–E16 evidence guards; Step 5 consumes seven pinned tables and publishes historical time-context explanations. Calendar quarters are not lunar seasons; non-overlapping histories are not correlated simultaneously. No new mission/equipment defaults, scoring weights or safety limits are adopted. [Findings](EDA/EDA_Notes.md#monthly-and-quarterly-comparisons--dar_043) | [Verification](data/verification/latest_temporal_environment.txt).

**New-download Step 3 extension (11 November 2026):** Dar_044 is executed and saved: ten source families, 18 tables and 10 plots, using explicitly declared full/sparse cohorts and seven PDF cases. Contemporary SEE supports new matched-date context comparisons; quality, instrument mode, clock ambiguity, historical location and model/measurement boundaries remain explicit. Existing Step 4-5 source pins and behaviour are unchanged. Any later handoff must adopt the appropriate cohort/support contracts rather than replacing local safety evidence with raw/reference values. [Results and exact cohort coverage](EDA/EDA_Notes.md#new-download-eda--executed-dar_044-11-november-2026) | [Validation](data/verification/latest_new_environment_eda.txt).
