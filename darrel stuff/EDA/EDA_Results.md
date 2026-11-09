# Decision-facing Moon EDA results

**Current downstream handoff - 9 November 2026:** [workflow Steps 4-5](../research/STEP_4_5_PROTOTYPE.md) are complete with optional mission/equipment inputs, unchanged existing-data scores, a scoped evidence/rule register and explicit candidate limitations. Historical EDA measurements and scope statements below remain unchanged; Step 6 is deferred.

**Current priority: Required Stage 3, then research P1/P2/P3. Latest continuation: 8 November 2026.** Start with the [required Stage 3 consolidation](#14-golden-stage-3-revamp). Sections 1–13 retain their original measured scope and accepted runs; their historical “no new downloads/implementation” statements do not describe the new reference acquisition and Stage 3 models. No mission profile or operating limit has been invented/adopted.

The goal is to help select a Moon base location by preparing reliable environmental evidence for [Stage 3](../../outline.md#stage-3--environmental-and-equipment-suitability-engine), considered together with terrain and mission/equipment requirements. We aim to supply location-specific profiles and explainable hard/soft-rule inputs—not declare a site safe or rank missions without requirements.

## 1. What was implemented

| Notebook | Completed analysis | Inputs |
| --- | --- | --- |
| [Dar_012 — joint environmental context](Moon/Environmental_Context/Dar_012_joint_environmental_context.ipynb) | Joint temperature/illumination/terrain fields; explicit missing phases; spatial coverage; changing versus fixed observation cohorts. | D01–D06 through accepted Dar_001/002 exports and original seven footprints; slope-error layer excluded from this run. |
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

**Authenticated sources remain KIV:** P1 **D21 ChaSTE** and **D23 ILSA** were not retrieved. Existing gated D22/D24 entries outside P1 are also unchanged. Project M-records are mission/equipment data to supply or generate, not hidden environmental-download files. The slope-error layer is excluded from the cited runs; its current usability requires a separate audit.

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

The prototype implements terrain-resemblance retrieval, not a completed base-suitability engine. The proposed environmental layer and remaining integration inputs are summarised in [the proposal](../purposal.md#3-what-to-recommend).

## 6. Findings → concrete implementation methods

Proposed methods and processing order are centralised in [the algorithm proposal](../purposal.md#5-what-else-is-needed). This report records observed comparisons and their limits; it does not define a second set of thresholds, weights or implementation instructions.

## 7. Can missing evidence come from online sources?

Public observations/reference tests, scenario-generated outputs and selected mission/equipment configuration are different evidence types. The [research report's source/gap review](../research/Research_Notes.md#public-sources-and-remaining-evidence-gaps) now holds the source routes and access caveats. R01/R02 were subsequently downloaded and analysed in section 8; authenticated sources remain KIV.

## 8. New datasets — executed reference EDA (7 November 2026)

Dar_015/016 read the R01/R02 downloads and verified receipts under `darrel stuff/data/reference/`. Reference-experiment results remain separate from local lunar-site measurements.

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

The implemented Ah/Wh integration and geometry-aware soil decoding provide reference features and method checks, not our mission's battery capacity or polar bearing limits. See [the proposal](../purposal.md#5-what-else-is-needed) for future operational use; grouped-by-cell validation and probe/contact-area distinctions must be preserved.

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

Dar_018 `environmental_rule_inputs.csv` contains **28 metric records, four per region**: solar, Earth visibility, slope and thermal context. They are Unconfigured/Unknown with NaN preference scores, not 28 adopted rules. `broader_reference_evidence.csv` retains radiation, battery, soil and seismic source-run records once each without invented local values. Subsequent diagnostic results are in section 10; algorithm consumption is specified in [the proposal](../purposal.md#3-what-to-recommend).

### Data sources, support and validation

Source chain: downloaded **D01 Diviner phase-average thermal products**, **D02–D04 illumination context**, **D06 LOLA elevation/slope/quality**, and the **D05 seven-region footprints** → accepted Dar_001/002 → Dar_012 context → Dar_017/018. Dar_018 rereads the original accepted **Dar_002 paired observations** for the thermal subgroups; it does not estimate temperatures from the regional profiles. Source labels and ancestor provenance retain the download identities.

Native support remains different: **240 m thermal**, **60 m solar/Earth/shadow**, **240 m sky view** and **40 m LOLA**. Containing-pixel lookups are technical joins, not proof of physical co-registration, full thermal-footprint coverage or whole-region representativeness. Static visibility is not a dated illumination/contact history, and cumulative phase-average temperature is not a mission extreme. The slope-error layer is excluded from the cited runs; its current usability requires a separate audit.

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

Stages above are under `darrel stuff/data/processed/analysis/`. Sources: downloaded D02–D04/D06 rasters with hashes pinned to Dar_002, original D05 rectangles from Dar_001, original Dar_002 temperature observations, and accepted Dar_012/017 exports. Labels/scales/CRS are checked using the existing readers. The slope-error layer is excluded from these runs. No new downloads, authentication, CNN training or final-reserve access occurred.

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

The diagnostics reuse notebooks 31–32's declared-control and fixed-pool availability/ranking comparisons. `eda_to_algorithm_lineage.csv` records the mapping. The tested [helper](environmental_selection_eda.py) supplies diagnostic methods; root notebooks/CNN/demo behaviour remains unchanged. Planned consumption, configuration and implementation order live in [the proposal](../purposal.md#3-what-to-recommend).

### Validation and remaining boundaries

All four notebooks passed representative one-region runs before seven-region execution, with saved output and no final error cells. Targeted checks cover grid bounds, connectivity/area arithmetic, unknown masks, control equivalence, shuffled identities, point association, absent thermal groups, Pareto ties, missing scores, gate semantics and late-filter failure. The latest suite total is recorded in section 12.

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

The notebooks contain the executed plots and tables; full generated exports remain in the isolated run directories above. Missing mission/equipment limits and dated exposure histories remain unresolved; slope-error support was not assessed in these runs. These findings do not mark a Stage 3 requirement as Passed.

Dar_001/002 read SDEM ZIP **headers only** for the original footprints and use available raw illumination labels directly. Dar_006 additionally reads bounded native SDEM patches and image-count masks inside the ZIPs, without extracting whole archives or replacing the existing 05/13 pipeline. The LOLA slope-error layer is explicitly excluded from these runs; no slope-error result or complete terrain-support restoration is claimed. Other complete D06 maps remain in the relationship/quality analysis.

### Findings from the wider research runs

- **D20:** the two RDR files contain **1,771,686 rows**, but **zero all-zero-quality rows** and **zero footprints below 80°S**. The plotted channel/local-time results are explicitly flagged diagnostics, not accepted seven-region thermal histories. Channels 1/2 are never treated as kelvin.
- **D28/D38:** Apollo supplies **34,838 bridge records** (34,819 in the conservative clean cohort), **187,882 depth-series rows** and **176,233 simultaneous sensor-gradient pairs**. GCP contains **1,382,400 rows**, including **122,405 missing bolometric values**. Neither dataset supplies polar mission extremes.
- **D07/D08/D31:** CRaTER contributes **172,800 SEC counter records**, not LET spectra. All **14,976 GOES channel/time rows** carry the dynamic-error flag; the explicit zero-flag filter accepts **none**, so accepted fluence remains **NaN, not zero**. REDMoon provides **48 scenario profiles / 14,448 depth rows**; its 148 observed monthly rows and 164 modeled monthly rows are parsed separately, with 148 overlapping months. Observed annualized absorbed rates and modeled effective-dose profiles keep their different units and meanings.
- **D05/D06/D26:** seven **1.2 km × 1.2 km central patches** and **6,109 within-product quality-band comparisons** were analysed. The two Kaguya pilots are equatorial and do not overlap the polar regions; no fabricated paired DEM accuracy comparison is reported.
- **D13/D14:** the two catalogs have **58 and 59 entries**, not 117 independent new events. The MHZ pilot has **404,020 samples**, including **72,084 encoded missing samples in 279 runs**, despite zero inter-trace gaps. ATT has **17,805 encoded missing samples**. Missing values are not interpolated; the PSD uses a nonmissing contiguous count-domain segment and is not a calibrated noise floor.
- **D15/D27/D33:** both NAC observations retain **quality ID 2**. The ShadowCam center is approximately **81.412°N** and its absolute physical unit is unconfirmed in the supplied map metadata. The crater catalog contains **222 detections**; observation brackets and surveyed search effort are not supplied by the identifiers alone.
- **D16/D19:** both LCROSS exposures are unsaturated **PREIMPACT** spectra with 100 wavelength samples, approximately **1.1693–2.4786 µm**. The SPICE benchmark has **10,080 modeled rows** (720 UTC epochs × seven centers × two targets); all 14 topocentric checks agree within numerical precision. The UTC grid excludes the scenario stop time; ET/TDB conversion is performed per UTC epoch.

## 12. Terrain-source, thermal-support and conditional-relationship follow-up

**Executed 7 November 2026:** 18 additional questions, **Q33–Q50**, using existing local inputs. The [question/work register](EDA_Notes.md#eda-question-register) records their outputs. No extra downloads, archive extraction, model training or operational policy adoption occurred.

| Notebook | Completed work | Accepted output stage / run |
| --- | --- | --- |
| [Dar_023 — terrain-source sensitivity](Moon/Terrain_And_Soil/Dar_023_terrain_environment_source_sensitivity.ipynb) | 880,466 accepted 60 m analysis centres; 30 m image-supported SDEM versus 40 m LOLA; 42 paired-statistic rows, 126 source/classification comparisons and 21 component support records. | `dar_023_terrain_source_sensitivity/20261107T145756928578Z_6db171/` |
| [Dar_024 — nominal thermal support](Moon/Site_Assessment/Dar_024_nominal_thermal_bin_support.ipynb) | Label-confirmed nominal resolution; 219 centre/square-size records, 63 component/size summaries and 3,570 phase/cohort/overlap-cut summaries. | `dar_024_nominal_thermal_support/20261107T145811163440Z_091024/` |
| [Dar_025 — conditional relationships](Moon/Thermal/Dar_025_conditional_terrain_temperature.ipynb) | 2,142 region/product/cohort/predictor/control comparisons, retaining undefined fits; matched-row raw versus rank-residual associations. | `dar_025_conditional_terrain_thermal/20261107T145837258343Z_fcfe52/` |

Stages are under `darrel stuff/data/processed/analysis/`. New terrain input is the completed **05** run `lunar_terrain_environment/20261106T180253772848Z_40d3f3`, not a fresh execution of 05/13. Its processed slope/elevation/local-SD/image-support rasters are read with their existing native CRS/scales and 0.99 upstream image-support definition. Dar_012/017/019/020 and original Dar_002 observations remain pinned. The previously excluded LOLA slope-error raster is not used here.

### Terrain-source agreement does not guarantee identical diagnostic cuts

Across finite slope pairs, SDEM/LOLA Spearman correlations are high (**0.984–0.993**), with small median SDEM-minus-LOLA differences (**0.003–0.029°**). These are **source/processing comparisons, not independent accuracy validation**: resolution, neighbourhood, imagery support and potentially shared information differ; neither source is designated ground truth.

The 21 illustrative components were originally selected with LOLA slope ≤10° plus solar/Earth visibility ≥0.5. Sampling the completed SDEM products at the same component analysis centres gives:

| Region | Component analysis centres | Finite SDEM slope | Missing SDEM slope | Finite SDEM slopes >10° |
| --- | ---: | ---: | ---: | ---: |
| Leibnitz Beta Plateau | 258 | 246 | 12 | 2 |
| Malapert Massif | 434 | 374 | 60 | 15 |
| deGerlache–Kocher Massif | 81 | 81 | 0 | 1 |
| Haworth | 170 | 135 | 35 | 1 |
| Faustini Rim A | 50 | 32 | 18 | 0 |
| deGerlache Rim 2 | 129 | 69 | 60 | 3 |
| Connecting Ridge Extension | 65 | 53 | 12 | 2 |
| **Total** | **1,187** | **990** | **197** | **24** |

**18 of 21** examples have some missing image-supported SDEM slope. **11 of 21** contain at least one finite SDEM slope above the illustrative 10° cut, but only **one** has a finite-sample q90 above 10° and **none** has a median above 10°. A median, upper quantile and maximum are not interchangeable. These observations are not operational failures; missing derivative support is not proof of physically worse terrain. No source is selected because it produces a preferred result.

Evidence: `sdem_sampling_coverage.csv`, `terrain_source_pair_statistics.csv`, `slope_source_classification.csv`, `candidate_sdem_support.csv`, selected case-cell exports and `solar_band_sdem_roughness.csv`. The local-SD field uses the source run's 11-cell window on its 30 m grid; it is not a rock-abundance or wheel-scale obstacle measurement. Full-context terrain views from notebook 13 are not claimed complete.

### Centre association does not establish local thermal containment

The downloaded Diviner XML explicitly describes observations **binned at 240 m resolution**. Dar_024 tests declared axis-aligned nominal squares of **120, 240 and 480 m** around accepted projected centres against the primary 60 m component lattice. It does **not** reconstruct an exact native affine/grid origin, radiometer FOV, geodesic footprint or physical co-registration. The alternative sizes and overlap cuts are diagnostics, not new instrumental resolutions or approved quality limits. Source normalized-coordinate descriptions/unit tags are not used to infer a new conversion.

For the **73 associated centres** in 19 component examples, **zero nominal 240 m squares** lie fully inside their associated illustrative component. Median component overlap is **0.5625** under the declared square/lattice model. The other two examples have no associated thermal centres and therefore supply no containment test. This does not invalidate the temperature dataset or rule out the regions; it limits a local interpretation for these narrow, irregular, condition-selected examples.

| Minimum nominal 240 m overlap — diagnostic only | Examples with any common-product temperature | Examples with all 17 products | Available centre–product rows |
| --- | ---: | ---: | ---: |
| 0.00 — original centre association | 19 | 5 | 1,068 |
| 0.25 | 19 | 5 | 1,044 |
| 0.50 | 17 | 5 | 781 |
| 0.75 | 7 | 5 | 214 |
| 1.00 | 0 | 0 | 0 |

The **zero-cut identity control reproduces all 714 Dar_020 candidate/product/cohort rows**, including counts and temperature quantiles. Empty groups remain zero-count/NaN, not zero temperature. Overlap is used only to describe support and select declared diagnostic cohorts: it is **not a weight for unmixing brightness temperature** or a basis for inventing small-footprint temperatures. Evidence: nominal-overlap summaries and `overlap_conditioned_thermal_profiles.csv` / `overlap_cohort_support.csv`.

### Terrain–temperature associations depend on the chosen controls and cohort

Dar_025 joins image-supported SDEM features directly at the accepted native thermal centres, rather than assigning a neighbouring 60 m sample. It keeps each region and the same 17 phase products separate, with available, positive-LOLA-spot and fixed-common cohorts.

Temperature, terrain predictor and solar visibility are ranked. The second control design adds **unranked sine/cosine local-time features**: ranking both monotone cyclic features in a narrow local-time interval can make them artificially collinear, so their explicit cyclic basis is preserved. Reported values are rank-residual associations under those chosen bases, not a claim that all illumination/geometry effects have been removed. Fits require **20 complete rows** as a predeclared numerical/descriptive safeguard, not 20 independent trials or a mission requirement.

For SDEM local elevation SD, available-cohort medians over the supported products are:

| Region | Supported products | Same-row unadjusted rho | Solar + cyclic-local-time rank-residual rho |
| --- | ---: | ---: | ---: |
| Leibnitz Beta Plateau | 17 | 0.040 | 0.502 |
| Malapert Massif | 17 | 0.400 | 0.461 |
| deGerlache–Kocher Massif | 16 | 0.205 | 0.381 |
| Haworth | 17 | 0.129 | 0.353 |
| Faustini Rim A | 14 | 0.119 | 0.337 |
| deGerlache Rim 2 | 17 | 0.377 | 0.539 |
| Connecting Ridge Extension | 17 | 0.445 | 0.423 |

Positive medians do not mean every phase has a positive relationship: the **115 supported available-cohort roughness comparisons** under that control design range from **−0.414 to +0.849**, including **nine negative** values. Cohort choice also matters: Haworth's fixed-common median changes from **0.762 unadjusted to 0.616 conditional**, whereas its available-cohort comparison is **0.129 to 0.353**. These are selected populations, not physical warming or a causal roughness coefficient.

Of 2,142 indexed comparisons, **1,686** have descriptive fits and **456** have insufficient complete rows. The latter include absent cohorts and small nonempty groups; counts distinguish them and associations stay NaN. Constant-control, deficient-design and no-residual states are explicitly implemented/tested even though they did not occur in this full run. No p-values, prediction model, transferable temperature correction or scoring weights were produced. Evidence: `within_product_conditional_rank_relationships.csv`, supported-phase summaries, fit-status counts and native-centre SDEM support.

### Execution, validation and resource footprint

Each notebook ran first on one region, with actual table/mask/identity checks, then in a fresh kernel over all seven. The kernels ran **sequentially and were shut down after execution**; unrelated user kernels were not stopped. The largest sampled working-memory footprint of an individual owned kernel was **309 MiB**; this sampling is not a measurement of total system memory or an absolute peak guarantee. Full-run exported files total approximately **1.23 MiB**, excluding rendered notebooks and verification copies. The large terrain extraction/preprocessing was not repeated.

**76 targeted EDA tests pass**, including 11 new source-comparison, geometric intersection, missingness, label-evidence, residual-arithmetic, collinearity and cyclic-basis cases. Existing tests were not modified. [Independent verification](../data/verification/terrain_followup_final/verification.json) checks current input/output hashes, executed notebook validity, direct raw SDEM samples, nominal intersection arithmetic, all 714 identity-control rows, monotone overlap-cohort counts, empty groups, fit status/support and one original source-product residual calculation independent of the helper. [Full execution/memory record](../data/verification/terrain_followup_execution_20261107T145754066782Z/verification.json).

These studies add terrain-source, support and conditioning evidence—not new mission limits, physical co-registration, equipment margins or a completed location-selection engine. Proposed consumption remains in the [root algorithm proposal](../purposal.md); authenticated sources remain KIV.

## 13. Manual ShadowCam and Mini-RF incorporation

**Executed 8 November 2026.** The five user-supplied D27/D30 image/label files were registered **in place**, without copying, renaming or altering their bytes. [Manual inventory](../data/manifests/eda_datasets/20261107T182412585915Z/inventory.json) and per-file receipts retain URLs, sizes and local SHA-256 baselines—not publisher checksum verification. D27's valid `.xml.txt` is parsed as XML.

**Subsequent organization:** these files and receipts were moved into `data/moon/eda_pilots/D27/manual_M013049982S/` and `D30/manual_global_cpr_128ppd/`. Their [journal](../data/manifests/file_relocations.json) preserves original paths and hashes; the reader resolves the pinned inventory without changing these historical EDA outputs. A separate [environmental prototype](../Pipeline_Proto/README.md) now consumes qualified EDA exports; its illustrative rankings are not new scientific EDA findings.

| Notebook | Accepted analysis run under `data/processed/analysis/` | Scope |
| --- | --- | --- |
| [Dar_026 — manual ShadowCam](Moon/Dar_026_shadowcam_manual_environment.ipynb) | `dar_026_shadowcam_manual/20261107T183427316296Z_f95fd8` | One southern scene, native special pixels/patches and image values at existing regional context centres. |
| [Dar_027 — manual Mini-RF](Moon/Dar_027_minirf_cpr_environment.ipynb) | `dar_027_minirf_manual/20261107T183457581811Z_bc568a` | One global CPR mosaic, signed/nonnegative cohorts and seven-region environment/terrain comparisons. |

### Valid pixel support is not geometric overlap

At the **55,380 existing region-qualified thermal/context centres**, 18,827 fall inside the ShadowCam image rectangle, but only **1,455 have ordinary image values**, all in deGerlache Rim 2. The remainder inside comprises **16,948 NULL and 424 high-instrument-saturation pixels**. Centres outside the rectangle are reported separately. This is not a complete image census or proof that the other regions lack imagery.

The 64 fixed 64×64 native patches contain 262,144 pixels: **237,568 NULL, 16,328 ordinary, 8,149 HIS and 99 LIS**. These are a declared deterministic patch sample, not whole-scene or area-weighted fractions. Display overviews do not supply statistics.

| Region | Ordinary ShadowCam centres | Nonnegative CPR centres | CPR median | CPR–slope Spearman |
| --- | ---: | ---: | ---: | ---: |
| Leibnitz Beta Plateau | 0 | 4,422 | 0.4753 | −0.0820 |
| Malapert Massif | 0 | 7,568 | 0.5420 | 0.0947 |
| deGerlache–Kocher Massif | 0 | 6,966 | 0.4954 | −0.0890 |
| Haworth | 0 | 15,480 | 0.3869 | −0.0018 |
| Faustini Rim A | 0 | 6,964 | 0.4449 | 0.2908 |
| deGerlache Rim 2 | 1,455 | 6,753 | 0.4499 | −0.0898 |
| Connecting Ridge Extension | 0 | 4,069 | 0.4040 | 0.1020 |

Counts refer to the existing comparison-centre population, not independent trials, full-region coverage or physically validated footprints. Empty image groups keep NaN summaries. Radiance is lighting-dependent, not temperature, albedo, ice or a hazard label. Its five supported within-region correlations apply only to deGerlache Rim 2; the other 30 comparisons remain insufficient.

### CPR supplies additional context, not an ice or slope rule

Mini-RF has **52,282 ordinary paired values**. **60 ordinary negatives** are retained as diagnostics but excluded from the explicitly declared nonnegative CPR cohort, leaving **52,222** values across seven regions; **3,098** centres contain ISIS NULLs. Negative CPR screening is not a publisher quality flag.

The 180×360 systematic native lattice (every 128th row/column) has 41,195 ordinary pixels and 23,605 NULLs; 46 ordinary samples are negative. This angular lattice is **not equal-area**. The nominal 236.9 m simple-cylindrical map scale is not an isotropic polar ground footprint.

All 35 within-region CPR/context comparisons have sufficient descriptive support. The slope associations range from **−0.0898 to +0.2908** and change sign. Parent-shadow CPR medians likewise do not change consistently in one direction. These observations do not justify a universal slope substitute, ice indicator, hard limit or preference weight.

### Label, processing and validation boundaries

- Both radar labels declare a missing constant outside the float32 range. Exact observed ISIS NULL/saturation bit patterns are decoded using [USGS definitions](https://isis.astrogeology.usgs.gov/7.2.0/Object/Developer/_special_pixel_8h_source.html), rather than casting that impossible constant or treating every finite value as a measurement. Explicit `isis_null`/saturation category names survive CSV roundtrips.
- The [ShadowCam SIS](https://pds.shadowcam.im-ldi.com/document/archsis.pdf) supplies calibrated-radiance units and geometric-control caveats. The native TIFF is polar stereographic variant B: the XML's reported origin-latitude value corresponds to its standard parallel, not its pole. The actual TIFF CRS/transform is retained.
- The [Mini-RF user guide](https://pds-geosciences.wustl.edu/lro/lro-l-mrflro-5-global-mosaic-v1/lromrf_1001/document/userguide.txt) describes uncontrolled/unorthorectified mosaics, mixed acquisition/viewing geometry and strip gradients. Source values and these holds remain together.
- Existing context is static/cumulative; neither centre lookups nor geographic overlap prove physical co-registration or simultaneous environmental conditions.

[Independent verification](../data/verification/manual_raster_final/verification.json) checks input/output hashes, executed notebook validity, raw pixel bytes/coordinates, special-pixel/status partitions, independent rank-correlation arithmetic and empty groups. **106 targeted EDA tests pass**, including 12 new reader, geometry, masking, schema and roundtrip cases; existing tests were unchanged. Sample-first execution covered an empty image-context case and supported CPR data before the seven-region runs.

The fresh kernels ran sequentially and were shut down; the largest sampled own-kernel RSS was **240.2 MiB**, not a total-system/absolute-peak measurement. Exports are approximately **11.23 MiB**. No new large downloads, full-scene uncompressed arrays, source-data copies, CNN changes or mission scores were produced in that study. Current incorporation is documented in [the proposal](../purposal.md#3-what-to-recommend).

<a id="14-golden-stage-3-revamp"></a>

## 14. Required Stage 3 assessment

**Executed 8 November 2026. Main target:** the five inputs, seven process steps and adequacy/margin/uncertainty output in [outline Stage 3](../../outline.md#stage-3--environmental-and-equipment-suitability-engine). Required Stage 3 work precedes research P1/P2/P3; original tags are unchanged. [Selection/rejection and incorporation table](../purposal.md#3-what-to-recommend).

### Accepted new runs

| Notebook | Stage under `data/processed/analysis/` | Accepted run |
| --- | --- | --- |
| [Dar_029 — data/input audit](Moon/Stage3_Requirements/Dar_029_stage3_golden_dataset_audit.ipynb) | `golden_stage3_audit` | `20261107T231030266513Z_7340dd` |
| [Dar_030 — time, season and terrain](Moon/Stage3_Requirements/Dar_030_stage3_time_season_terrain.ipynb) | `golden_stage3_time_terrain` | `20261107T231040505351Z_6e96d0` |
| [Dar_031 — crew/equipment/margin references](Moon/Stage3_Requirements/Dar_031_stage3_crew_equipment_margins.ipynb) | `golden_stage3_references` | `20261107T231043552019Z_584162` |

### Consolidated findings and disposition

| Required Stage 3 / research category | Executed EDA result | Chosen / rejected role and reason |
| --- | --- | --- |
| **Required Stage 3 dataset readiness** | All 53 research entries audited, plus completed core selections and latest Moon support. **426 unique selected files**, all present at expected size and with receipts. | Accept recorded selection readiness, **not complete archives or fresh all-file checksum verification**. Receipt existence does not revalidate file contents. |
| **All original P1** | 34 rows: 22 external D-sources, 11 project M-inputs and C01. Twenty public P1 source selections are present; D21/D23 require login. Existing Dar_001–027 and new reference/readiness work cover these roles. | Retain original P tags. Missing M-records receive schema/readiness analysis only; no nonexistent measurements are claimed analyzed. |
| **Supporting Earth / analog evidence** | Dar_003 and legacy ports retain five-site, five-variable 2015–2024 Earth climate comparisons. Their original processing/coverage findings remain separate from lunar measurements. | Keep for Earth analog/training comparisons; reject Earth climate as a substitute for lunar conditions or local equipment response. |
| **Joint support, cohorts and redundancy** | Dar_012/013/017/018 compare matched phase/cohort context, quality, regional/spatial grain and co-located rather than unrelated marginal advantages. | Accept support/relationship diagnostics; do not mix unmatched pools or double-reward correlated terrain/environment fields. |
| **Connectivity and preference design** | Dar_019 covers 1,512 diagnostic grid/cut/connectivity cases; Dar_020 retains 21 purposive examples. Dar_021 tests a 15-point weight simplex and normalization; Dar_022 tests gate order and unresolved readiness. | Accept gate-first/redundancy/sensitivity guardrails. Reject nominal component area as a guaranteed base footprint, or weight/threshold sensitivity as an adopted mission policy. |
| **Remaining research data** | 32 public D-source selections present; D21–D24 gated; D17/D25 are unselected P2; 14 M-inputs lack configured project records; C01 is a baseline. | D17/D25 are not silently promoted above required Stage 3 gaps. Gated sources remain KIV. |
| **Crew/requirements reference acquisition** | S01 BVAD Rev2 has seven manually curated official-source rows and provenance; full local PDF transport returned 403. S02 NASA-STD-3001 V2 F and S03 V1 C PDFs are acquired with receipts. | Use reference coefficients/requirement mapping; **not a chosen mission, approved local safety limit or publisher-provided CSV**. |
| **Thermal local time / seasonal support** | **1,032/3,024** region×cohort×Ls×local-hour bins have data. **191** matched-hour summaries have at least two Ls groups. Earlier Dar_001 used 144 phase products / 4,825,369 usable centre-product observations. | Accept phase/local-time context; reject phase bins as calendar dates or measured mission extrema. Matched hour does not ensure the same physical centres across Ls. |
| **Cyclic thermal diagnostic** | Of 108 supported whole-Ls holdouts, the fixed cyclic basis has lower aggregate-bin MAE than its training-mean baseline in **83**. Median fold MAE: available **23.27 K vs 35.42 K** baseline; common-available **31.52 vs 41.50 K**; complete-common **24.05 vs 31.79 K**. | Accept domain/coverage diagnostic; **do not deploy as a mission temperature predictor**. Cohorts overlap and aggregate bins are not independent site observations; 25 supported folds did not beat the baseline. |
| **Terrain-conditioned thermal evidence** | Dar_025/030 retain **2,142** source/cohort/control comparisons: **1,686** descriptive and **456** insufficient; phase sign/support summaries are exported. Earlier terrain-source study found 197/1,187 comparison centres without SDEM slope. | Preserve source/cohort/phase/control identity and missingness; reject a universal slope/roughness correction or correlation-derived score weight. |
| **Rotation / year / month geometry** | **4,704** dated Sun/Earth reference samples: seven observers, first seven days of each 2020 month, six-hour cadence. Local solar hour is calculated in the documented Moon-fixed reference frame. | Accept bounded reference geometry; reject annual duty-cycle, physical terrain illumination or contact guarantees. No Moon seasonal-bin to Earth-month conversion. |
| **Exposure/contact interval support** | Existing November hourly geometry yields **25 below-reference-horizon sample spans**, retaining censoring. | These are first-to-last sample spans, **not measured continuous darkness/outage durations**. Terrain, solar disc, relays and link budgets are not supplied by this benchmark. |
| **Crew/duration / life-support demand** | Seven published nominal interface rates; **63** declared sensitivity records (1/2/4 crew × 1/7/30 days × seven quantities). Nominal metabolic heat converts to **143.82 W/reference crew**. | Use reference sensitivity and unit/quantity review. No crew/mission or stocks/recovery/reserves are selected; metabolic heat is not total habitat heat rejection. Consumed food solids are not total logistics mass. |
| **Power / laboratory equipment** | Dar_015: **34 cell histories / 2,794 discharges**. Dar_031 keeps **40 cell/condition groups** separated by protocol, ambient and stop voltage. | Reference-only. No inferred mission battery, lunar qualification, randomized ambient effect or conversion of mean sunlight into reserve. |
| **Radiation / protection** | Dar_005: 48 published profiles / 14,448 depth rows; strict GOES pilot has zero accepted rows. Dar_031 exports scenario/depth envelopes from **2,408 qualified shielding-sensitivity rows**. | Retain quantity/scenario/material/depth context. Reject zero accepted rows as zero exposure, orbital counters as local dose and automatic cross-unit/biological conversions. |
| **Soil / subsurface / foundation** | Dar_016: **94 records / six tests**, geometry-dependent stresses. Dar_004: **176,233** simultaneous historical gradient pairs. Dar_031 retains six geometry-qualified soil reference cases. | Reference-only; reject peak observed stress as allowable polar bearing pressure and Apollo profiles as polar/component temperatures. |
| **Seismic / imagery / physical hazards** | Dar_007: catalogs of 58/59 entries, 72,084 encoded missing waveform samples. Dar_008: 222 crater detections with effort/time gaps; Kaguya pilots do not overlap selected polar sites. | Retain availability/quality findings; reject duplicate event populations, local recurrence/impact probabilities and unsupported spatial transfer. |
| **P1 LCROSS / sample handling** | Dar_009: two 100-pixel PREIMPACT spectra; no post-impact or containment/release observations. | Reference-only; not volatile abundance, extractable water, sample exposure or containment adequacy. |
| **ShadowCam / Mini-RF additions** | Dar_026: 1,455 ordinary regional comparison values; three candidate examples supported. Dar_027: 52,222 nonnegative values across seven regions; 19 candidate examples supported, mixed slope associations. | Context only; no brightness/CPR-based ice, strength or hazard score. These additions do not replace required Stage 3 inputs. |
| **Mission/equipment/safety gaps** | Dar_029 exports eleven P1 M-input contracts; Dar_031 reports six numerical-margin input gaps and three source-qualified human-system reference mappings. | Required required Stage 3 backlog. These are project/design/test/model inputs, not universally downloadable lunar datasets. |

### Pipeline update and interpretation

[Pipeline_Proto](../Pipeline_Proto/README.md) now **loads and pins the new required Stage 3 exports** under `stage3_evidence/`, alongside existing candidate evidence. Its conditional Stage 3 checks compute adopted-rate stock margins, chronological finite-capacity storage reserve/shortfall, component thermal envelopes, configured outage and exact-quantity/unit capability–demand margins when applicable inputs exist.

The blank [profile contract](../Pipeline_Proto/mission_profile_template.json) does not invent dates, crew, equipment, limits or supply. Current operational candidates remain **Unknown**, with no operational top-k. Diagnostic proxy rankings stay separate. Numerical pass/fail tests use explicitly synthetic fixtures only; no real mission margin, improved final base ranking or trained environmental CNN is claimed.

A full declared mandatory requirement inventory must pass before operational preferences can be ranked. Body, candidate support, period, source/model role, units, interval completeness and thermal/power/contact applicability are checked; supplied applicability declarations still need independent physical validation.

**Remaining work, in priority order:** actual required Stage 3 mission/equipment/requirements; applicable terrain-aware temporal/response/local evidence; quality-qualified dated polar D20 selection and gated sources; remaining original research P1; optional P2/P3. [Exact decisions and reasons](../purposal.md#3-what-to-recommend).

### Verification and reproducibility

[Current verification](../data/verification/golden_stage3_final/verification.json) confirms consumed Required Stage 3/pipeline input/output hashes, four executed notebooks, **392** new/old November geometry matches (maximum difference **1.78×10⁻¹⁵ degrees**), independent recomputation of **108** cyclic folds and **63** reference crew-load sensitivity rows. Beyond the 426 research-selected files, **25** selected R01/R02/S02/S03 raw-reference files are present by size/receipt; S01 full PDF remains a recorded acquisition failure with the curated extract separately available.

**222 relevant tests passed:** 113 EDA/maintenance, 81 downloader and 28 pipeline. Existing tests were not modified. Current blank-profile pipeline runs retain **21 Unknown candidates / 210 Unknown readiness records** and empty operational top-k in both evidence-only and diagnostic modes; proxy scores do not leak into operational eligibility. Kernels were sequential and shut down, owned runtime folders cleaned, and root `data/` remains absent.

## 15. Original notebook reuse — executed 8 November 2026

[Source/dataset inventory](../data/verification/source_port_review/original_notebook_dataset_inventory.csv): **36 original notebooks** reviewed, plus shared helpers and downloaders. [Reuse/dependency table](EDA_Notes.md#original-notebook-reuse-and-datasets--re-check-8-november-2026). No dated terrain-aware mission history generator was identified; the useful existing work is static spatial processing, support checks and terrain views.

| Executed reuse | Measured result | Interpretation / Stage 3 boundary |
| --- | --- | --- |
| [Dar_032](Moon/Stage3_Requirements/Dar_032_native_terrain_illumination_support.ipynb), methods from original 11/12/25 | Seven regions; **28 native source/crop comparisons**, **1,792 finite paired sample positions**. Maximum absolute difference **4.63×10⁻⁷** in decoded source units (maximum in sky-view sr); all within 10⁻⁶ tolerance. **Zero** elevation-policy or derivative-neighborhood mismatches. | Scaling, coordinates and support agree within the checked sample/tolerance. Not exhaustive equality or instrument validation. |
| Static PSR versus image-supported terrain cohorts | On the 30 m analysis grid, **85,871 of 89,505 PSR-labelled cells (95.9%)** lie in the excluded-elevation cohort; **3,634** in retained elevation. | Image-support exclusions overlap strongly with PSR, but are **not equivalent**. Retained terrain alone underrepresents mapped shadow. Counts are resampled analysis cells, not independent native measurements or an area/probability estimate. |
| [Existing local notebook 13](Moon/Terrain_And_Soil/13_build_lunar_terrain_views.ipynb), reusing original 13 | Seven regions, **129 recorded outputs**. Full-source context restores **298,239 elevation cells**. Complete-feature cells: **2,300,477 strict** versus **3,436,572 context**, from **3,537,694 ROI cells**. **101,122** context cells remain excluded by source-edge roughness support. | Strict six-layer views stay byte-identical to accepted inputs. Context uses published elevation and real-source halo, not invented filling. Feature gain includes neighborhood support; it is not 1,136,095 new elevation observations or proof of traversability. |
| Pipeline evidence handoff | Native-support tables and terrain-view summary explicitly pinned in `environment_experiment.json`, hash-checked and copied under `stage3_evidence/`. | Quality/support context only. No automatic thresholds, new physical scores, mandatory passes or replacement of existing candidate measurements. Missing mission/equipment/history evidence remains Unknown. |

Accepted runs: `analysis/stage3_native_support/20261108T085949685187Z_d0bda9` and `lunar_terrain_views/20261108T090010390213Z_9fb81e` under local `data/processed/`. [Execution record](../data/verification/source_ports_execution_20261108T085945333243Z/verification.json); [final checks](../data/verification/source_port_review/final_verification.json). Launcher-RSS sampling in the execution record is not a verified peak-memory measurement and is not used as a resource claim.

**Missing for full original replay:** FABDEM/WorldCover/OSM Earth inputs, independently selected NAIP/3DEP/Landsat data for original 24, and rebuilt patch/scaler/model artifacts for original 28–36. These are supporting paths, not all mandatory environmental downloads. Required Stage 3 mission/equipment configuration and applicable temporal/response evidence retain priority.

Active notebooks use `Moon/Stage3_Requirements/`; future required-work outputs use `analysis/stage3_required_*` and `stage3_evidence/`. Historical data/verification paths remain unchanged. Original code outside Darrel remains read-only.

**Current validation: 225 tests passed** (116 EDA/maintenance, 81 downloader, 28 pipeline), with existing tests unchanged. Dar_028 re-executed in both modes with the new pinned context tables: **21 operational Unknown candidates / 210 Unknown readiness records**, zero operational top-k, and separate unchanged proxy diagnostics. The external `prototype2/run_main.ipynb` was also checked: it launches a generic eligibility/scoring pipeline, not lunar data processing or a terrain-aware time-history generator; its unrelated input data are not transferred.


## 16. Step 3 available-data EDA milestone - 9 November 2026

[Full existing-notebook review, findings, hazard matrix and scope](../research/STEP_3_EDA_REVIEW.md). Moon only; no CNN, adopted rules, ranking or engine changes. **39 existing notebooks reviewed**, with one pre-existing blocked legacy Moon 25 port (absent original unit policy); no saved errors in Dar_001-032. Historical notebooks were not blanket rerun or modified.

| Executed analysis | Measured result | Operational boundary |
| --- | --- | --- |
| [Dar_033](Moon/Stage3_Requirements/Dar_033_mission_resource_and_risk_eda.ipynb) | 16/18 primary Apollo 17 resource records consumed more than predicted; smallest remaining-minus-historical-redline differences: oxygen 0.00 lb, feedwater 0.05 lb, battery charge 0.82 Ah. 65/66 reconstruction rows have paired predictions. | Source-specific rounded historical quantities, not modern equipment limits or site feasibility. Ah is not Wh. |
| [Dar_034](Moon/Stage3_Requirements/Dar_034_radiation_and_hazard_evidence_eda.ipynb) | Three dates: 259,200 selected-state CRaTER seconds; 369/22,464 strict GOES channel/time rows; no full qualified sensor/channel day; 96 modeled reference dose-duration sensitivities. | Counters/flux are not lunar crew dose. Missing supported exposure remains blank; steady-rate scaling does not bound solar events. Related catalogs and 222 crater detections do not establish local disaster probabilities. |
| [Dar_035](Moon/Stage3_Requirements/Dar_035_dated_polar_thermal_support_eda.ipynb) | Six products, one region, channels 3/4: 95,695 observations, 59,871 inside the exact rectangle; zero strict-quality observations; 36,101 positive in-region flagged diagnostics. | All qge=12; no silent relaxation. Sparse local-hour/channel brightness is not bolometric/equipment temperature or a mission envelope. |

Radiation, thermal/power loss, seismic/impact/ejecta, dust, life support, ground/mobility, communications, charging, resources and contingency risks are explicitly recorded. No numeric cutoff was invented; missing applicability/capability remains Unknown and cannot be converted into a preference pass.

Accepted runs: `analysis/stage3_resources_eda/20261108T211453295966Z_b828df`, `analysis/stage3_radiation_eda/20261108T211459851919Z_a935df`, `analysis/stage3_thermal_eda/20261108T211520197662Z_f64ea4`. [Verification](../data/verification/stage3_eda_review/verification.json): **11 targeted tests passed**, three notebooks fully executed with no saved errors, 28 retained-output and 65 non-notebook consumed-input hashes verified. These are targeted software/data checks, not physical qualification or a fresh full-suite count. Frozen selections remain valid while other downloads continue. Steps 4-6 remain deferred.


## 17. Expanded Step 3 - outline crosswalk, terrain geometry and annual radiation

[Expanded findings, source review and final acquisition cutoff](../research/STEP_3_EXPANDED_EDA.md), [27-factor outline crosswalk](../research/outline_environment_crosswalk.csv). Moon only; no CNN or engine/rule changes.

| Executed notebook | Findings / contribution | Boundary |
| --- | --- | --- |
| Dar_036 | Seven ROI-center points, 5,040 sampled horizon bearings, 80,752 Sun/Earth-center samples. Increasing range 10 to 20 km raises skyline at 348 matched bearings, up to 4.418 degrees. Joint refinement changes Leibnitz solar blocking by up to 2.36 percentage points. | Finite terrain/target-center sampling, not clear-horizon proof, solar-disk power, continuous darkness or a working communication link. Zero sampled blocking is not continuous illumination. |
| Dar_037 | 394 consecutive GOES-16 completed days; 266,507/2,950,272 strict bins (9.03%). | Source-file coverage is not qualified exposure coverage; observed maxima are not certified events or dose. |
| Dar_038 | 456 completed CRaTER dates: 39,356,608 records; two missing dates and four partial-record days. Extend GOES to 457 dates with explicit gaps. | Year-plus context, not a dense two-year survey; counters and flux remain separate physical quantities. |
| Dar_039 | Late revisit adds 38 dates per instrument. Final **494 CRaTER dates / 42,639,808 records**, and **495 GOES-16 dates / 3,706,560 bins**, of which **385,750 (10.41%)** qualify. | About 16 months dense coverage meets minimum one year, not two dense years. CRaTER lacks 19-20 June 2024; GOES retains 29 missing dates before the isolated April file. |

Final external cutoff: **9 November 2026, 05:55:42 Singapore time**. No new successful D20 job; polar thermal-quality limitations remain. New dates arriving after this cutoff are not silently credited. Earlier rows and 42 prior notebooks are preserved. [Targeted verification](../data/verification/stage3_expansion/verification.json) checks four new notebook executions, hashes, 25 tests, annual support/missingness and geometry/incremental-preservation contracts; not physical qualification. Full details, run IDs and primary documentation are in the expanded report. Steps 4-6 remain deferred.
