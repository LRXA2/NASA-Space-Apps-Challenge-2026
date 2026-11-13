# Moon proof-of-concept workflow

# Moon proof-of-concept workflow

**Lunar conditions -> evidence-backed rules -> candidate results.**

Moon only, existing data first, no CNN. Mission/equipment profiles are optional in the default comparison. Steps 1-5 are complete within the bounded evidence scope; new downloads enter through the same quality checks, not automatic scoring.

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

**New-download Step 3 extension:** Dar_044 defines initial screening across environmental source families and source/page-linked PDF cases. Preserve full/sparse cohorts, instrument mode, clock ambiguity, historical location and model/measurement boundaries. Handoff adoption requires the appropriate support contracts rather than substituting raw/reference values for local safety evidence. [Methods and cohort scope](EDA/EDA_Notes.md#new-download-eda---dar_044).
