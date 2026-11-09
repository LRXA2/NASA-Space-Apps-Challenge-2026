# Moon proof-of-concept workflow

**Lunar conditions -> evidence-backed rules -> candidate results.**

Moon only, existing data first, no CNN. Mission/equipment profiles are optional in the default comparison. Steps 1-5 are complete within the bounded evidence scope; new downloads enter through the same quality checks, not automatic scoring.

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
