# Moon Environmental EDA

**Purpose:** understand lunar conditions and compare candidate sites using observations, modelled indicators and reference studies. This is environmental evidence, not proof that a mission can operate safely.

**Scope:** findings below describe scientific EDA, not the standalone pipeline's assumed test fixture. Dar_044 screening/subset results are retained as earlier baselines; the Dar_045-055 subject studies and Dar_056 handoff provide the expanded coverage. Exact completed-run sources are listed under Evidence and notebook conventions.

## Scope and coverage

- Moon-focused research EDA across seven study regions and 21 exploratory candidate components. These are not the separate 77-row software fixture or its newly defined 1.2 km patches. Earth experiments are supporting references only.
- Quality flags, missing dates, spatial support and observation cohorts are checked before comparison. Missing evidence stays **Unknown**, not zero risk.
- **Expanded Stage 3-4 complete within declared evidence scopes:** Dar_044 remains the initial screen; Dar_045-055 are the eleven executed subject studies and Dar_056 is the unadopted requirement synthesis. Full/sampled/experimental coverage and unresolved qualification remain explicit. The separate [Stage 5 pipeline](../env_pipeline/README.md) now uses `assumption_NASA_values`, available-data/strict modes and independent toggles; those test choices do not update or validate these EDA findings. [Scope/checklist](../todo_workflow.md#comprehensive-subject-eda-and-stage-4).

## Expanded subject EDA and time windows

The **eleven subject notebooks (Dar_045-055)** and **Stage 4 synthesis Dar_056** define the expanded analysis. Each subject adds analysis beyond Dar_044, cross-checks source evidence and states its conclusion and remaining uncertainty. Their scope does **not establish that a mission/site is operationally qualified**.

| Grouping | Definition |
| --- | --- |
| Month / quarter | UTC calendar month / Jan-Mar, Apr-Jun, Jul-Sep, Oct-Dec. |
| Four-month term | Jan-Apr, May-Aug, Sep-Dec; included alongside quarters to avoid ambiguous "trimester". |
| Half-year / year | Jan-Jun or Jul-Dec / calendar year. |
| Two-year | Nonoverlapping even-year pairs, anchored 2000; distinct from twice-yearly. |
| Calendar season | DJF, MAM, JJA, SON; DJF is named for its January year. **Not lunar climate seasons.** |

**Method:** retain timestamps, complete calendar denominators, valid days/samples, gaps, partial periods and observed maxima. Aggregate from days, not averages of monthly medians; do not pool instruments, energy bands, modes or historical epochs. Fixed-month comparisons retain unequal coverage. Static/cumulative maps have acquisition/model applicability, **not fabricated monthly histories**. Short historical missions are not stretched to a year.

| Subject / notebook | Additional steps and measured findings | Base conclusion |
| --- | --- | --- |
| [UV - Dar_045](Moon/Stage3_Requirements/Dar_045_uv_spectral_spatial_time.ipynb) | All **1,206 SEE spectra**, five bands, wavelength support, uncertainty and model-assisted partitions; all native pixels of **20 LAMP maps**. Supported days: XUV 727, EUV 139, 50-115 nm subband 1,206, FUV 1,206, 180-190 nm 1,206. All seven time groupings, matched June-October years, native-vs-stride map checks. | Band support differs substantially; a supported narrow band does not repair an unsupported wider band. LAMP is historical albedo/brightness, not local incident UV or dose. |
| [Plasma - Dar_046](Moon/Stage3_Requirements/Dar_046_plasma_modes_charging_time.ipynb) | Expanded **82 to all 1,173 ESA files** (2023-06-01 to 2026-10-12), six modes / **53.86 million mode-records**, quality flags, clock/cadence and seven time groupings; reused checked P1/P2 merged context. Reduced-electron quality=0 support is **4.24% of native records before further screening**. All **1,374** previous ESA day/series rows retain their values/support. | Mode and quality selection materially affect comparisons. Full-mode ion/electron daily density association is 0.955 versus 0.222 for reduced mode; this is descriptive, not instantaneous quasi-neutrality, surface voltage or a charging safety model. |
| [Subsurface thermal - Dar_047](Moon/Stage3_Requirements/Dar_047_subsurface_thermal_depth_time.ipynb) | All **30 HFE tables / 520,977 records**, **100 original/derived series**, documented sensor positions, corrected signed differences, bit flags and seven time groupings (1971-1977). Retained **131 undated records** in diagnostics. All **32,545** original thermometer/day rows match Dar_044. | Depth and deployment matter. In 1972, Apollo 15 probe 1's matched-date p95-p05 daily span is **5.67 K at 35 cm vs 0.160 K at 139 cm** (366 common dates). This is not a causal insulation coefficient, polar history or equipment envelope; early deployment transients and archival sampling remain explicit. |
| [Dust - Dar_048](Moon/Stage3_Requirements/Dar_048_dust_threshold_quality_time.ipynb) | All **36 LDEX tables**, **677,271 current records / 441,166 mass-catalog entries**, 166 recorded dates, current/background uncertainty, native quality/saturation classes, mass thresholds and seven time groupings. **9,041 numerically supported entries fall below their reported native mass threshold**; they are identified, not silently reclassified as qualified impacts. All **498** original current/day rows match. | Thresholds, classification and saturation need qualification. Catalog counts are not flux/event rates, current is not surface loading, and the short 2013-2014 history cannot support a repeating annual-season claim. |
| [Radiation - Dar_049](Moon/Stage3_Requirements/Dar_049_radiation_calendar_extremes.ipynb) | Reused all **79 accepted radiation series / 35,281 daily rows**; added seven time groupings, daily-max upper-tail segments and solar association sensitivity to year/common-time trends. All **1,232** prior monthly medians match. CRaTER/FUV pooled level correlation **0.464** becomes **-0.001** for 1,038 consecutive-day differences; within-year associations also vary. | The pooled association is not stable across these comparisons; it is not a causal/dose model. Quantile tags are descriptive, **not safety limits or physical event detection**. GOES remains Earth-orbit space-weather context, not lunar-local exposure. The sparse primary cohort was not expanded. |
| [Polar thermal - Dar_050](Moon/Stage3_Requirements/Dar_050_polar_thermal_model_support.ipynb) | All **2.88 million PRP facets**, native 3-D facet areas, triangle/area-weighted distributions, histogram quantile intervals and regional boundary support. Original eight regional/global count/temperature summaries match. Malapert's mean surface-maximum statistic is **274.04 K by triangle vs 275.15 K by facet area**; **286/3,486** centre-selected triangles cross that box boundary. | Mesh weighting and footprint inclusion matter, but these are not clipped candidate areas or component temperatures. The source explicitly has no applicable start/stop chronology: no monthly histories are fabricated. |
| [Exosphere - Dar_051](Moon/Stage3_Requirements/Dar_051_exosphere_species_geometry_time.ipynb) | Expanded **36 to all 2,715 selected NMS files / 592,721 records**, Ar/He/Ne, uncertainty, altitude/latitude/local-solar-time strata and seven calendar groupings, **2013-11-21 to 2014-04-17**. All **36** original sparse-cohort day/species rows replay exactly. Separate clock-policy and added-orbit comparisons isolate their effects; **33 native `Seconds=60` records** are conservatively held in the new analysis, not silently corrected. | Added orbit/geometry coverage changes matched-date medians (Ar median full-minus-sparse difference **-713.15 particles/cm3** across 12 shared dates under the same clock policy). This shows cohort sensitivity, not a causal altitude/season effect, surface concentration, breathable air or hardware compatibility. |
| [Neutrons/resources - Dar_052](Moon/Stage3_Requirements/Dar_052_neutron_spectra_state_time.ipynb) | Expanded **74 dates/five channels to all 1,110 selected days / 11 channels / 95.62 million frames** (2023-06-01 to 2026-06-14). Added clock/geometry/parameter support, raw collection-register rates, native spectral bins, zero-state runs and seven calendar groupings. The original 740 sparse spectral summaries replay exactly. | Zero channels are common and are not absence of neutrons, safe dose or detected ice. Raw register rates are not calibrated flux or qualified live exposure. All **1,110 SCALT unit holds** remain explicit: the acquired XML says `8`, not verified kilometres. |
| [Seismic - Dar_053](Moon/Stage3_Requirements/Dar_053_seismic_axes_response_time.ipynb) | All **2,193 selected MH1/MH2/MHZ files / 1.246 billion samples**, preserving mode/axis and reusing 730 accepted ATT diagnostics. All 731 previous vertical traces match. Added seven calendar groupings and **300 inverse-response experiments**: two diagnostic filters on first gap-free 8,192-sample windows from 150 preselected file/trace cases. | Metadata-based band-limited displacement is not qualified ground-motion peaks, independent natural events, polar recurrence or structural demand. Filter, nominal-clock, selection and attribution limits remain explicit. |
| [Terrain/illumination - Dar_054](Moon/Stage3_Requirements/Dar_054_terrain_illumination_multiyear.ipynb) | Expanded two short windows to **two complete model years (2020-2021), 982,464 samples / 56 reference-point/scenario/target tracks**, calendar and persistence analysis, 60/30-minute cadence sensitivity and native terrain/image checks. All **80,752** previous timestamps/classifications match. | At 2 m/20 km, Leibnitz and Malapert reference points have similar clear-center fractions (**0.214/0.233**) but different longest observed blocked-sample spans (**2,819/691 h**). These are sampled model spans, not guaranteed continuous darkness, candidate histories, generation or contact service. |
| [Operations/habitat - Dar_055](Moon/Stage3_Requirements/Dar_055_operations_habitat_source_evidence.ipynb) | Audited **95 retained PDFs**, retaining 14 review holds; freshly extracted **23 declared pages / ten documents** support 18 coded cases, not a new full-library manual review. Decomposed 18 visually checked Apollo 17 resource rows into duration and mean-rate effects; old arithmetic matches. **16/18** total consumptions and **15/18** mean rates exceed predictions. | NASA evidence supports calibration, coupled services, contingency return, maintenance and condition-specific decisions. Historical normal/moving-traverse communication provisions differ; no universal outage cutoff, modern reserve factor or flight/trainer capacity substitution is adopted. |

**Polar resource-quality finding:** the new physical-domain check withholds **1,947,758** ice-depth values, versus **1,847,439** in the earlier invalid-constant-only tally. The additional **100,319** values include native `-1` examples whose meaning is not resolved by the acquired label. Negative/excluded model depth is not no ice; model surface stability is not detected or recoverable ice. This is a separately named quality interpretation, not a changed original Dar_044 count.

**Exosphere clock review:** the initial full run stopped because the new canonical-component clock policy was being compared directly against the old arithmetic decoder. The corrected study faithfully replays the old decoder, then separately measures clock-policy and added-orbit effects. An eight-file edge sample and the corrected full run pass. The native second=60 rounding/carry meaning remains unresolved; old outputs were not changed or silently reclassified.

**Time finding:** SEE's same-June-October FUV median decreases from **0.02607 W/m2 (2023)** to **0.02196 W/m2 (2026)**, with 153/151/151/151 valid dates across 2023-2026. This is a historical comparison, not demonstrated repeating seasonality or a safe-month forecast. Mode, epoch, coverage and quantity matter more than a simple lowest-value ranking.

**Validation record:** representative samples, source/artifact hashes, native decoding, crosschecks and saved execution are documented in [subject verification](../data/verification/latest_subject_eda.txt). The subject notebooks Dar_045-055 and synthesis Dar_056 have saved execution for every code cell without saved error outputs. This is recorded execution evidence, not a fresh rerun or a claim about the current pipeline test suite. The PRP zero-quantile helper correction is separate from its published p05/p50/p95/p99 intervals; retain the executed source version. Failed/sampled runs are not accepted full results.

The subject JSON is the frozen initial scope plan, not a live completion tracker; its original planning/remaining-work labels do not override completed provenance or saved execution. Recorded acquisition/library audits apply only to their stated cutoff and selected files, not a current live inventory or an extra whole-archive checksum claim.

### Stage 4 handoff - proposed, not integrated

[Executed Dar_056](Moon/Stage3_Requirements/Dar_056_stage4_evidence_rule_synthesis.ipynb) compiles **64 proposal rows: 15 conditional hard constraints, 11 conditional soft preferences and 38 evidence guards**. It covers all eleven subjects and 27 outline factors, with 427 analysis-column and 349 native/derived-field records, eight cross-subject findings and four shared-evidence families.

- **Read the handoff:** [proposal CSV](../data/processed/analysis/stage4_environment_proposal/20261110T212854527708Z_fa4445/proposed_requirement_register.csv), [subject scope/conclusions](../data/processed/analysis/stage4_environment_proposal/20261110T212854527708Z_fa4445/subject_scope_and_conclusions.csv), [cross-subject findings](../data/processed/analysis/stage4_environment_proposal/20261110T212854527708Z_fa4445/cross_subject_findings.csv).
- Each row retains source-specific logic, evidence origin, quantity/units, applicability, reviewed existing-rule crosswalk, adoption/authority gaps and Passed/Failed/Unknown semantics. Historical source-creation TODO notes are not current unfinished-analysis claims.
- **Hard Failed/Unknown cannot be offset by preferences.** Inapplicable requirements are not selected or counted as Passed; evidence-use failure is not automatically site failure. Missing soft values are not zero-filled. Mission/equipment profiles remain optional.
- Proposal rows are not independent risk weights or 64 independent mission requirements. During later adoption, consolidate the same underlying requirement/quantity and preserve source dependencies; Sun/UV/photoemission proxies and related Apollo accounts must not be double-counted.
- Missing local demand, response, applicable capability/limit and adoption authority remain **Unknown**. Sparse primary radiation, bounded response windows, finite model horizons, short historical missions and unreadable/unreviewed PDF material remain declared limits—not invented operational evidence.
- **No scientific limit/weight is adopted by these EDA studies.** Their research proposals and frozen source pins are separate from the active standalone `assumption_NASA_values` software-test policy. Scientific adoption and mission-specific engineering validation remain necessary; test scores and skipped blank inputs are not operational qualification.

## Radiation

- **Steps taken:** checked CRaTER instrument states, GOES quality flags, dates and separate detector/energy/platform/version groups; reviewed shielding scenarios and derived a terrain sky-openness indicator.
- **Expanded findings (Dar_049):** **79 separate series / 35,281 daily rows**, spanning 2023-07-01 to 2026-10-31 across the declared instruments/cohorts, retain calendar support and daily upper tails. The CRaTER/FUV descriptive level correlation **0.464** becomes **-0.001** for consecutive-day differences; pooled levels are not a stable causal/dose model. **Earlier Dar_041 coverage:** CRaTER 1,091 dates / 94.1 million records, GOES-16/19 524/791 dates and strict channel/time support of 10.48%/10.82%; the 660,000-record primary sample is not a complete event census.
- **Inference:** sky openness supports relative geometric comparisons. Orbital counts and the 96 published reference scenarios are **not candidate crew doses**; more shielding is not universally safer.
- **Dar_044 extension:** joined contemporaneous SEE FUV with the accepted CRaTER daily counter summaries on **1,050 valid UTC dates**. Descriptive Spearman correlation is **0.464**, not a dose relationship, causal result or site-safety rule; calibration, sampling and common time trends remain relevant.

## UV

- **Steps taken:** retained the candidate sunlight/UV-opportunity proxy; parsed downloaded SOLSTICE FUV/MUV daily spectra, accepting only complete 1-nm bands with quality=0 and finite nonnegative irradiance/uncertainty.
- **Earlier SOLSTICE-reference findings:** the **2003-05-14 to 2020-02-25** solar-reference record contains **5,700 FUV / 5,760 MUV valid daily band integrals**. This is time-varying solar irradiance, not terrain-adjusted intensity or biological dose at our 21 candidates. The earlier northern LAMP pilot lacked south-polar coverage; Dar_044 reviews separate south-polar products below.
- **Inference:** lower opportunity can be a stated preference, but sunlight and UV share the same input and must not be counted twice as independent weights.
- **Dar_044 steps/results:** integrated **1,206 SEE daily spectra (June 2023-October 2026)**, retaining model-filled-bin/flare-removal and uncertainty context. Complete positive-bin screening supports **1,206 FUV days (115-180 nm), but only 139 EUV days (27-115 nm)**. Other EUV bands/dates were not substituted; unresolved zero bins are not zero exposure. SEE and historical SOLSTICE were not stitched as a calibrated single instrument. **Dar_045 expands the spectral/map review:** all 1,206 SEE spectra and native pixels of 20 LAMP maps; supported days are 727 for XUV, 139 for EUV and 1,206 for each of 50-115 nm, FUV and 180-190 nm. The supported FUV median is **0.0242102 W/m2** across its declared daily cohort, not a candidate-local dose.

## Plasma and charging

- **Steps taken:** retained published charging regimes and separate P1/P2 merged context; expanded native ESA analysis to **all 1,173 files / 53,860,929 mode-records** in Dar_046. Native species/modes, quality, clocks/cadence and geometry remain explicit. The earlier THB merged baseline has its own 36-file / 319,946-record cohort, not extra independent ESA observations.
- **Earlier merged-baseline findings:** observations span **2023-10-01 to 2026-09-29**. File-level median timestamp spacings range from **137.571 to 550.738 seconds**, unlike the nominal 96/384-second metadata description. Record counts therefore do not establish elapsed valid-time coverage. **Lower plasma density or more darkness is not automatically safer.**
- **Limit:** these are spacecraft plasma/field observations, not candidate surface-potential measurements. Geometry strata are not certified plasma regimes; local voltage and discharge risk remain Unknown.
- **Earlier Dar_044 subset:** read all **40 P2 merged files**, retaining position strata, plus **82 preselected ESA day files** (first/last available date per month, six modes separate). ESA Q fields are virtual: explicit native quality=0 screening was required. The reduced-electron mode has only **4.33% zero-quality-flag records before further screening**; 231 ambiguous/missing mode-clock records were withheld and 5,482 file-boundary context records excluded from nominal-day bins. FUV/P2 density has **1,095 paired valid dates, correlation 0.135**: weak descriptive association, not a surface-charging response. **Expanded Dar_046 findings:** reduced-electron quality=0 records are **4.24%** before further screening, versus the earlier subset's 4.33%. Full-mode ion/electron daily association is **0.955**, reduced-mode **0.222**; neither is surface voltage or a safe-density rule. All 1,374 shared earlier day/series rows retain their support within floating-point tolerance.

## Temperature and heat

- **Steps taken:** compared Diviner temperature by location, local time and solar phase; checked fixed observation cohorts, terrain relationships and dated-product quality.
- **Dated Diviner findings (Dar_040/041):** **812 dated query products** across three regions yield **zero strict-quality rows**. Existing phase products provide five complete candidate thermal profiles, but only one passes the current context filters.
- **Inference:** cohort choice changes temperature summaries; no universal terrain correction was established. Phase averages are not instantaneous extremes or equipment temperatures. One supported candidate alone cannot establish a thermal preference winner.
- **Dar_044 steps/results:** read all **30 Apollo HFE tables / 520,977 records**, retaining flags and sensor identity; 131 undated records remain in diagnostics, not invented calendar dates. Processed all **2.88 million south-PRP model triangles** in chunks. The seven **bounding-box maxima** of modelled surface temperature are **305.95-342.08 K**; triangle-centre inclusion is not candidate-footprint validation. Annual mean at 2 cm and maximum at the surface are different quantities, not a thermal-cycle amplitude. These model/reference inputs do not qualify the rejected dated Diviner rows or supply equipment temperatures. **Expanded Dar_047/050 findings:** all 30 HFE tables / 520,977 records retain depth/deployment/clock identity; Apollo 15 probe 1 has a 1972 matched-day p95-p05 span of **5.67 K at 35 cm versus 0.160 K at 139 cm**. Native PRP weighting and boundary checks remain spatial model statistics, not a chronological equipment envelope.

## Sunlight, shadow and communications

- **Steps taken:** compared solar/Earth visibility and modelled horizons for seven regional reference points; Dar_054 extends the earlier short windows to **2020-2021**, with **982,464 samples / 56 scenario-target tracks** and cadence sensitivity. Observer height, horizon radius and sampling remain explicit.
- **Findings (Dar_054):** at 2 m height / 20 km horizon radius, the Leibnitz/Malapert reference points have similar sampled Sun-clear fractions (**0.214/0.233**) but longest observed blocked-sample spans of **2,819/691 h**. Mean visibility alone misses persistence. These are point/configuration model histories, not the research candidates or current test patches; zero sampled blocking is not guaranteed continuous sunlight, and Earth visibility is not a working RF link.
- **Limit:** power endurance and communications margins still require applicable time histories and response models.

## Monthly and quarterly comparisons — Dar_043

- **Steps taken:** [executed Dar_043](Moon/Stage3_Requirements/Dar_043_temporal_environment.ipynb) using existing CRaTER/GOES daily summaries and downloaded UV/plasma files. Built **101 separate series, 2,352 year-month rows and 856 calendar-quarter rows**, with 18 level/coverage/daily-peak plots. Quarters are recomputed from days, not averaged monthly medians; years, channels, versions, UV modes and plasma geometry strata are not pooled.
- **Results:** in 2025, CRaTER monthly medians of daily GOOD-counter medians range **24–27 counts/SEC record**; all-position ARTEMIS monthly medians of daily ion-density medians range **2.27–4.115 ions/cm³**. In 2019, FUV monthly medians of daily band integrals range **0.0219186–0.0222434 W/m²**. These examples have different coverage and do not establish a repeating seasonal pattern or safest month. Tables retain each period's valid days, samples and, for GOES only, qualified seconds.
- **Limits:** Dar_043's historical **SOLSTICE** UV does **not overlap** its recent plasma/radiation inputs; no simultaneous correlation or forecast was inferred from that cohort. Dar_044 separately analyses contemporary SEE overlap. Calendar quarters are **not lunar seasons**; missing/flagged periods stay missing, and daily maxima remain available because monthly medians can conceal short peaks. Existing illumination windows and flagged dated thermal records were not stretched into annual histories.
- **Handoff:** Step 4 adds E14–E16 temporal evidence guards; Step 5 exports seven checked tables and a historical time-context report without new candidate scores or operational passes. [Accepted run and verification](../data/verification/latest_temporal_environment.txt).

Run again from the repository root: `.venv/Scripts/python.exe "darrel stuff/EDA/Moon/Stage3_Requirements/stage3_temporal_eda.py"` (or run the notebook). `--sample` is bounded validation, not the full analysis. The CDF reader dependency is pinned as `cdflib==1.3.6` in `../requirements.txt`.

## Terrain and data quality

- **Steps taken:** checked DEM/crop alignment, source uncertainty, spatial scale, coverage and temperature associations.
- **Findings:** 28 source/crop checks at 1,792 positions agreed within the stated tolerance. Missing elevation is not permanent shadow; associations change with scale. Thermal-center association does not establish whole-footprint coverage.

## Seismic activity and impacts

- **Steps taken:** reviewed related Apollo seismic catalogs and selected new-crater detections, including event independence and observation coverage.
- **Catalog findings:** the 58/59 catalog entries are related, not 117 independent events. The 222 selected crater detections do not establish local mission-window impact probabilities.
- **Dar_044 steps/results:** decoded **731 MHZ files / 415.5 million raw vertical samples** and **730 ATT timing files** across 1973-1974. About **2.04%** of each channel family's sample values use the missing code. Response metadata is available at both ends of all MHZ traces, but no response removal or event detection was performed. Clock gaps, raw-count variation and crew/active-source signals are not moonquake rates or candidate ground acceleration. **Expanded Dar_053 findings:** **2,193 three-axis motion files / 1,246,454,631 native samples**, with **1,220,986,653 valid native samples**, preserve MH1/MH2/MHZ and mode. The **300** bounded inverse-response experiments are not qualified event peaks or polar structural demand; all 731 earlier vertical traces replay without changed support.

## Dust, resources and imagery

- **Steps taken:** reviewed dust/chemistry evidence coverage and environmental image/radar context.
- **Research-candidate image coverage:** ShadowCam covers 3/21 examples and Mini-RF 19/21; this does not describe the separate 77-row pipeline fixture. Darkness, radar backscatter and spectral indicators do not prove recoverable ice, soil strength or safety. Candidate-specific dust contamination and equipment degradation remain unqualified.
- **Dar_044 dust:** processed all 36 LDEX current/mass tables, including **677,271 current records on 166 recorded dates**. Current/background remain separate; mass summaries retain quality and saturation classes rather than inventing a science-good event class or surface dust loading. **Expanded Dar_048 findings:** 441,166 mass-catalog entries include **9,041 numerically supported entries below their reported native threshold**; numerical support does not silently reclassify them as qualified impacts.
- **Dar_044 LAMP:** sampled all four southern map families at fixed stride 4, joining quality=0, positive exposure and SNR>=3. Supported fractions of the sampled south-polar domain are **46.51% long, 98.77% Lyman-alpha, 3.79% off-band and 28.82% on-band**. `ERROR` is SNR, not an error bar. White/masked pixels are not proof of darkness or zero UV; brightness/albedo are not local irradiance.
- **Dar_044 neutrons/resources:** read complete records on **74 preselected LEND dates**, first/last available date per month. SETN and CSETN2 each have all-zero supported spectra on **52 selected dates**; channel activity/background/response remain unqualified, so these zeros do not establish absence of neutrons or safe radiation. Raw spectra and PRP model ice-stability depths do not establish recoverable ice.

## Exosphere

- **Steps taken:** Dar_051 expands the earlier 36-file screen to **all 2,715 selected NMS orbit/species files**, retaining abundance, uncertainty, geometry and historical clock policy separately.
- **Expanded findings (Dar_051):** **592,721 records / 876 daily rows**, covering 2013-11-21 to 2014-04-17; **33** noncanonical/missing-clock records are held explicitly. Added orbit coverage changes matched-date medians, so clock-policy and orbit-selection effects are analysed separately. **Earlier Dar_044 subset:** 10,869 records on 12 sampled dates per species, with sampled altitude 1.88-145.01 km. Its sparse support is not the full selected cohort.
- **Limit:** full selected orbit coverage is still historical spacecraft sampling, not a surface concentration, modern atmosphere or life-support assessment. Apollo outgassing/background cases reinforce the need for contamination checks.

## Standalone soil/regolith properties - Dar_057

[Notebook](Moon/Stage3_Requirements/Dar_057_lunar_soil_properties.ipynb) | [Analysis helper](Moon/Stage3_Requirements/stage3_soil_eda.py) | [Tables, figures and source provenance](../data/processed/analysis/subject_soil/)

**Question and scope:** compare the available soil-property distributions and associations before deciding whether they can inform a later environmental algorithm. This is a standalone study: no dust/thermal/mobility/engineering-response model, candidate-site mapping, soil scoring domain or pipeline edits. Sample IDs and missions distinguish observations; sample coordinates and collection-location tables are not required outputs.

### Evidence and method

- **Handbook of Lunar Soils**, JSC 19069, supplied as `D:/projects/NASA Dataset/soils_hb.pdf`: examine all 1,183 PDF pages for selected scalar soil properties. The supported cohort contains **168 sample-sheet identities**: Apollo 11 **7**, Apollo 12 **14**, Apollo 14 **9**, Apollo 15 **30**, Apollo 16 **40**, Apollo 17 **68**. These are related historical non-core returned samples, not 168 independent landing-site experiments or every measurement in the handbook.
- Retain reported major-oxide percentages, `Is/FeO`, maturity-table agglutinate percentages and grain-size descriptors `Mz`/`Md`. Keep blanks missing. Each extracted number retains its PDF page, line, units and source text. Do not mix adjacent petrography/trace-element columns, average competing analyses, or guess missing decimal points. The extraction holds include the `21003` sample-ID/mission inconsistency, four out-of-range printed/OCR percentages and ambiguous grain-fraction assignments; no silent repair is made.
- The handbook's default is the less-than-1-mm fraction unless otherwise stated. For wrapped grain-size entries containing both less-than-1-cm and less-than-1-mm results, select only the explicitly labelled fine-fraction value. Leave the other descriptor missing when its fraction cannot be established. Supported values: **139 maturity indices, 75 Mz values, 22 Md values, 60 maturity-table agglutinate percentages, 131 FeO values and 131 Al2O3 values**. Support differs by property and mission.
- Use pairwise-complete Spearman associations with pair counts; report nominal multiple-comparison-adjusted statistics as exploratory, not evidence of independent site trials. Compare within-mission associations, mission-adjusted rank residuals, leave-one-mission-out results and distinct-pair-profile sensitivity. Stratified bootstrap/permutation results describe conditional sample sensitivity, not population confidence or a causal effect. Do not impute missing values or correlate unpaired mission-labelled environmental histories.
- **68 complete eleven-oxide profiles** support a closure diagnostic; reported sums span **98.90-101.88%**. Values are not forcibly renormalised. Chemical percentages are compositional, so an association can reflect shared closure, geological mixtures or analytical dependencies rather than an independent effect. `Is/FeO` also contains FeO in its definition.
- Reuse the label-driven reader for **six Apollo 15 penetrometer runs / 94 native records**. Keep cone/plate geometry, reported depth limitations and the collapse flag. Loading-path points are not independent repeated soil-type experiments. No chemical profile is joined to a penetrometer run by mission label alone.
- **Surveyor comparison:** [USGS analysis of Surveyor 7](https://www.usgs.gov/publications/implications-surveyor-7-results) reports lower Fe in the highland material than in the previously analysed mare material. This qualitatively agrees with the iron/aluminium composition contrast in the Apollo data, but is not a matched sample comparison. The handbook contains no Surveyor sample sheets; no harmonized local Surveyor numerical table is pooled with these oxide percentages. [NASA/JPL Surveyor 5](https://www.jpl.nasa.gov/missions/surveyor-5/) supplies additional mission context. Regional D37 geology, D34 M3 L1B radiance and D30 radar products are different quantities, not extra soil specimens; without a requested spatial join or compatible derivation they remain context rather than fabricated correlation pairs.

### Findings relevant to a later environmental algorithm

| Relationship | Supported comparison | What can be used later |
| --- | --- | --- |
| FeO versus Al2O3 | **rho = -0.908, n=130**, six missions; mission-adjusted rank association **-0.741**. The association remains negative when any one mission is excluded. | A composition/regime distinction, not an iron-is-bad or aluminium-is-good safety rule. Avoid separately weighting correlated oxides as independent evidence. |
| FeO versus TiO2 | **rho = +0.789, n=126**; mission-adjusted association **+0.794**. Without Apollo 16 the pooled rho is approximately **+0.507**, illustrating cohort sensitivity. | Useful chemical context; not a demonstrated environmental hazard or an adopted scoring direction. |
| Maturity versus agglutinates | **rho = +0.702, n=47**, only three missions; **36 paired samples are Apollo 17**. Mission-adjusted association **+0.719**. | Related maturity indicators may be redundant; neither higher nor lower maturity is shown to be safer. The sample imbalance limits transfer. |
| Maturity versus Mz | Weak pooled association: **rho = -0.154, n=70**, five missions; conditional bootstrap range approximately **-0.370 to +0.085**. Apollo-specific and leave-one-mission-out results differ. | Do not infer grain size from maturity or adopt a universal maturity-to-fineness rule from this cohort. |
| Mz versus Md | **rho = +0.764, n=11**, with sparse mixed mission support. | Potentially related grain descriptors, but too little paired support for a universal conversion or redundant-feature decision without further evidence. |
| Penetrometer stress contrasts | Cone maxima approximately **342-347 kPa**, plate maxima **34.1-34.3 kPa**; tool areas differ by about a factor of ten. Four runs have depth limitations; one includes documented trench collapse. | Geometry/protocol are essential context. The apparent tenfold stress difference is not evidence of a tenfold soil-strength contrast or a transferable threshold. |

**Illustrative composition medians, not mission-wide uniform soil values:** Apollo 11 has FeO **15.83%** and Al2O3 **13.21%** (four supported records each); Apollo 16 has FeO **5.365%** (40) and Al2O3 **26.90%** (39). Apollo 17 spans FeO **8.45-22.04%** and TiO2 **1.39-10.31%** in the extracted supported records, so a single mission/site label conceals substantial sample variability.

**End-goal conclusion:** the evidence supports adding soil-property descriptors to a future research comparison, but does **not** establish which soil type provides the best base environment or whether soil type causes an operational/environmental outcome. There is no specimen-matched outcome or appropriate negative comparison. NASA mission selection/success is not a ground-truth soil-suitability label, and historical Apollo/Surveyor coverage does not establish polar-site properties.

`pipeline_research_candidates.csv` separates candidate chemistry, grain-size and maturity descriptors from reference-only mechanical evidence. It explicitly leaves scoring direction, thresholds and weights unestablished. No pipeline inputs, schema, scoring formulas, gates, weights or outputs are changed by this EDA.

### Reproduce

Open the notebook or run from the repository root:

```powershell
.\.venv\Scripts\python.exe -B "darrel stuff/EDA/Moon/Stage3_Requirements/stage3_soil_eda.py" --pdf "D:/projects/NASA Dataset/soils_hb.pdf" --pdf-python "C:/Users/silen/AppData/Local/Programs/Python/Python310/python.exe"
```

The analysis environment uses the existing NumPy, pandas, SciPy and plotting dependencies; the explicitly selected PDF Python needs `pypdf`. In the notebook, set `SOIL_PDF_PYTHON` if the default `python` does not contain it. `--sample` selects a bounded extraction sample, not the full EDA. Generated source text, extraction holds, figures, tables and provenance stay under `data/processed/analysis/subject_soil/`, separate from the standalone scoring runtime.

## Soil-only NASA versus wider mission evidence - Dar_058

[Notebook](Moon/Stage3_Requirements/Dar_058_soil_cross_mission_metrics.ipynb) | [Analysis helper](Moon/Stage3_Requirements/stage3_soil_comparison_eda.py) | [Source pins](Moon/Stage3_Requirements/stage3_soil_comparison_config.json) | [Derived tables and figures](../data/processed/analysis/soil_cross_mission/)

**Purpose:** identify soil-only measurements, reference intervals and categorical boundaries that could inform a later pipeline field. Compare actual mission-area evidence, not the pipeline's assumed input rows. This is a soil study, not a combined environmental-response model or an adopted soil scoring domain.

### Real-world evidence and comparable units

- [USGS Historical Lunar Data Archive, Lunar Sourcebook Table 7.15](https://lunar-consortium.astrogeology.usgs.gov/data/chem_min/tab7_15.asc) supplies six selected Apollo mission references and three Luna references in oxide wt%. Retain the ten Apollo regional references separately; they overlap mission averages and are not ten additional independent missions. Apollo 11 is represented by soil 10002, whereas other entries are selected averages: these are published reference profiles, not equivalent random mission-wide surveys.
- [Chang'e-5 primary study](https://pmc.ncbi.nlm.nih.gov/articles/PMC8974359/), Table 1, supplies one bulk-soil XRF reference. Its repeated laboratory measurements are technical repeats, not extra landing areas. [Chang'e-6 primary study](https://pmc.ncbi.nlm.nih.gov/articles/PMC11495410/), Table 2, supplies two soil aliquots; average them once for the mission-level comparison and explicitly exclude the basalt fragment and later trace-element rows. This yields **11 mission references: six NASA, five non-NASA**. Laboratory/sieve methods are not fully harmonized, so descriptive differences are not an isolated agency effect.
- Use the Dar_057 individual Apollo sample cohort as a separate reference-range sensitivity. Do not count those related specimens as additional independent missions or merge their sample-level distributions with mission averages.
- The Chang'e-5 supplementary grain table has **80 Apollo analysis records, five missions and 23 parent sample IDs**. Despite broader Apollo/Luna wording in the article narrative, the actual supplementary table has no Luna analyses. Preserve this attribution. Related parent/depth/subsample records are not 80 independent operating areas. Compare their reported phi statistics with the Chang'e studies' model-mass grain statistics; retain number-versus-mass and method distinctions.
- Surveyor remains external qualitative NASA context: the [USGS Surveyor 7 analysis](https://www.usgs.gov/publications/implications-surveyor-7-results) identifies lower Fe in highland material than in earlier mare analyses. Do not convert grouped/atomic-element summaries into oxide wt% by assumption. No suitable numerical Surveyor soil cohort is merged here.
- The available collection is broader **real-mission evidence**, not a representative whole-Moon survey or an unvisited-site control. No global general-soil population distribution is inferred. Original source files, source tables and source hashes are retained under `data/reference/lunar_soil_comparison/`. The archived ASCII's Apollo 11 Na2O value `47` and `P2O3` label are held out rather than silently repaired or remapped.

### Differences and explanations

All values below are the selected mission-reference oxide percentages, not whole-area uniform conditions:

| Mission | FeO wt% | Al2O3 wt% | TiO2 wt% |
| --- | ---: | ---: | ---: |
| Apollo 11 | 15.3 | 13.6 | 7.8 |
| Apollo 12 | 15.1 | 12.9 | 3.0 |
| Apollo 14 | 10.4 | 17.4 | 1.7 |
| Apollo 15 | 14.3 | 14.6 | 1.4 |
| Apollo 16 | 5.1 | 27.3 | 0.54 |
| Apollo 17 | 12.2 | 17.1 | 4.2 |
| Luna 16 | 16.7 | 15.3 | 3.4 |
| Luna 20 | 7.0 | 22.3 | 0.55 |
| Luna 24 | 19.8 | 12.5 | 1.3 |
| Chang'e-5 | 22.5 | 10.8 | 5.0 |
| Chang'e-6 | 17.2 | 14.35 | 2.7 |

- **There are differences, but no NASA-only chemical signature:** selected NASA-reference FeO median is **13.25%**, versus **17.20%** in the five wider mission references. However, all five wider references' TiO2 values fall within the NASA-reference interval **0.54-7.8%**. Luna 20 has a highland-like low-Fe/high-Al pattern resembling Apollo 16, whereas Luna 16 and Chang'e-6 are compositionally nearer Apollo 12 in the selected three-oxide log-ratio diagnostic. This describes geological composition, not suitability or a NASA preference policy.
- **Geological mixtures matter within NASA areas:** Apollo 17 regional references span FeO **8.8-16.7%**, TiO2 **1.7-8.4%**, and Al2O3 **12.0-20.7%**. The source distinguishes mare and massif/light-mantle-related materials. Such within-mission variation contradicts a single agency-labelled soil type. The Chang'e papers discuss local basalt versus non-basaltic ejecta mixing and different source material; these are supported geological explanations, not a causal test of agency membership.
- **Grain differences overlap historical support:** Chang'e-5 mass median is **52.54 um**; Chang'e-6 is **35.03 um**. Using the published mean-phi definitions, **47/80** Apollo analyses are coarser than Chang'e-5 and **66/80** are coarser than Chang'e-6. After replacing related analyses with a median per parent ID, the comparisons are **15/23** and **20/23**. Both modern mean/median phi values still lie inside the observed 80-record Apollo ranges. These are cohort/method sensitivities, not independent site-probability estimates. The phi-derived equivalent diameter is not an arithmetic average of particle diameters.
- **Maturity is not a NASA preference:** the 80-record table contains **26 immature, 33 submature and 21 mature** analyses. This is a different, partly depth-related cohort from Dar_057; its labels are not evidence of equivalent mission outcomes. Chang'e-5's grain-inferred maturity must not be treated as an independent measured Is/FeO value in a grain/maturity correlation.
- **Density needs its own protocol:** reported returned-soil bulk densities are **1.2387 g/cm3** for Chang'e-5 and **0.983 g/cm3** for Chang'e-6. The corresponding true grain densities are **3.1952** and **3.035 g/cm3**, respectively. Packing/preparation and depth affect these quantities; they are not interchangeable with each other or in-situ density profiles.

### What can become a soil-only pipeline field?

| Candidate | Defensible use | Range/threshold interpretation |
| --- | --- | --- |
| Soil chemistry: FeO, Al2O3, TiO2 | Measured composition or regime context, with analytical/sieve support | **No preferred or forbidden range established.** Percent plausibility 0-100 is data validation, not a site-failure rule. |
| Is/FeO maturity class | Categorical descriptor | [NASA Noble reference, PDF page 8](https://www.nasa.gov/wp-content/uploads/2019/04/05_1_snoble_thelunarregolith.pdf): immature **<30**, submature **30-60**, mature **>60**. This study assigns equality at 30/60 to submature under that reference convention; other publications differ at boundaries. Categories are not best-to-worst. Check original FMR/fraction definitions before transfer; a generic bulk-soil fraction must not be assumed equivalent. |
| Mass-median grain diameter | Continuous soil descriptor with weighting/fraction/method metadata | The [NASA geotechnical reference](https://ntrs.nasa.gov/citations/20220014634), PDF page 1, describes **40-130 um** as a typical historical median-size range, **not a preferred interval**. Chang'e-6's reported 35.03 um demonstrates why it cannot be a universal exclusion rule. |
| Bulk density | Protocol/depth-dependent descriptor | **No universal preferred range or gate.** Do not substitute true density or loose returned-sample packing for in-situ bulk density. |
| Nearest-reference composition distance | Optional research diagnostic: centred-log-ratio distance for positive FeO/TiO2/Al2O3 | Lower means more compositionally similar to the selected Apollo reference only. It is **not** an adopted NASA metric, suitability score or evidence that closer is better. Zero/detection-limit treatment requires explicit support; no pseudocount is invented. |

**Why not turn the NASA ranges into gates?** The selected Apollo mission-reference FeO interval is **5.1-15.3%**, while Dar_057's individual Apollo sample interval is **4.09-22.04%**. Merely changing aggregation radically changes the apparent boundary. A hypothetical upper gate of 15.3% would exclude Luna 16, Luna 24, Chang'e-5 and Chang'e-6 reference profiles. A sample p95 gate of 17.58% would instead exclude Luna 24 and Chang'e-5. These flags are conditional reference-range diagnostics, not failed-site conclusions; they demonstrate an unsupported rule's transfer sensitivity. Chang'e-5's 22.5% is also a point estimate with reported FeO uncertainty of 0.33 wt% (k=2), not a precisely known natural boundary.

**Recommendation:** retain soil composition, grain-size definition and maturity class as individual/categorical research fields. `metric_candidate_evidence.csv` and `reference_range_audit.csv` document which quantities/ranges are observed and why none is an adopted preference or hard gate. No chemical exclusion, soil suitability score or weight is justified by NASA-versus-other-mission membership alone. No active pipeline file is changed.

### Reproduce

Open Dar_058 or run from the repository root:

```powershell
.\.venv\Scripts\python.exe -B "darrel stuff/EDA/Moon/Stage3_Requirements/stage3_soil_comparison_eda.py"
```

The helper works offline with the pinned archived sources and the declared completed Dar_057 baseline. It writes its tables, figures, source-quality holds and provenance under `data/processed/analysis/soil_cross_mission/`; it does not download files or import the active scorer. Source hashes, cohort identities and units must match the pinned selection; missing/changed sources fail explicitly.

## Equipment and past missions

- **Steps taken:** compared Apollo resource predictions with actual usage; analysed laboratory batteries, Apollo soil tests and nominal crew-load sensitivities.
- **Findings:** **16/18 Apollo 17 resource consumptions exceeded predictions**. Rounded oxygen headroom reaches zero, reinforcing the need for contingency analysis. Battery protocols and six historical soil tests are references, not qualification of our lunar equipment. Crew-rate sensitivities are not actual stocks or life-support adequacy.
- **Dar_044 PDF cases:** coded seven source/page-linked cases covering calibration, deployment/dust, outgassing and duty cycle, signal attribution, illumination, conditional decisions and equipment cooling. They guide analysis and later rule applicability; historical redlines and secondary journal diagnoses were not adopted as modern requirements.

<a id="newly-acquired-inputs-and-pdf-leads"></a>
<a id="new-download-eda-dar_044"></a>
## New-download EDA - Dar_044

**Earlier screening baseline:** the subset counts and checks in this section belong to Dar_044. The expanded subject studies above supersede its coverage for ESA, NMS, LEND, native LAMP and three-axis seismic interpretation; do not label a screening subset as the latest full cohort.

[Dar_044 notebook](Moon/Stage3_Requirements/Dar_044_acquired_environment.ipynb) produces **18 tables / 10 plots**. It analysed **2,986 science files across ten source families**, generating 70 series, 45,465 daily rows, 2,469 monthly rows and 874 quarterly rows. This is the declared cohort, **not every downloaded file or an event census**.

- **Full selected collections:** 1,206 SEE days; 40 P2 monthly files; 30 HFE tables; 36 LDEX tables; all 2.88 million PRP triangles.
- **Bounded collections:** 82 ESA days; 36 NMS orbit/species files; 74 LEND days, selected by calendar filenames before values were read. LAMP uses stride 4 in 20 maps with aligned support. PSE covers two years of MHZ/ATT, not all three motion axes.
- **Method:** validate receipts/hashes and labels; screen quality, fill values and clock ambiguity; preserve body, depth, units, modes, gaps and provenance; aggregate UTC months/quarters without filling missing periods. SEE daily band maxima are maxima of daily means, not subdaily flare peaks.
- **Results:** see the environmental categories above. Contemporary FUV now supports matched-date context comparisons; it does not identify a safest month or prove surface dose/charging. No repeatable lunar-season claim or forecast is made.
- **Handoff:** these are recorded Step 3 research outputs. They did not themselves adopt operational requirements; the separate standalone test policy is configured independently. Equipment response, local exposure, physical hazard rates and applicable limits remain unresolved; missing mandatory evidence stays Unknown.

Reproduce with `.venv/Scripts/python.exe "darrel stuff/EDA/Moon/Stage3_Requirements/stage3_acquired_eda.py"` or the notebook. Use `--sample` only for bounded checks. [Source/PDF applicability](../research/Research_Notes.md#expanded-pdf-library-and-environmental-impact).

<a id="final-comparison-scope"></a>
## Final results and findings

- The EDA supports **relative environmental comparisons**, not an absolute safest-site claim.
- All eleven subject studies and the Stage 4 synthesis have completed artifacts within their recorded scopes. Dated inputs retain month/quarter/four-month/half-year/year/two-year/calendar-season support; static products and short historical missions are not fabricated into histories. No safe-arrival month or absolute safest-site claim follows.
- The **archived research prototype's** illustrative filters retain **14 candidates and exclude seven**; these are not outcomes of the current software-test fixture. The science view finds **two non-dominated trade-off options** using radiation geometry, UV opportunity and Earth visibility; the original visibility score remains a baseline.
- Thermal comparison is withheld because only one filter-passing candidate has a complete comparable profile. Plasma is not forced into a lowest-is-safest ranking.
- Mission/equipment inputs remain optional for the demo. Operational suitability stays Unknown without applicable requirements, response evidence and limits; preference benefits cannot compensate for mandatory safety failures.

## Evidence and notebook conventions

[Source register](../research/Research_Notes.md) | [Science/model assumptions](../research/lunar_science_models.json) | [Active pipeline guide](../env_pipeline/README.md) | [Archived research comparison](../env_pipeline/legacy_1/README.md)

**Analysis source references:** non-sample subject artifacts supporting the documented evidence. The synthesis remains its own frozen, pinned handoff; reviewing a newer individual subject run does not silently change that handoff or a pipeline rule.

| Notebook | Recorded analysis source |
| --- | --- |
| Dar_045 | [`subject_uv/20261110T231614701627Z_e1ffa3`](../data/processed/analysis/subject_uv/20261110T231614701627Z_e1ffa3/findings.json) |
| Dar_046 | [`subject_plasma/20261110T231619494574Z_f61cb6`](../data/processed/analysis/subject_plasma/20261110T231619494574Z_f61cb6/findings.json) |
| Dar_047 | [`subject_hfe/20261110T231624967300Z_04aff6`](../data/processed/analysis/subject_hfe/20261110T231624967300Z_04aff6/findings.json) |
| Dar_048 | [`subject_dust/20261110T231630522312Z_a8ddbb`](../data/processed/analysis/subject_dust/20261110T231630522312Z_a8ddbb/findings.json) |
| Dar_049 | [`subject_radiation_time/20261110T233725005604Z_72515a`](../data/processed/analysis/subject_radiation_time/20261110T233725005604Z_72515a/findings.json) |
| Dar_050 | [`subject_polar_thermal/20261110T233730894536Z_e98b6f`](../data/processed/analysis/subject_polar_thermal/20261110T233730894536Z_e98b6f/findings.json) |
| Dar_051 | [`subject_exosphere/20261110T233735590232Z_dffb7c`](../data/processed/analysis/subject_exosphere/20261110T233735590232Z_dffb7c/findings.json) |
| Dar_052 | [`subject_neutrons/20261110T180136708725Z_23f6a8`](../data/processed/analysis/subject_neutrons/20261110T180136708725Z_23f6a8/findings.json) |
| Dar_053 | [`subject_seismic/20261110T183033924956Z_ba610a`](../data/processed/analysis/subject_seismic/20261110T183033924956Z_ba610a/findings.json) |
| Dar_054 | [`subject_terrain_time/20261110T210226961886Z_f00b81`](../data/processed/analysis/subject_terrain_time/20261110T210226961886Z_f00b81/findings.json) |
| Dar_055 | [`subject_operations/20261110T211407977377Z_3abbf8`](../data/processed/analysis/subject_operations/20261110T211407977377Z_3abbf8/findings.json) |
| Dar_056 | [`stage4_environment_proposal/20261110T212854527708Z_fa4445`](../data/processed/analysis/stage4_environment_proposal/20261110T212854527708Z_fa4445/findings.json) |

Detailed tables, figures and provenance remain in `../data/processed/analysis/` and the accepted notebooks, especially Dar_033-056. Original notes/results/instructions are archived through `../data/verification/latest_eda_notes_cleanup.txt`.

**Notebook conventions:** name new notebooks `Dar_0xx_descriptive_name.ipynb`, using the next unused number across Earth and Moon. Keep reference/ported names unchanged. Use `EDA/<planet>/<category>/` only when a category has more than two notebooks; otherwise keep notebooks directly under the planet. Store generated data, figures, manifests and execution/debug artifacts under `darrel stuff/data/`, not beside source notebooks.

### Python helper locations

| Folder (relative to `EDA/`) | Purpose |
| --- | --- |
| [shared/](shared/) | Reusable readers, provenance, terrain/site utilities, reference experiments and decision helpers. |
| [Moon/Stage3_Requirements/](Moon/Stage3_Requirements/) | Stage 3 subject/requirement analysis scripts and analysis JSON configs. |

Existing import names are preserved. Only helper/config locations and necessary search paths/file references changed; no new package structure was introduced. Notebook locations, data paths and analysis methods are unchanged. Restart open notebook kernels before using the updated paths.
