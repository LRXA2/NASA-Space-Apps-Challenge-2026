# Decision-facing Moon EDA results

**Initial decision-facing runs: 6 November 2026; latest continuation: 7 November 2026.** Existing local datasets and accepted prior exports only. No new downloads, logins, equipment assumptions or adopted operating limits. [Latest: 32-question expansion, connected-zone profiles and hard/soft-rule influence](#10-expanded-eda--32-questions-and-hardsoft-rule-influence).

The goal is to help select a Moon base location by preparing reliable environmental evidence for [Stage 3](../../outline.md#stage-3--environmental-and-equipment-suitability-engine), considered together with terrain and mission/equipment requirements. We aim to supply location-specific profiles and explainable hard/soft-rule inputs—not declare a site safe or rank missions without requirements.

## 1. What was implemented

| Notebook | Completed analysis | Inputs |
| --- | --- | --- |
| [Dar_012 — joint environmental context](Moon/Environmental_Context/Dar_012_joint_environmental_context.ipynb) | Joint temperature/illumination/terrain fields; explicit missing phases; spatial coverage; changing versus fixed observation cohorts. | D01–D06 through accepted Dar_001/002 exports and original seven footprints; unfinished slope-error map excluded. |
| [Dar_013 — sensitivity and redundancy](Moon/Environmental_Context/Dar_013_feature_sensitivity_redundancy.ipynb) | Same-product temperature-cohort comparison; predictor correlations at native-center, 1.2, 2.4 and 4.8 km grains; matched quality-band sensitivity. | Dar_012, Dar_002 correlations and Dar_006 quality-band results, with matching environmental provenance. |
| [Dar_014 — geometry and rule readiness](Moon/Environmental_Context/Dar_014_rule_readiness_geometry_context.ipynb) | Sun/Earth reference-geometry co-occurrence and consecutive sample runs; published radiation scenario/depth sensitivity; readiness of possible equipment checks. | Existing D19 benchmark from Dar_010, D31 study tables from Dar_005, Dar_012/013 and research register. |

These complete the **data-supported parts** of the six proposed studies. Actual power endurance, equipment thermal margins, radiation protection margins and communications continuity remain **Unknown**.

## 2. Priority findings for the algorithm

### P1 — Patchy observations are not complete evidence

Dar_012 retains **4,825,369 usable center–product observations**, **55,380 distinct regional native centers**, seven regions and 144 phase products. The 1.2 km index contains **2,430 blocks × 144 products = 349,920 rows**.

- **132,244 block/product combinations (37.8%) have no usable thermal observations.** Their temperatures remain NaN, not zero.
- **17 indexed blocks have no observed thermal centers at any selected phase.** They remain in the index rather than disappearing.
- Of **524 blocks** containing some observed center in all **17 common products**, **24 have no single center observed across all 17**: apparently complete evidence comes from mixing different locations.
- The other **500 blocks contain at least one fixed-common center**. This does not mean every center or the entire block is observed.

| Region | Indexed blocks | Any thermal data | Some center in all 17 products | At least one fixed-common center | Mixed-center-only completeness |
| --- | ---: | ---: | ---: | ---: | ---: |
| Leibnitz Beta Plateau | 196 | 196 | 11 | 10 | 1 |
| Malapert Massif | 342 | 342 | 320 | 315 | 5 |
| deGerlache–Kocher Massif | 306 | 306 | 0 | 0 | 0 |
| Haworth | 650 | 650 | 190 | 172 | 18 |
| Faustini Rim A | 306 | 306 | 3 | 3 | 0 |
| deGerlache Rim 2 | 306 | 289 | 0 | 0 | 0 |
| Connecting Ridge Extension | 324 | 324 | 0 | 0 | 0 |

**Algorithm use:** carry counts, missingness, phase identity and fixed-cohort flags with environmental values. Do not infer a pass, usable area or complete exposure history from a non-empty block. Blocks group sampled centers; they are not CNN inputs or physically validated footprints. Technical native-pixel joins do not establish physical co-registration.

**Evidence:** Dar_012 `candidate_phase_features.csv.gz`, `candidate_block_coverage.csv`, `regional_joint_coverage_summary.csv`, `feature_contract.json`.

### P1 — Temperature summaries depend on which locations are observed

Dar_013 makes **68 same-product comparisons**: 17 common products in the four regions with fixed-common centers. Difference = **fixed-center median minus all-available-center median**, not change over time.

| Region | Fixed-common centers | Median difference across products (K) | Range of product differences (K) |
| --- | ---: | ---: | ---: |
| Leibnitz Beta Plateau | 84 | −6.59 | −37.45 to +38.81 |
| Malapert Massif | 6,051 | +1.17 | −30.77 to +115.79 |
| Haworth | 2,510 | +12.92 | +4.28 to +89.90 |
| Faustini Rim A | 15 | −14.86 | −32.26 to +0.42 |

Largest shift: **+115.79 K** at Malapert, `pcp_avg_tbol_pols_ls030_slon02_240`. Available median: **126.67 K**, 7,569 centers; fixed-common median: **242.46 K**, 6,051 centers. Independently recalculated from the accepted paired observations. This is a selection-sensitive median, **not warming or a sensor uncertainty estimate**. Three regions have no fixed-common cohort and cannot enter this comparison.

**Algorithm use:** retain cohort/phase support rather than treating a regional median as a stable requirement input. Phase-average surface brightness temperature is not equipment temperature, a mission extreme or a dated exposure history.

**Evidence:** Dar_013 `matched_product_cohort_sensitivity.csv`, `cohort_sensitivity_by_region.csv`.

### P1 — Grain, quality and correlated predictors affect interpretation

- **196 native-center predictor pairs** were compared with **588 coarser-grain associations**. There are **22 descriptive sign reversals**, not significance tests; small near-zero reversals need not be meaningful.
- Largest absolute rho change: **0.659**. Elevation versus spot count at deGerlache–Kocher changes from **0.065** at 6,972 native centers to **0.724** at 25 occupied 4.8 km blocks. This changes the grain/weighting, not the underlying physics.
- Elevation-error and effective-resolution ranks are **almost perfectly correlated in all seven regions** (Spearman rho approximately 1). Values and units differ; this does not prove duplicated files.
- Malapert solar/Earth visibility rho is **0.825**. Co-located mean visibility does not establish simultaneous power and contact availability.
- **12,218 quality-band comparisons** were retained; **12,160** have two defined correlations. Some largest differences involve only **3–4 centers** in a band, so they are not robust operational cutoffs. The other **58 remain undefined**, not zero.

**Algorithm use:** retain resolution, cohort and quality support; avoid rewarding several proxies for the same soft preference. Do **not** remove independent mandatory physical checks because their predictors correlate, or turn these correlations into learned scoring weights. Terrain penalties remain attributable to their own assessment stage.

**Evidence:** Dar_013 `aggregation_sensitivity.csv`, `strongest_context_dependencies.csv`, `matched_quality_band_sensitivity.csv`.

### P1 — Published radiation results depend on solar scenario and depth

For **eight all-particle study profiles**—four aluminium areal densities (1, 10, 30 and 60 g/cm²) × two solar scenarios—matched-depth **Smin2019/Smax2015 effective-dose ratios range from 1.286 to 1.835** over tabulated 0–300 cm depths.

**All eight profiles have adjacent depth increases.** A universal “more depth always reduces dose” rule is unsupported by these tables.

**Algorithm use:** keep scenario, material, depth, dose quantity and units together. Published modeled effective-dose rates (cSv/year) are not project crew-dose measurements, approved limits or project transport outputs. Existing CRaTER SEC counters are not LET spectra; the GOES pilot still has **zero strictly accepted rows**. Missing accepted fluence is not zero exposure. No safe/optimal shielding depth is inferred.

**Evidence:** Dar_014 `published_solar_scenario_sensitivity.csv`, `published_depth_profile_shapes.csv`; unchanged Dar_005 quality tables.

### Supporting diagnostic — Mean visibility does not describe operating gaps

The **existing illustrative November 2020 benchmark** supplies 720 hourly UTC samples per region, 1–30 November, with Sun/Earth center elevations over a reference sphere and **no terrain horizon**. It is not a newly assumed mission.

- Both centers are above the reference horizon in **2/720 samples at Faustini (0.28%)**, versus **248/720 at deGerlache–Kocher (34.44%)**. These are sample fractions, not actual power/contact rates or a site ranking.
- Longest Sun-center-at/below-reference-horizon runs contain **341–458 consecutive hourly samples** across regions. First-to-last spans are **340–457 hours**, not sample count in hours.
- **17 of 25 run records are boundary-censored**, so their full extent is not established.

**Algorithm use:** actual battery/contact checks need dated terrain-aware conditions and equipment requirements. Static mean visibility and terrain-free sample runs do not establish darkness duration, battery autonomy, radio outage duration or service continuity.

**Evidence:** Dar_014 `reference_geometry_state_counts.csv`, `reference_horizon_sample_runs.csv`, `reference_horizon_run_summary.csv`.

## 3. What stays Unknown or KIV

| Proposed study | Completed environmental analysis | Still Unknown — not a failed download |
| --- | --- | --- |
| Power endurance | Joint solar context; reference-geometry sample runs. | Loads, generation/storage characteristics, mission schedule and dated terrain-aware illumination/power model: M04/M07. |
| Thermal capability | Joint thermal/context tables; cohort sensitivity. | Component response/testing and equipment limits: M01/M04. |
| Radiation protection | Published solar/depth sensitivity; quality holds retained. | Applicable transport/protection outputs and mission requirements: M04/M06. |
| Joint conditions | Co-located features; empty phases; mixed/fixed-center support. | Physical co-registration, contemporaneous conditions and mission eligibility requirements. |
| Communications | Earth-visibility context; reference-geometry states/runs. | Antenna/relay/link budget and acceptable outages: M04/M08. |
| Uncertainty/redundancy | Cohort, quality-band and spatial-grain sensitivity. | Mission ranking stability: no eligible cohort, mission profile or approved scoring policy. |

The readiness export contains **28 possible region/check combinations, all Unknown**, and **no preference scores**. Applicability and mandatory-versus-preference classification are also Unknown; these are not 28 invented mandatory requirements. Missing project inputs do not label sites Failed.

**Authenticated sources remain KIV:** P1 **D21 ChaSTE** and **D23 ILSA** were not retrieved. Existing gated D22/D24 entries outside P1 are also unchanged. Project M-records are mission/equipment data to supply or generate, not hidden environmental-download files. The unfinished slope-error map remains excluded.

## 4. Outputs and verification

All three notebooks completed in fresh project-Python kernels, with saved tables/plots and no error cells. That batch's targeted tests passed; current suite status is recorded with the latest verification below. A one-region execution was checked before the full batch. Output sizes/SHA-256 and table invariants were checked separately.

Accepted directories under `darrel stuff/data/processed/analysis/`:

| Notebook | Stage / run |
| --- | --- |
| Dar_012 | `dar_012_joint_environment/20261106T134155791814Z_c6f9ab` |
| Dar_013 | `dar_013_feature_sensitivity/20261106T134244275613Z_b3888b` |
| Dar_014 | `dar_014_rule_readiness/20261106T134825293895Z_7a80ac` |

[Final verification](../data/verification/decision_eda_final/verification.json). Data/figures stay in the ignored data folder; notebooks retain rendered outputs. Raw downloads, Dar_001–011 notebooks and root reference folders were not modified by this follow-on.

**Bottom line:** the useful algorithm inputs are environmental features **plus support and sensitivity flags**. The evidence does not yet support a battery size, equipment margin, safe shielding depth or “best site” decision.

## 5. Does the CNN / algorithm engine already exist?

The saved prototype implements terrain-resemblance retrieval, not a completed base-suitability engine. The referenced checkpoints, training run and orientation cache were absent from this checkout at review; that blocks exact demo replay, not the independent environmental EDA. Architecture and integration details are maintained in [the proposal](../Brief_Overview.md#2-what-the-sample-cnn-pipeline-currently-implements).

## 6. Findings → concrete implementation methods

Proposed methods and processing order are centralised in [the algorithm proposal, sections 6–10](../Brief_Overview.md#6-eda-evidence--environmental-criteria-and-methods). This report records observed comparisons and their limits; it does not define a second set of thresholds, weights or implementation instructions.

## 7. Can missing evidence come from online sources?

Public observations/reference tests, scenario-generated outputs and selected mission/equipment configuration are different evidence types. The [research report's source/gap review](../research/Research_Notes.md#public-sources-and-remaining-evidence-gaps) now holds the source routes and access caveats. R01/R02 were subsequently downloaded and analysed in section 8; authenticated sources remain KIV.

## 8. New datasets — executed reference EDA (7 November 2026)

Both R01 and R02 are now present in the main local `data/reference/` folder. This continuation reads those downloads and their verified receipts, **not the earlier verification sample**. No additional downloads or authenticated retrievals were performed. The original Dar_001–014 results above remain separate.

| Notebook | Data / completed analysis | Output stage |
| --- | --- | --- |
| [Earth Dar_015 — battery reference experiments](Earth/Dar_015_battery_reference_experiments.ipynb) | R01 nested MATLAB packages: source/protocol inventory, duplicate-history checks, per-cell capacity histories, measured discharge-energy integration, temperature/ambient context and impedance-parameter quality. | `data/processed/analysis/dar_015_battery_reference/20261106T160105346409Z_3ad1ca/` |
| [Moon Dar_016 — Apollo 15 soil reference](Moon/Terrain_And_Soil/Dar_016_apollo15_soil_reference.ipynb) | R02 six label-driven tables: source missing constants, stress/penetration curves by geometry, load/area/unit consistency, cone corrections and documented depth/collapse flags. | `data/processed/analysis/dar_016_apollo_soil_reference/20261106T160018461511Z_ac6ed4/` |

### P1 reference findings — battery evidence and power-model development

- **38 MATLAB members represent 34 unique cell histories.** Four duplicated histories (B0025–B0028) are byte-identical across packages and are counted once; both source locations remain in `package_member_inventory.csv`. Repeated files/cycles must not inflate the independent-battery count or leak into training and validation folds.
- **7,565 operation records:** 2,815 charge, **2,794 discharge** and 1,956 impedance records. Nine source README/protocol documents are retained. Recorded ambient values are **4, 22, 24, 43 and 44°C**; load profiles, stop voltages and cycling histories differ.
- All 2,794 discharge traces have finite adjacent electrical samples and strictly increasing time for the implemented integral. This is a **structural integration check, not proof of experimental accuracy or mission applicability**. Actual median sampling steps vary by record, roughly **9.34–18.72 s**; no assumed fixed 10 Hz resampling is introduced.
- **25 reported capacities are missing**: four B0050 and 21 B0052 records have empty source capacity arrays. Another **19 source records explicitly report zero capacity**. Both situations are retained distinctly; missing values are not filled with zero and unusual low-capacity records are not removed.
- **Nine impedance records contain complex-valued Re and Rct estimates** (eight B0049, one B0051). Their real and imaginary components remain in exports with a `complex_estimate` flag; they are excluded from real-resistance summaries, not converted to magnitudes or silently stripped of imaginary parts. Frequency vectors are not supplied, so no frequency-labelled impedance fit is claimed.
- **Declared example B0005:** over 168 recorded discharges, reported capacity changes from **1.8565 to 1.3251 Ah**. The full-record observed discharge-energy integral changes from **6.6088 to 4.6110 Wh**, about **30.23% lower** at the final record. These are this cell's experimental results, not a universal ageing law or our mission's usable battery capacity.
- B0042–B0044 each contain **41 discharge records labelled 22°C**, alongside 4°C records, even though their README group describes a nominal 4°C experiment. The notebook preserves record-level conditions instead of replacing them with the README's nominal condition. For B0038–B0040 the recorded ambient changes between 24°C and 44°C. These histories do not isolate a causal temperature effect from age/load/protocol changes.

**Evidence:** Dar_015 `operation_records.csv.gz`, `discharge_features.csv`, `cell_summary.csv`, `cell_ambient_condition_summary.csv`, `impedance_parameter_summary.csv`, protocol files and rendered plots. The energy calculation integrates `max(-I,0)` and `V × max(-I,0)` with seconds converted to hours; it uses valid adjacent endpoints only. A full-record integral can differ from source-reported capacity because it includes the recorded tail/rest/noise and may use a different effective endpoint definition. Differences are diagnostics, not automatically corruption.

### P1 reference findings — soil evidence and geometry-sensitive interpretation

**94 source rows across six tests; six `-9.99` stress entries are label-defined not-applicable values**, not negative stress. The decoder preserves original fields, raw records and sequence, while adding an explicit conversion of **1 N/cm² = 10 kPa**.

| Run | Geometry / context | Rows | Maximum force (N) | Maximum source stress (kPa) | Maximum uncorrected penetration (cm) | Documented limitation |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | Cone; north trench end | 16 | 110.9 | 344 | 9.14 | No run-specific depth warning in the cited source note. |
| 2 | Cone; trench bottom | 18 | 111.0 | 344 | 10.87 | No run-specific depth warning in the cited source note. |
| 3 | Cone; rover tracks | 16 | 110.3 | 342 | 6.30 | Depth-reference-pad problem. |
| 4 | Cone; adjacent to tracks | 18 | 111.8 | 347 | 11.97 | Depth-reference-pad problem. |
| 5 | Plate; trench bottom | 11 | 110.0 | 34.1 | 9.77 | Depth-reference-pad problem. |
| 6 | Plate; outside trench | 15 | 110.5 | 34.3 | 6.93 | Depth-reference-pad problem and documented trench-edge collapse. |

Maximum forces are similar (**110.0–111.8 N**), but cone and plate maximum stresses differ by roughly a factor of ten. Their nominal contact areas also differ by roughly ten (**3.22 versus 32.258 cm²**). This is a geometry-dependent comparison, not evidence that one test location is ten times stronger. Stress is already derived from load/contact area; the ratio check is not independent validation of soil strength.

The cone corrected-depth field differs from uncorrected depth by **3.75 cm**; the plate records do not have that correction and are not given one. Runs 3–6 retain the source warning that depth can be overestimated because the reference pad moved. Run 6's collapse is documented in the source, not newly detected from a fitted classifier. All tests share one historical Apollo 15 site; they are not six independent polar regions. Maximum tabulated stress is **not allowable foundation pressure**.

**Evidence:** Dar_016 `decoded_soil_records.csv`, `source_field_units.csv`, `run_summary.csv`, `cone_correction_check.csv`, `algorithm_reference_features.csv` and geometry-separated plots. The shared PDS4 reader received a backward-compatible fix to select the numeric table's own file area when a product also declares a supplemental text header. Existing reader tests remain unchanged and pass.

### Interpretation boundary

The implemented Ah/Wh integration and geometry-aware soil decoding provide reference features and method checks, not our mission's battery capacity or polar bearing limits. See [the proposal](../Brief_Overview.md#6-eda-evidence--environmental-criteria-and-methods) for future operational use; grouped-by-cell validation and probe/contact-area distinctions must be preserved.

### Execution and verification

Both notebooks executed in fresh project-Python kernels with saved outputs and no error cells. A B0005 pilot and cone/plate reader samples were checked before full processing. **The reference batch passed its targeted tests**, including the existing tests and new archive, missingness, integration, complex-estimate and supplemental-file-area cases. [Reference EDA verification](../data/verification/reference_eda_final/verification.json) checks output sizes/SHA-256, duplicate identities, counts, decoded units/flags, source receipts and an independent B0005 energy recomputation.

**Current conclusion:** the new datasets provide useful experimental reference features and reveal important quality/protocol constraints. They do not remove the need for a selected mission/equipment profile or polar-site response evidence. Authenticated sources remain KIV; no original downloads, prior notebooks or CSV priorities/statuses were replaced.

## 9. Lunar base-location comparison — executed 7 November 2026

**Question:** how can our environmental evidence help select a lunar base location, together with terrain and the pipeline's hard/soft-rule pattern? The new notebooks compare existing locations and test whether useful environmental/terrain conditions occur at the **same sampled centers**, rather than treating separate regional advantages as a ready-made base score.

| Notebook | Executed work | Accepted output run |
| --- | --- | --- |
| [Dar_017 — regional profiles](Moon/Site_Assessment/Dar_017_lunar_base_environment_profiles.ipynb) | Seven regions, 55,380 distinct regional centers, nine static fields across three cohorts (**189 profiles**), plus thermal profiles using **17 common products**. | `data/processed/analysis/dar_017_lunar_site_profiles/20261106T163555259282Z_731d59/` |
| [Dar_018 — joint trade-offs](Moon/Site_Assessment/Dar_018_joint_environment_terrain_tradeoffs.ipynb) | **567** region/cohort/diagnostic combinations, center maps, **1,071** thermal class summaries, **254** supported same-product joint-versus-other contrasts and criterion-ready evidence. | `data/processed/analysis/dar_018_joint_base_environment/20261106T163600510960Z_762655/` |

### P1 — Regional strengths have terrain and thermal trade-offs

Static columns below are **medians at observed regional centers**, not whole-region averages. Visibility is a fraction, not measured mission availability. Temperature is the **median of 17 common products' spatial medians**, with equal product weight—not a dated temperature, duration average, minimum or maximum.

| Region | Observed centers | Solar visibility median | Earth visibility median | Slope median (°) | Thermal summary (K) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Leibnitz Beta Plateau | 4,422 | 0.260 | 0.485 | 11.29 | 84.73 |
| Malapert Massif | 7,569 | 0.380 | 0.438 | 17.79 | 110.67 |
| deGerlache–Kocher Massif | 6,972 | 0.241 | 0.294 | 14.69 | 94.81 |
| Haworth | 15,500 | 0.238 | 0.407 | 9.99 | 83.08 |
| Faustini Rim A | 6,972 | 0.158 | 0.425 | 9.64 | 51.44 |
| deGerlache Rim 2 | 6,889 | 0.350 | 0.518 | 12.41 | 90.30 |
| Connecting Ridge Extension | 7,056 | 0.248 | 0.130 | 14.41 | 88.38 |

- **Malapert has the highest sampled median solar visibility, but also the steepest median slope.** A light-related advantage is not automatically a terrain advantage.
- **deGerlache Rim 2 has the highest median Earth visibility**, but no fixed-center thermal cohort across the 17 common products. Useful geometric context and incomplete comparable thermal support must coexist in its record.
- **Faustini has the lowest median slope and solar visibility.** Its lower thermal summary is not inherently better: acceptable temperatures depend on actual activities/equipment.

**Evidence:** Dar_017 `seven_region_environment_comparison.csv`, `regional_static_profiles.csv`, `region_support.csv`, `common_product_thermal_profiles.csv` and the distribution/phase plots. Full profiles also retain shadow, sky view, elevation and LOLA quality fields; no field is discarded merely because it is absent from this compact table.

### P1 — Evaluate environmental conditions together with terrain

Dar_018 sweeps solar and Earth visibility cuts of **0.25, 0.50 and 0.75**, and slope ceilings of **5°, 10° and 15°**, separately for available, positive-LOLA-spot and fixed-common cohorts. These are **predeclared diagnostic choices, not adopted hard constraints, scientific safety limits or preference weights**.

For the illustration **solar ≥0.50, Earth visibility ≥0.50 and slope ≤10°**, the observed-center results are:

| Region | Centers meeting all three / finite-context centers | Observed-center fraction |
| --- | ---: | ---: |
| Leibnitz Beta Plateau | 64 / 4,422 | 1.447% |
| Malapert Massif | 89 / 7,569 | 1.176% |
| deGerlache–Kocher Massif | 14 / 6,972 | 0.201% |
| Haworth | 23 / 15,500 | 0.148% |
| Faustini Rim A | 3 / 6,972 | 0.043% |
| deGerlache Rim 2 | 32 / 6,889 | 0.465% |
| Connecting Ridge Extension | 9 / 7,056 | 0.128% |

These are **not percentages of usable land**, contiguous base footprints or simultaneous Sun/Earth availability. Region center counts and observation support differ; the table is not a base ranking.

**Why joint analysis matters:** five of the 189 available-cohort parameter combinations have positive counts for every individual condition but **no center meeting all three**. For example, at Malapert with solar ≥0.75, Earth visibility ≥0.50 and slope ≤5°, there are **2**, **3,738** and **329** individually matching centers respectively, but **zero joint matches**. These five combinations are not five independent observations; the high-solar marginal is only two sampled centers. The result demonstrates why separately favourable factors cannot simply be added as evidence of a co-located base opportunity.

**Evidence:** Dar_018 `joint_condition_sweep.csv`, `illustrative_joint_conditions.csv`, `illustrative_joint_center_maps.png` and `marginal_versus_joint_conditions.png`. Map coordinates locate sampled centers; no connected-area or minimum-buildable-footprint claim is made.

### P1 — Thermal relationships need matched phases and cohort checks

The illustrative joint subset is compared with **other measured-context centers in the same region and source product**. Missing context has its own class and never becomes a failed condition or a valid comparison group. All products/classes/cohorts remain indexed, including empty groups with NaN temperatures.

- Malapert's median **joint-minus-other temperature contrast** across 17 products is **+24.70 K** for available centers, but **−2.49 K** for the fixed-common cohort. These are different selected populations, not a causal temperature reversal or a universal effect of illumination.
- Haworth's corresponding contrasts are **+49.05 K** available versus **+17.96 K** fixed-common, each over 17 products.
- Faustini's illustrative joint subset contains **at most three centers**, with both groups observed in only **11 of 17 products**. Its large apparent contrasts cannot be interpreted as robust whole-region or hardware-response results.
- Three regions have **no fixed-common thermal cohort**. At Leibnitz and Faustini the fixed-common cohort exists, but contains **zero centers in this illustrative joint subset**. These cases differ: absent cohort means an undefined fraction; an observed nonempty cohort with no joint matches has a defined zero fraction.
- Regional thermal support itself changes greatly: deGerlache–Kocher has **15–6,972** usable centers per common product; Faustini has **24–6,972**. Matching products alone does not fix changing locations.

**Algorithm consequence:** retain product/cohort identity, counts and ranges with thermal values. Do not turn these contrasts into cooling/heating corrections, equipment margins or scoring weights. Use fixed-center results as a sensitivity analysis, not as an assumption that unobserved sites are unsuitable.

**Evidence:** Dar_018 `joint_thermal_product_context.csv`, `matched_product_joint_temperature_contrasts.csv`, `joint_temperature_contrast_summary.csv`; Dar_017 `common_product_thermal_profiles.csv` and `static_cohort_sensitivity.csv`. Positive-spot sensitivity retains **228 versus 234** regional center records in the illustrated joint subset; it is a support diagnostic, not an adopted exclusion policy.

### Exported evidence and boundary

Dar_018 `environmental_rule_inputs.csv` contains **28 metric records, four per region**: solar, Earth visibility, slope and thermal context. They are Unconfigured/Unknown with NaN preference scores, not 28 adopted rules. `broader_reference_evidence.csv` retains radiation, battery, soil and seismic source-run records once each without invented local values. Subsequent diagnostic results are in section 10; algorithm consumption is specified in [the proposal](../Brief_Overview.md#10-how-the-eda-outputs-will-be-used-in-the-algorithm).

### Data sources, support and validation

Source chain: downloaded **D01 Diviner phase-average thermal products**, **D02–D04 illumination context**, **D06 LOLA elevation/slope/quality**, and the **D05 seven-region footprints** → accepted Dar_001/002 → Dar_012 context → Dar_017/018. Dar_018 rereads the original accepted **Dar_002 paired observations** for the thermal subgroups; it does not estimate temperatures from the regional profiles. Source labels and ancestor provenance retain the download identities.

Native support remains different: **240 m thermal**, **60 m solar/Earth/shadow**, **240 m sky view** and **40 m LOLA**. Containing-pixel lookups are technical joins, not proof of physical co-registration, full thermal-footprint coverage or whole-region representativeness. Static visibility is not a dated illumination/contact history, and cumulative phase-average temperature is not a mission extreme. The unfinished slope-error map remains excluded.

Both notebooks executed first on one region and then on all seven, with saved plots/tables and **no error cells**. **This batch includes eight tests for joint-versus-marginal evidence, repeated-center weighting, unknown context, empty cohorts, thermal group indexing, invalid joins and unconfigured rule inputs. [Independent verification](../data/verification/site_eda_final/verification.json) checks output sizes/SHA-256 and source hashes, independently recomputes all 189 static profiles and 567 joint masks, verifies thermal partitions, and checks one original Malapert source product's subgroup quantiles. [Fresh-kernel execution record](../data/verification/site_eda_execution_20261106T163552480956Z/verification.json).

**Conclusion:** the EDA now directly supports base-location comparison by exposing environmental–terrain trade-offs, co-location and evidence stability. It does not yet establish a safe footprint, power endurance, equipment limits or a final preferred location. Authenticated sources remain KIV; no existing downloads or earlier notebooks were replaced.

## 10. Expanded EDA — 32 questions and hard/soft rule influence

**Executed 7 November 2026.** The [32-question register](EDA_Notes.md#eda-question-register) maps every question to a notebook, source, output and algorithm implication. Questions are related diagnostics, not independent experiments. Existing data support spatial/profile/preference comparisons; missing operational requirements are explicitly reported, not fabricated.

### EDA → influence → implementation: what was coded and run?

| Notebook / questions | Implemented comparison | Output stage / accepted run |
| --- | --- | --- |
| [Dar_019 — connectivity](Moon/Site_Assessment/Dar_019_spatial_environment_connectivity.ipynb), Q01–08 | Native-source sampling, complete-cell grids, 27 joint cuts × four grid/origin cases × two adjacency definitions × seven regions = **1,512 cases**. | `dar_019_spatial_environment/20261106T175056432784Z_dfd0ab/` |
| [Dar_020 — candidate profiles](Moon/Site_Assessment/Dar_020_candidate_environment_profiles.ipynb), Q09–16 | **21** size-ordered component examples, **189** static distributions, **714** common-product/cohort thermal rows and same-center phase spans. | `dar_020_candidate_environment/20261106T175311055762Z_b68ce6/` |
| [Dar_021 — preferences](Moon/Site_Assessment/Dar_021_environment_preference_sensitivity.ipynb), Q17–24 | Separate **2,430-block** and **21-component** pools; Pareto comparisons and **30** weight/normalization scenarios per unit (**73,530 rows**). | `dar_021_preference_influence/20261106T175348058844Z_dc2517/` |
| [Dar_022 — gates/handoff](Moon/Site_Assessment/Dar_022_environment_hard_soft_rule_influence.ipynb), Q25–32 | **108** threshold/pool/cohort cases, marginal/joint availability, gate-first versus late filtering, **35 Unknown** operational readiness records and notebook lineage. | `dar_022_rule_influence/20261106T175355870393Z_4cebce/` |

Stages above are under `darrel stuff/data/processed/analysis/`. Sources: downloaded D02–D04/D06 rasters with hashes pinned to Dar_002, original D05 rectangles from Dar_001, original Dar_002 temperature observations, and accepted Dar_012/017 exports. Labels/scales/CRS are checked using the existing readers. The unfinished slope-error map is excluded. No new downloads, authentication, CNN training or final-reserve access occurred.

### P1 finding — favourable samples fragment into spatial zones

Primary illustration: **solar ≥0.5, Earth visibility ≥0.5, slope ≤10°**, on the **60 m unshifted analysis lattice with four-neighbour adjacency**. These are diagnostic cuts, not mission limits. Complete lattice cells remain inside each source rectangle.

| Region | Joint cells | Components | Single-cell components | Largest nominal projected component (km²) |
| --- | ---: | ---: | ---: | ---: |
| Leibnitz Beta Plateau | 869 | 160 | 65 | 0.5652 |
| Malapert Massif | 1,373 | 192 | 86 | 0.6264 |
| deGerlache–Kocher Massif | 274 | 46 | 17 | 0.1260 |
| Haworth | 367 | 79 | 51 | 0.2700 |
| Faustini Rim A | 117 | 30 | 13 | 0.0756 |
| deGerlache Rim 2 | 576 | 129 | 69 | 0.1764 |
| Connecting Ridge Extension | 227 | 62 | 34 | 0.0864 |

There are **880,466 primary-grid regional cells**, with finite sampled context in all nine fields. These are raster lookups, not that many independent measurements. The table contains **698 components, including 335 singletons**. Source resolution remains 60 m illumination, 240 m sky and 40 m LOLA; the analysis lattice does not create higher-resolution evidence.

**Sensitivity matters:** Haworth's largest component changes from **75 to 155 cells** when only adjacency changes from four to eight neighbours. Leibnitz's largest nominal projected extent changes from **0.5652 to 0.2880 km²** between 60 and 120 m lattices. Connecting Ridge Extension changes from **0.0864 to 0.1728 km²** between 60 and 240 m. Coarser cells can merge/alias spatial opportunities; a larger number is not proof of improvement. A half-cell shift is a separate origin control.

**Rule influence:** do not use total favourable-cell count as a minimum-footprint pass. A future footprint criterion needs a declared size/layout and validated spatial support, with grid/adjacency/boundary sensitivity. Component extent and the reported interior-distance proxy do not establish buildability, geodesic area, guaranteed minimum width, bearing capacity or physical co-registration. Evidence: `connectivity_threshold_grid_sweep.csv`, `illustrative_component_catalog.csv`, `illustrative_grid_connectivity_comparison.csv`, `native_source_grid_support.csv` and saved primary-grid cells/labels.

### P1 finding — smaller candidate units expose missing thermal evidence

Dar_020 selects the **three largest primary-illustration components in each region**, not the best base sites or a representative random sample. Their static profiles retain temperature-relevant illumination, slope/elevation, sky, shadow and terrain-quality context.

- **2 of 21 components have no associated usable thermal centers**: one Faustini example and one Connecting Ridge Extension example. This is a coverage/point-association result, not proof that a download is missing or the environment is unsuitable.
- Only **5 of 21** have some point-associated temperature observation in **all 17 common products**: three Malapert and two Haworth examples. This alone does not prove a fixed cohort or full spatial coverage.
- **73 distinct regional centers** are associated with the selected examples; **25** have all common products. Remaining phase groups stay indexed with NaN temperatures and zero observed counts.
- For Malapert component `00082`, the fixed-common versus available **median-of-product-medians difference is −11.35 K**. It is a cohort-selection effect, not an equipment correction or temperature change over elapsed time.
- All sampled cells in these selected components have PSR class **0**; this describes the illumination-conditioned pool, not all candidate locations. **10 of 21** components include at least one sampled zero-LOLA-spot value. Finite terrain is not proof of a local laser measurement.

**Rule influence:** use location-qualified profiles, explicitly choose the statistic required by each criterion (median/q90/maximum are different), and propagate missing or sparse thermal support. Do not fill absent groups with regional medians or zero. A containing 60 m cell associates only the **thermal center**; it does not contain/validate the full 240 m observation footprint. Phase-average spans are not chronological mission extremes or heating rates. Evidence: candidate static/thermal profiles, `candidate_thermal_association_support.csv`, `candidate_thermal_cohort_comparison.csv` and `associated_center_phase_spans.csv`.

### P1 finding — soft rankings depend on preference definitions

The two pools stay separate. Solar/Earth proxies are medians and slope is q90. Higher solar/Earth and lower slope are **declared diagnostic preferences**, not universal design truths. Fifteen weight triples in increments of 0.25 are compared under two transformations: documented fraction/degree domains, and ranks within the fixed pool. Physical-domain slope benefit is `1 − slope/90`; that scaling choice is also a diagnostic, not a safety function.

- **24 of 2,413 supported blocks** are nondominated across these three proxies; **17 empty blocks remain Unknown**. In the component pool, **13 of 21** are nondominated. Dominance does not establish operational eligibility or justify discarding evidence about other factors.
- Under weights **(solar 0.25, Earth 0.25, slope 0.50)**, the component pool's physical-domain and percentile **top-five sets have zero overlap**. The data did not change; the scoring definition did.
- Across all 15 weight triples, median top-five Jaccard overlap between transformations is **0.429 for blocks** and **0.667 for components**, with minima **0 in both pools**. Scenario frequency is not a probability that a site is best.
- Missing metrics produce no score, even at zero-weight boundaries; no silent missing-criterion renormalization is used. Diagnostic rank sets preserve ties and can contain more than five units.

**Rule influence:** inspect Pareto trade-offs and normalization/weight sensitivity before adopting a preference function. Keep preference scores separate from hard requirements and terrain similarity; avoid rewarding slope twice. No numerical preference policy was selected from these results. Evidence: `pareto_dominance.csv`, `diagnostic_preference_scenarios.csv.gz`, `normalization_comparison.csv`, `diagnostic_rank_stability.csv`, metric correlations and regional representation.

### P1 finding — hard gates must precede top-k selection

Dar_022 compares explicit proxy conjunctions with the same fixed units and diagnostic weights **(0.25, 0.25, 0.50)**. Here top-k retains **at most five**, sorted by diagnostic score then unit ID; that deterministic comparison is distinct from Dar_021's tie-inclusive rank sets.

| Counterfactual example | Measured result | Algorithm consequence |
| --- | --- | --- |
| Block solar median ≥0.25, Earth median ≥0.50, slope q90 ≤5° | **8** of 2,430 blocks meet the proxy conditions; **none** are in the ungated top five. Gate-first returns five, while late filtering returns zero. | Apply configured mandatory eligibility to the full candidate pool before top-k ranking; late filtering can hide qualifying alternatives. |
| Block solar median ≥0.50, Earth median ≥0.50, slope q90 ≤10° | **1 DiagnosticMet, 2,412 DiagnosticNotMet, 17 Unknown**. | Preserve no-match and Unknown states; a compensating soft score is not a mandatory conjunction. |
| Same illustration, fixed-common block cohort | **0 DiagnosticMet, 500 DiagnosticNotMet, 1,930 Unknown**. | Changing the evidence cohort changes support and summaries, not the physical environment. Do not call missing fixed-cohort evidence a physical failure. |
| Component examples under their original selection cuts | All **21 DiagnosticMet**, by construction. | This is not independent validation of the cuts or proof that these are better than the differently grained block pool. |

Late filtering hides qualifying proxy units in **9 of 27 block scenarios** and **4 of 27 component scenarios**, with maximum top-five deficits **5 and 4** respectively. Across the four pool/cohort cases, **56 of 108 scenarios** have no matching proxy unit; no fake candidate is supplied. These scenarios are related, not independent trials or validated operating cases.

**Actual readiness is separate:** five proposed operational checks × seven regions = **35 Unknown records**, covering power endurance, component thermal margin, communications continuity, radiation protection and an applicable footprint requirement. Their limits, response/scenario inputs or layout requirements are not supplied by static rasters. `DiagnosticMet`/`DiagnosticNotMet` are not operational Passed/Failed. No operational score was computed.

### Relation to the existing workflow

The diagnostics reuse notebooks 31–32's declared-control and fixed-pool availability/ranking comparisons. `eda_to_algorithm_lineage.csv` records the mapping. The tested [helper](environmental_selection_eda.py) supplies diagnostic methods; root notebooks/CNN/demo behaviour remains unchanged. Planned consumption, configuration and implementation order live in [the proposal](../Brief_Overview.md#10-how-the-eda-outputs-will-be-used-in-the-algorithm).

### Validation and remaining boundaries

All four notebooks passed representative one-region runs before seven-region execution, with saved output and no final error cells. A sample plotting issue involving an all-missing cohort was fixed using explicit numeric candidate positions; missing thermal values were preserved. **65 targeted EDA tests pass**, including 17 new cases for grid bounds, connectivity/area arithmetic, unknown masks, control equivalence, shuffled identities, point association, absent thermal groups, Pareto ties, missing scores, gate semantics and late-filter failure.

[Independent verification](../data/verification/extended_environment_final/verification.json) checks input/output sizes and SHA-256, notebook execution, all seven saved primary-grid label maps, direct raw-raster sample agreement, candidate static quantiles, missing thermal groups, phase-span arithmetic, preference/gate calculations and actual Unknown readiness. [Full fresh-kernel execution record](../data/verification/extended_environment_execution_20261106T175053002941Z/verification.json).

No adopted hard limits, weights, chosen base size, equipment margins, physically validated full footprints or final safe/best-site claim were generated. Existing source data and notebooks Dar_001–018 were preserved; authenticated sources remain KIV.

## 11. Core and wider P1 execution record

These established findings were consolidated from the work plan so numerical evidence has one home. Dar_001–003 accepted runs are `20261106T082643415392Z_4e6a0b`, `20261106T082929336242Z_623f9f` and `20261106T082730253024Z_45fcca`. Dar_001 reuses verified raw-preparation exports from `20261106T081135919918Z_54e79b`, recalculating local-time validity and cohort sensitivity; set `PREPARED_RUN_ID=None` only when rebuilding from raw inputs.

[Core verification](../data/verification/dar_p1_final_20261106T083530Z/verification.json) and [wider P1 verification/accepted runs](../data/verification/research_p1_final_20261106T094423Z/verification.json) retain execution and provenance evidence. Current test status is recorded once in the work plan; earlier test-batch totals are not separate current suites.

### Findings from the executed core P1 EDA

| Finding | Evidence / implication for Stage 3 |
| --- | --- |
| **144 lunar phase products; 4,825,369 usable center–product rows across 55,380 distinct regional native centers.** | Dar_001 `product_coverage.csv`, `local_time_temperature.csv` and `findings.json`. These are repeated phase-average observations, not independent exposure trials or dated mission temperatures. Lunar local hour is a cyclic phase coordinate, not elapsed Earth mission hours. |
| **243 of 1,008 region/product combinations have no selected rows. Only 17 products contain usable data in every region.** | Dar_001 coverage tables. Zero invalid temperatures among observed rows does not establish complete coverage: source tables omit empty bins. Do not fill absent phases with zero or infer mission extremes. |
| **Only four of seven regions have a complete fixed-cell cohort over those 17 common products.** | Dar_001 `cohort_coverage.csv` and matched-product `cohort_sensitivity.csv`. Complete-common cohorts are absent for deGerlache–Kocher, deGerlache Rim 2 and Connecting Ridge Extension; report this selection limitation rather than forcing a comparison. |
| **11 raw local-time values equal exactly 24.0.** | Dar_001 retains raw `ltim`, normalizes only this exact endpoint to midnight (`local_time_h=0`), and counts conversions. Other invalid values are not arbitrarily wrapped. |
| **All nine selected environmental/quality rasters have finite lookups at the 55,380 observed regional centers, but 3,101 centers have zero LOLA spots in the sampled 40 m pixel.** | Dar_002 `join_coverage.csv` and `native_center_quality_support.csv`. A finite derived terrain value is not proof of a local laser measurement, full thermal-footprint coverage or physical co-registration. Zero counts are retained, not silently converted to good support or used to remove terrain values. |
| **3,818 supported within-product descriptive correlations were calculated.** | Dar_002 `within_product_correlations.csv`, plus local-hour, PSR-class, predictor-band and matched-product cohort-sensitivity tables. Inspect region/phase support and quality before interpretation; these associations are not causal effects or algorithm weights. |
| **Median within-product temperature–solar-visibility correlations are positive in all seven regions (Spearman rho approximately 0.455–0.784). Other relationships vary by region and phase.** | Available-cell comparisons in Dar_002. For example, median sky-view correlation is negative at Malapert but positive at Leibnitz Beta Plateau; several phase-product spreads cross zero. This supports keeping region/phase and quality context rather than assigning one universal environmental weight. |
| **Earth EDA verifies 3,000 regional monthly summaries: five variables, five sites, 120 months; 50 annual precipitation totals. Lanzarote has 65 jointly complete centers out of 180 selected centers.** | Dar_003 coverage/seasonal/spatial tables preserve the coastal gaps rather than filling them. Four other sites have complete selected-center support in this collection. Earth air climate remains separate from lunar surface brightness temperature. |

The notebooks contain the executed plots and tables; full generated exports remain in the isolated run directories above. Missing mission/equipment limits, dated exposure histories and the unfinished slope-error support remain unresolved. These findings do not mark a Stage 3 requirement as Passed.

Dar_001/002 read SDEM ZIP **headers only** for the original footprints and use available raw illumination labels directly. Dar_006 additionally reads bounded native SDEM patches and image-count masks inside the ZIPs, without extracting whole archives or replacing the existing 05/13 pipeline. The unfinished LOLA slope-error map is explicitly excluded; no slope-error result or complete terrain-support restoration is claimed. Other complete D06 maps remain in the relationship/quality analysis.

### Findings from the wider research runs

- **D20:** the two RDR files contain **1,771,686 rows**, but **zero all-zero-quality rows** and **zero footprints below 80°S**. The plotted channel/local-time results are explicitly flagged diagnostics, not accepted seven-region thermal histories. Channels 1/2 are never treated as kelvin.
- **D28/D38:** Apollo supplies **34,838 bridge records** (34,819 in the conservative clean cohort), **187,882 depth-series rows** and **176,233 simultaneous sensor-gradient pairs**. GCP contains **1,382,400 rows**, including **122,405 missing bolometric values**. Neither dataset supplies polar mission extremes.
- **D07/D08/D31:** CRaTER contributes **172,800 SEC counter records**, not LET spectra. All **14,976 GOES channel/time rows** carry the dynamic-error flag; the explicit zero-flag filter accepts **none**, so accepted fluence remains **NaN, not zero**. REDMoon provides **48 scenario profiles / 14,448 depth rows**; its 148 observed monthly rows and 164 modeled monthly rows are parsed separately, with 148 overlapping months. Observed annualized absorbed rates and modeled effective-dose profiles keep their different units and meanings.
- **D05/D06/D26:** seven **1.2 km × 1.2 km central patches** and **6,109 within-product quality-band comparisons** were analysed. The two Kaguya pilots are equatorial and do not overlap the polar regions; no fabricated paired DEM accuracy comparison is reported.
- **D13/D14:** the two catalogs have **58 and 59 entries**, not 117 independent new events. The MHZ pilot has **404,020 samples**, including **72,084 encoded missing samples in 279 runs**, despite zero inter-trace gaps. ATT has **17,805 encoded missing samples**. Missing values are not interpolated; the PSD uses a nonmissing contiguous count-domain segment and is not a calibrated noise floor.
- **D15/D27/D33:** both NAC observations retain **quality ID 2**. The ShadowCam center is approximately **81.412°N** and its absolute physical unit is unconfirmed in the supplied map metadata. The crater catalog contains **222 detections**; observation brackets and surveyed search effort are not supplied by the identifiers alone.
- **D16/D19:** both LCROSS exposures are unsaturated **PREIMPACT** spectra with 100 wavelength samples, approximately **1.1693–2.4786 µm**. The SPICE benchmark has **10,080 modeled rows** (720 UTC epochs × seven centers × two targets); all 14 topocentric checks agree within numerical precision. The UTC grid excludes the scenario stop time; ET/TDB conversion is performed per UTC epoch.
