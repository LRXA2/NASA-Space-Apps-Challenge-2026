# EDA summary: problems, decisions and next steps

Updated 30 October 2026. **Earth and Moon only; Mars is excluded.**

**Status:** broad terrain and environmental EDA is complete across five Earth sites and seven lunar regions. No model, independent analog labels or mission suitability scores have been validated. The next step is to define one mission/training scenario and what makes an analog relevant—not another generic EDA sweep.

## Key problems

| Problem | Implication |
| --- | --- |
| **Similarity is not validated relevance.** Slope/relief bands measure selected physical differences. | Obtain independent relevance judgments, including weak and no-match cases. Do not use the bands as both labels and proof of accuracy. |
| **Matches lack geographic variety.** Wadi Rum rarely meets joint strict-lunar requirements; many queries reuse Earth candidates. | More nearby patches do not create independent settings. Evaluate transfer across whole regions. |
| **Screening changes the answer.** Relaxing bare-ground requirements adds Arizona matches, but sampled imagery shows woody cover. | Keep baseline and alternative screens separate. More matches do not establish better training sites. |
| **Lunar support is uneven.** Full-context terrain may be prior-dominated; a common 30 m grid does not establish equal effective resolution. | Retain full-context and image-supported views separately. Source checks do not establish absolute accuracy. |
| **Thermal completeness would erase regions.** Requiring all 17 common products removes three regions; image-supported Faustini also loses all qualifying centers. | Preserve missingness, report selection effects and avoid a universal complete-case filter. |
| **Environmental data cannot establish mission limits.** Monthly climate, phase-average temperatures and mean illumination do not resolve event extremes or continuous darkness. | Keep unsupported constraints and unresolved units/quality Unknown. Obtain finer evidence only when the scenario requires it. |
| **Infrastructure is not verified access.** OSM tags do not prove permission, passability or emergency readiness. | Verify practical requirements separately from terrain and environmental fidelity. |

Death Valley and Wadi Rum now have matching climate/support coverage. Keep climate at native resolution. Do not invent equipment thresholds or collapse missing evidence into a universal suitability score.

**Resolved processing issue:** the original Arizona elevation gaps came from tile selection, and Earth derivative losses from insufficient processing context. These were corrected. The old lunar elevation holes were introduced by our image-support mask; the current full-context elevation has zero gaps inside all seven ROIs. Historical masked maps must not be interpreted as absent source heights. Derivative edge exclusions and genuine environmental missingness remain separate limitations.

## Decisions we keep

- **Current sites are development data:** Arizona, Lanzarote, Atacama, Death Valley, Wadi Rum and all seven explored lunar regions. Prior EDA exposure cannot become an untouched test retrospectively.
- **Keep locations together:** overlapping patches, scales, origins, augmentations, support views and source versions share one split role. Check full feature context, currently at least 150 m beyond grid footprints. Separation alone does not prove independence.
- **Keep model choices provisional:** retain 300/600/960 m comparisons and both lunar views. Fit normalization, features and models only on development data; compare site-balanced sampling with count-weighted sampling.
- **Protect final reserves:** validation may guide choices; final regions remain unopened for morphology inspection or tuning. If exposed, retire their final role and record it. Never replace a region because it scores poorly.
- **Evaluate fairly:** freeze splits, source masks, model/baseline, candidate pools, rubric, top-k and no-match rules. Test unseen lunar queries, unseen Earth candidates and both unseen separately. Report regional failures and macro averages; neighboring patches are not independent test replicates.

## Proposed reserves—not yet verified or enforced

| Role | Regions |
| --- | --- |
| Earth validation | Askja; Flinders Ranges |
| Earth final test | Mauna Loa; Namib–Sossusvlei |
| Lunar validation | Peak Near Shackleton |
| Lunar final test | Amundsen Rim + Nobile Rim 2, treated conservatively as one block |

Before training, verify source feasibility, footprints, context overlap and prior exposure, then implement a region-role manifest. Other nearby lunar regions remain unassigned. These few proposed groups do not justify broad generalization; lunar coverage remains south-polar.

## Next steps—adapt to findings

1. Define **one scenario**: activity, duration, season, equipment and what Earth must reproduce.
2. Define **relevance and evaluation**: independent judgments, no-match cases, geographic splits and metrics.
3. Resolve **only consequential gaps**, such as extremes, darkness duration, thermal-quality concerns or access.
4. Evaluate a **physical baseline**, then test whether a learned model adds value.

Update this summary when a decision changes; keep detailed methods and measurements in notebooks and reports.

## Evidence when needed

[Notebook index and accepted runs](notebooks/README.md) · [Candidate inspection](notebooks/diagnostics/candidate-inspection-20261029T132642335288Z/REPORT.md) · [Source checks](notebooks/diagnostics/source-check-20261029T144220349448Z/REPORT.md) · [Lunar environment](notebooks/diagnostics/environment-eda-20261029T152503541251Z/REPORT.md) · [Five-site Earth environment](notebooks/diagnostics/five-site-environment-eda-20261029T163459826797Z/REPORT.md) · [Units policy](notebooks/diagnostics/environment-readiness-20261028/REPORT.md) · [Diviner source interpretation](notebooks/diagnostics/environment-eda-research-20261029/SOURCES.md) · [Region research](notebooks/diagnostics/region-diversity-20261029/REGION_RESEARCH.md).

Historical reports/manifests remain unchanged and may reference retired working documents. This file is the current decision summary.
