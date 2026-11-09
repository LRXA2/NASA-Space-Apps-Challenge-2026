# Step 3 - Moon mission/environment EDA review

**Completed: 9 November 2026 (Singapore), for the bounded available-data proof of concept.**

**Objective:** establish what available lunar conditions and historical equipment evidence can tell us about whether an intended mission could operate at a selected site. This is EDA completion, **not a declaration that any site or mission is safe**. No CNN, new engine rules, ranking, downloads or mission defaults were implemented.

**Later expansion:** [outline-factor crosswalk, terrain horizons, year-plus radiation coverage and late-download refresh](STEP_3_EXPANDED_EDA.md). The three-day radiation results below remain the historical pilot, not the current temporal extent.

## Start here

| Executed notebook | New contribution |
| --- | --- |
| [Dar_033: mission resources and risk](../EDA/Moon/Stage3_Requirements/Dar_033_mission_resource_and_risk_eda.ipynb) | Actual versus predicted Apollo consumables, source-specific remaining reserves, duration differences, related-source consistency and hazard evidence boundaries. |
| [Dar_034: radiation and hazards](../EDA/Moon/Stage3_Requirements/Dar_034_radiation_and_hazard_evidence_eda.ipynb) | Recent CRaTER/GOES samples, strict quality/temporal coverage, published dose-duration/shielding sensitivity, and limits of seismic/impact evidence. |
| [Dar_035: dated polar thermal support](../EDA/Moon/Stage3_Requirements/Dar_035_dated_polar_thermal_support_eda.ipynb) | Six new dated polar products: native identity, exact regional clipping, quality/missingness and channel/local-hour support. |

Code: [`stage3_mission_eda.py`](../EDA/stage3_mission_eda.py). Frozen source selection: [`stage3_eda_config.json`](../EDA/stage3_eda_config.json). Inputs remain in their two existing data roots; no ongoing inventory tracker was created.

## 1. Existing EDA: reuse, enhance or rework?

Reviewed **39 existing local notebooks**: Dar_001-032, including the separate Dar_028 prototype, plus seven legacy ports. Review used code, saved outputs and accepted-run findings, not a blanket rerun. Their review-time hashes and decisions are retained in the [review snapshot](../data/verification/stage3_eda_review/existing_notebook_review.json).

**Decision:** preserve the useful thermal, terrain, matched-support and uncertainty work. Extend operational evidence, dated observations and hazard applicability through new notebooks rather than rewriting established calculations. Preference/hard-soft sensitivity notebooks remain **illustrative diagnostics**, not an approved requirement set.

**One pre-existing blocked port:** legacy `25_environment_native_support_eda.ipynb` contains a saved `FileNotFoundError` because `data/reference/environment-readiness-20261028/native_layer_units.json` is absent. It is **not** credited as an executed result. Replaying it requires restoring a verified original unit policy, not inventing units or silently substituting a file. Numbered Dar notebooks have no saved error outputs; executed Dar_001/002/025/032 already cover related thermal/native-support questions. The legacy port was left unchanged and is not a dependency of the three new analyses.

| Notebook | Decision | Reason / retained limitation |
| --- | --- | --- |
| [03_earth_climate](../EDA/Earth/Climate/03_earth_climate.ipynb) | Defer | Earth climate is outside current Moon-only scope. |
| [26_earth_environment_expansion](../EDA/Earth/Climate/26_earth_environment_expansion.ipynb) | Defer | Earth climate is outside current Moon-only scope. |
| [27_five_site_environment_eda](../EDA/Earth/Climate/27_five_site_environment_eda.ipynb) | Defer | Climate-only Earth port, not full original OSM analysis; outside current Moon scope. |
| [Dar_003](../EDA/Earth/Climate/Dar_003_earth_climate.ipynb) | Defer | Earth climate is outside this Moon-only task. |
| [Dar_015](../EDA/Earth/Dar_015_battery_reference_experiments.ipynb) | Reference only | Battery protocol/ambient groups are not matched causal temperature experiments or lunar qualification. |
| [Dar_005](../EDA/Moon/Dar_005_research_radiation.ipynb) | Enhance: Dar_034 | Recent completed counter days, GOES quality coverage and explicit duration/reference sensitivity. |
| [Dar_007](../EDA/Moon/Dar_007_research_seismic.ipynb) | Qualify: Dar_034 | Related catalogs and count-domain waveforms do not establish independent local recurrence or physical ground loads. |
| [Dar_008](../EDA/Moon/Dar_008_research_imagery_change.ipynb) | Qualify: Dar_034 | Selected detections lack effort-normalized event rates; Dar_026 updates older ShadowCam availability only. |
| [Dar_009](../EDA/Moon/Dar_009_research_lcross_spectra.ipynb) | Context only | Pre-impact LCROSS spectra do not establish resources, containment or toxicology. |
| [Dar_026](../EDA/Moon/Dar_026_shadowcam_manual_environment.ipynb) | Reuse | ShadowCam context at 3/21 components is not ice or temperature measurement. |
| [Dar_027](../EDA/Moon/Dar_027_minirf_cpr_environment.ipynb) | Reuse | Mini-RF context at 19/21 components is not certified ice, soil strength or suitability. |
| [25_environment_native_support_eda](../EDA/Moon/Environmental_Context/25_environment_native_support_eda.ipynb) | Blocked prerequisite; do not credit as executed | Saved FileNotFoundError: original native_layer_units.json is absent. Restore a verified original policy before replay; do not invent units. Dar_001/002/025/032 provide executed related thermal/native-support analyses, not an assertion this port ran. |
| [Dar_010](../EDA/Moon/Environmental_Context/Dar_010_research_spice_geometry.ipynb) | Reuse geometry only | Reference-sphere sampling is not terrain-aware continuity or a working communication link. |
| [Dar_011](../EDA/Moon/Environmental_Context/Dar_011_research_p1_coverage_gaps.ipynb) | Update availability snapshot | Retain historical audit; Step 1 report and new frozen config capture newer external inputs. |
| [Dar_012](../EDA/Moon/Environmental_Context/Dar_012_joint_environmental_context.ipynb) | Reuse | Joint support cohorts remain useful; phase rows are not dated mission conditions. |
| [Dar_013](../EDA/Moon/Environmental_Context/Dar_013_feature_sensitivity_redundancy.ipynb) | Reuse | Sensitivity and redundancy help avoid double counting, not establish thresholds. |
| [Dar_014](../EDA/Moon/Environmental_Context/Dar_014_rule_readiness_geometry_context.ipynb) | Enhance: Dar_033/034 | Historical operational evidence adds context but cannot replace the actual mission/equipment profile. |
| [Dar_017](../EDA/Moon/Site_Assessment/Dar_017_lunar_base_environment_profiles.ipynb) | Reuse | Regional summaries retain units, support, aggregation and missingness boundaries. |
| [Dar_018](../EDA/Moon/Site_Assessment/Dar_018_joint_environment_terrain_tradeoffs.ipynb) | Reuse | Joint support is distinct from marginal support; reference battery/soil/shielding is not site measurement. |
| [Dar_019](../EDA/Moon/Site_Assessment/Dar_019_spatial_environment_connectivity.ipynb) | Reuse | Components depend on grid scale, origin and diagnostic filters; not validated base footprints. |
| [Dar_020](../EDA/Moon/Site_Assessment/Dar_020_candidate_environment_profiles.ipynb) | Diagnostics only | The 21 components are not approved mission sites or feasibility results. |
| [Dar_021](../EDA/Moon/Site_Assessment/Dar_021_environment_preference_sensitivity.ipynb) | Reframe; retain code | Preference sweeps use illustrative weights, never an override of mandatory conditions. |
| [Dar_022](../EDA/Moon/Site_Assessment/Dar_022_environment_hard_soft_rule_influence.ipynb) | Reframe; retain code | Illustrative hard/soft cutoffs are not adopted requirements; rule definition remains Step 4. |
| [Dar_024](../EDA/Moon/Site_Assessment/Dar_024_nominal_thermal_bin_support.ipynb) | Reuse | Associated thermal centers do not guarantee whole-component containment or thermal coverage. |
| [Dar_029](../EDA/Moon/Stage3_Requirements/Dar_029_stage3_golden_dataset_audit.ipynb) | Update availability snapshot | The 53-entry audit is dated readiness, not full archive verification; new subset is pinned separately. |
| [Dar_030](../EDA/Moon/Stage3_Requirements/Dar_030_stage3_time_season_terrain.ipynb) | Reuse | Retain phase gaps and held-out diagnostics; sampled monthly sphere geometry is not mission darkness endurance. |
| [Dar_031](../EDA/Moon/Stage3_Requirements/Dar_031_stage3_crew_equipment_margins.ipynb) | Enhance: Dar_033 | Observed/predicted historical resource use supplements references without creating mission defaults. |
| [Dar_032](../EDA/Moon/Stage3_Requirements/Dar_032_native_terrain_illumination_support.ipynb) | Reuse | Seven-region native units/crop/neighborhood checks already cover this question; no broad raster rerun. |
| [05_lunar_terrain_environment](../EDA/Moon/Terrain_And_Soil/05_lunar_terrain_environment.ipynb) | Reuse | Local lunar preprocessing/support; Dar_032 extends checks. |
| [13_build_lunar_terrain_views](../EDA/Moon/Terrain_And_Soil/13_build_lunar_terrain_views.ipynb) | Reuse | Keep strict layers and real-source context/halo separate; neither is tested soil strength. |
| [Dar_006](../EDA/Moon/Terrain_And_Soil/Dar_006_research_terrain_support.ipynb) | Reuse | Keep terrain masks and original regional limits; Dar_032 extends native support checks. |
| [Dar_016](../EDA/Moon/Terrain_And_Soil/Dar_016_apollo15_soil_reference.ipynb) | Reference only | Six historical soil tests do not provide site-specific bearing capacity or traction. |
| [Dar_023](../EDA/Moon/Terrain_And_Soil/Dar_023_terrain_environment_source_sensitivity.ipynb) | Reuse | Source/crop and cohort differences remain; context is not independent validation. |
| [06_diviner_temperature](../EDA/Moon/Thermal/06_diviner_temperature.ipynb) | Reuse | Thermal preparation and phase bins; no dated history claim. |
| [Dar_001](../EDA/Moon/Thermal/Dar_001_temperature_local_time.ipynb) | Reuse | Local-hour thermal baseline; preserve native support and phase-versus-date distinction. |
| [Dar_002](../EDA/Moon/Thermal/Dar_002_temperature_environment_relationships.ipynb) | Reuse | Matched-support thermal/environment associations are not causal equipment response. |
| [Dar_004](../EDA/Moon/Thermal/Dar_004_research_thermal.ipynb) | Enhance: Dar_035 | Old 2013 RDR pilot lacks polar support; new polar observations extend availability, not qualified thermal history. |
| [Dar_025](../EDA/Moon/Thermal/Dar_025_conditional_terrain_temperature.ipynb) | Reuse | Conditional phase/support relationships are not universal corrections or causal effects. |
| [Dar_028](../Pipeline_Proto/Dar_028_environment_pipeline.ipynb) | Freeze; untouched | Operational Unknown must stay separate from proxy preferences; no engine integration in this task. |

## 2. New findings and their operational meaning

### Historical deployment and resource use - Dar_033

The [checked Step 2 extraction](STEP_1_2_EVIDENCE.md) supplies 18 primary Apollo 17 EMU resource records, 66 later EVA percentage reconstructions across Apollo 14-17, eight LM totals and 26 contextual records. Row counts are **not independent missions or safety trials**.

- Actual consumption exceeded prediction in **16/18** primary records. All six oxygen and all six feedwater records exceeded prediction; battery charge did so in four of six. This supports examining workload/duration, uncertainty and reserve depletion; not using a nominal prediction as guaranteed adequacy.
- Smallest remaining-minus-source-redline differences were **0.00 lb oxygen**, **0.05 lb feedwater** and **0.82 Ah battery charge**. The oxygen value is equality at the published rounding, **not evidence of a robust positive margin**. Ah is charge, not Wh or usable energy.
- Recorded EVA durations exceeded the 420-minute plan by **12, 37 and 15 minutes**. Planned duration alone is not an unconditional actual operational cutoff; do not label these missions retrospectively failed from that comparison.
- Across the later reconstructions, actual-minus-predicted remaining medians were **-4.15 percentage points feedwater**, **-1.10 oxygen**, **-1.80 power**. There are **65 paired comparisons**, not 66: the missing predicted power value remains missing.
- Primary and reconstructed Apollo 17 remaining percentages agree within **0.050 percentage points**, consistent with rounding. This is a consistency check between related sources, not independent validation.
- LM total consumption was **46.46 versus 43.90 lb oxygen**, **390.40 versus 373.00 lb water**. Do not combine phase-specific remaining stocks or LM quantities with suit supplies. The source's printed predicted descent-water total is retained with its previously documented tank-sum discrepancy.

**Evidence-backed strategy inference, not adopted rules:** NASA used budgets plus operational monitoring/adjustment, contingency return capability, conditional communications provisions, and dust/thermal maintenance. The checked records describe brushed/dusted cooling surfaces, parking choices, rover fender repair and thermal anomalies. Temperature indications also needed equipment/measurement context: the historical LRV rule did not order abandonment from temperature alone. These support a future capacity-demand-reserve assessment with explicit equipment states; they do not transfer Apollo thresholds to a modern mission.

### Radiation, duration and event evidence - Dar_034

Frozen common completed dates are **2023-11-01, 2024-02-12 and 2024-05-25**, chosen by acquisition coverage before reading science values. These are sparse samples, **not selected solar events or a worst-case survey**.

- CRaTER: **259,200 one-second records**, all satisfying the selected bias/calibration/processing-state checks, with no sampled cadence gaps. Their counters are **not lunar surface or shielded crew dose**. The [PDS processed-product description](https://pds.nasa.gov/ds-view/pds/viewProfile.jsp?dsid=LRO-L-CRAT-3/4-DDR-PROCESSED-V1.0) identifies the instrument products; passing these selected checks is not full physical validation.
- GOES: **369/22,464 channel/time rows (1.64%)** meet the strict finite/nonnegative flux, sample-count, DQF and LUT-match policy. Qualified counts by date are **0, 11 and 358**. **No sensor/channel has all 288 daily bins qualified.** Only supported 300-second-bin contributions are calculated; absent support remains blank, not zero exposure or a complete-day fluence.
- File metadata explicitly defines `ExpectedLUTNotFound=1` as matching lookup tables despite the confusing variable name. Do not reverse the meaning to obtain more usable values.
- **96 published-scenario duration sensitivities** retain solar scenario, Al areal density and modeled depth. Conversion is `cSv/year * 10 * days / 365.25 -> mSv`, assuming a steady annual rate. For example, the selected depth-zero references span **15.43-33.78 mSv at 30 days**. These are study sensitivities, **not selected-crew dose, an exposure-limit test, or an SPE worst-case bound**.
- Greater shielding cannot be assumed to improve every reported component at every depth: **3,627 model rows** exceed their same-scenario/component/depth minimum-Al reference, including **24 total-particle rows**. Do not fit a universal "more shielding = safe" rule from this table.
- Seismic context contains **58 and 59 entries in related catalogs**, not 117 independent events; their overlapping class counts are retained separately. The **222 selected new-crater detections** lack event timing/observation-effort support for a local mission-window probability. Neither catalog certifies absence of dangerous moonquakes or impacts.

### Dated polar thermal support - Dar_035

The fixed selection contains **six completed products**, channels **3/4**, months **2023-06, 2025-03 and 2026-06**, for **one Leibnitz Beta Plateau regional rectangle**. June 2023 is a partial query month. It is not full seven-region coverage, a validated base footprint or the intended mission period.

- **95,695 native channel observations**; **59,871** fall in the exact projected rectangle. Product query bounding boxes are not identical to that rectangle.
- **39,072** observations have nonpositive/missing brightness temperature across the full query products and cannot be used as physical temperatures. This count and the regional count have different denominators; do not subtract them to infer accepted support.
- All records carry **qca=0, qge=12, qmi=0**. Therefore **zero** satisfy the conservative all-zero quality cohort. Nonzero geometry-flag semantics were not established from the applicable SIS in this work and are not silently approved.
- **36,101** positive in-region observations remain in the separately labelled download-policy diagnostic cohort. Local-hour medians cover only **2-8 hour bins per channel/month**. Plotted points do not interpolate missing hours or establish continuous conditions.
- ODE labels contain the opening-token typo `COLUM` at column 17. The reader records it and requires all 33 uniquely named, consecutively numbered columns plus exact file/record sizes; no source file was edited.

**Consequence:** dated polar observations are now demonstrably available, but this sample **does not resolve the qualified mission thermal-history gap**. Channel brightness temperatures are not bolometric surface or equipment temperatures; observed extrema are not mission extrema. [NASA PDS Diviner archive](https://pds-geosciences.wustl.edu/missions/lro/diviner.htm), [instrument data guide](https://www.diviner.ucla.edu/data).

## 3. Common-sense hazards: what must not disappear into a score

Both Dar_033/034 export a **12-category hazard/evidence-boundary table**. These are risk principles and missing-input findings, **not implemented gates or adopted numerical limits**.

| Hazard family | Required distinction / outstanding evidence |
| --- | --- |
| Radiation and solar-particle events | Exposure exceeding an applicable crew/equipment limit, or inadequate essential protection, cannot be offset by good terrain. Need field/scenario, duration, shielding/transport and applicable requirement. Raw high counters/flux alone do not define a crew dose cutoff. |
| Thermal extremes and prolonged darkness | Need dated environment, thermal response, power generation/load/storage, efficiencies and reserves. A pleasant mean or high average illumination cannot hide a lethal excursion or life-critical outage. |
| Moonquakes, impacts and ejecta/plumes | Separate event evidence from local recurrence probability and structural/penetration response. Sparse catalogs and no detections do not establish negligible risk. Landing/plume scenarios also require geometry and equipment response. |
| Dust, vacuum, life support | Need equipment-specific cooling, sealing, visibility, wear and protected-system performance; orbital dust and exterior maps do not establish cabin safety or life-support adequacy. |
| Terrain, foundations, mobility and return | Need local mechanics/loads, hardware capability and contingency return; slope/context and old soil tests alone are insufficient. |
| Communications, charging and contingency workload | Need actual contact/link assumptions, charging/electronics response and workload/reserve requirements. Historical exceptions remain conditional. |
| Resources and chemistry | Do not credit unverified local materials as essential consumables; need extractability, processing, containment and exposure evidence. |

For a later assessment: a demonstrated breach of an applicable essential requirement is **Failed**; missing applicability, measurements or protection evidence is **Unknown**, never automatically Passed. Severe hazards are not preference penalties. Current measurements do **not** justify classifying any selected site as definitively safe or definitively unsafe overall.

Current human-system requirements must be selected by scope/revision, not reverse-engineered from observations: [NASA-STD-3001 Volume 1](https://standards.nasa.gov/node/238), [Volume 2](https://standards.nasa.gov/node/237). No numerical requirement was adopted from them in this step.

## 4. Completion, validation and remaining boundaries

**Step 3 is complete for this bounded proof-of-concept analysis:** per-notebook decisions, three executed new notebooks, retained plots/tables, source/receipt hashes, explicit hazard coverage and targeted checks. Step 2's checked extraction is sufficient for these historical comparisons, **not exhaustive PDF curation**. New downloads can support later extensions without invalidating this frozen analysis.

[Verification](../data/verification/stage3_eda_review/verification.json): **11 targeted tests passed**, all code cells in the three new notebooks executed with zero saved errors, **28 retained-output hashes** and **65 non-notebook consumed-input hashes** verified. All **39 reviewed historical notebooks** were unchanged. Tests cover source balance/identity, missing predictions, unit conversion, quality rejection, label parsing, and absence of inferred eligibility. This establishes software/data-handling checks, not engineering qualification.

Accepted runs under `data/processed/analysis/`:

- `stage3_resources_eda/20261108T211453295966Z_b828df`
- `stage3_radiation_eda/20261108T211459851919Z_a935df`
- `stage3_thermal_eda/20261108T211520197662Z_f64ea4`

[Execution record](../data/verification/stage3_eda_execution_20261108T211448258607Z/verification.json). Local generated artifacts are in the existing ignored data tree; retain it to open linked evidence. Run manifests capture pre-execution notebook hashes; the verification separately records saved executed-notebook hashes.

**Not completed or claimed:** full acquisition/full PDF manual review, repair of the legacy port's absent original policy, an event-extreme census, full dated terrain-aware illumination/contact histories, local quake/impact probabilities, qualified thermal/charging/dust/structural response, a selected mission/equipment profile, adopted requirements or actual operational margins. Additional downloaded ARTEMIS/Kaguya/ShadowCam records are not processed indiscriminately: a defined applicable question, support and response model are needed before they could change adequacy. Existing terrain/image support EDA is retained rather than duplicated.

**Stop here:** workflow Steps 4-6 (define rules, build/integrate, validate the recommendation engine) remain deferred. No site eligibility or preference result was produced by this work.
