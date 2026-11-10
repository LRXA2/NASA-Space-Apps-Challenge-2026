# Moon Environmental EDA

**Purpose:** understand lunar conditions and compare candidate sites using observations, modelled indicators and reference studies. This is environmental evidence, not proof that a mission can operate safely.

## Scope and coverage

- Moon-focused analysis across seven study regions and 21 exploratory candidate components. Earth experiments are supporting references only.
- Quality flags, missing dates, spatial support and observation cohorts are checked before comparison. Missing evidence stays **Unknown**, not zero risk.
- **Expanded Stage 3-4 complete within declared evidence scopes:** Dar_044 remains the initial screen; Dar_045-055 are the eleven executed subject studies and Dar_056 is the unadopted requirement synthesis. Full/sampled/experimental coverage and unresolved qualification remain explicit. Stage 5 revamp is separate. [Scope/checklist](../todo_workflow.md#comprehensive-subject-eda-and-stage-4-completed-11-november-2026).

## Expanded subject EDA and time windows - 11 November 2026

All **eleven subject notebooks (Dar_045-055)** and **Stage 4 synthesis Dar_056** are executed and saved. Each subject adds analysis beyond Dar_044, cross-checks earlier results and states its base conclusion and remaining uncertainty. Completion means the scoped EDA/proposal work is finished, **not that a mission/site is operationally qualified**.

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

**Validation:** **132 targeted tests pass cumulatively**; representative samples precede full execution. Accepted subject/synthesis outputs and saved execution are checked in [subject verification](../data/verification/latest_subject_eda.txt). A post-run PRP helper fix affects only the unused zero-quantile edge case; all **256 published p05/p50/p95/p99 intervals** were rechecked unchanged, with its executed source version retained. Failed/sampled runs are not counted as accepted full results.

The subject JSON is the frozen initial scope plan, not a live completion tracker; its original planning labels do not override completed provenance or saved execution. A final D-drive arrival check found no newer plans/dataset files or partial downloads after the work cutoff; the library still contains 95 retained PDFs. This is not an extra whole-archive checksum claim.

### Stage 4 handoff - proposed, not integrated

[Executed Dar_056](Moon/Stage3_Requirements/Dar_056_stage4_evidence_rule_synthesis.ipynb) compiles **64 proposal rows: 15 conditional hard constraints, 11 conditional soft preferences and 38 evidence guards**. It covers all eleven subjects and 27 outline factors, with 427 analysis-column and 349 native/derived-field records, eight cross-subject findings and four shared-evidence families.

- **Read the handoff:** [proposal CSV](../data/processed/analysis/stage4_environment_proposal/20261110T212854527708Z_fa4445/proposed_requirement_register.csv), [subject scope/conclusions](../data/processed/analysis/stage4_environment_proposal/20261110T212854527708Z_fa4445/subject_scope_and_conclusions.csv), [cross-subject findings](../data/processed/analysis/stage4_environment_proposal/20261110T212854527708Z_fa4445/cross_subject_findings.csv).
- Each row retains source-specific logic, evidence origin, quantity/units, applicability, reviewed existing-rule crosswalk, adoption/authority gaps and Passed/Failed/Unknown semantics. Historical source-creation TODO notes are not current unfinished-analysis claims.
- **Hard Failed/Unknown cannot be offset by preferences.** Inapplicable requirements are not selected or counted as Passed; evidence-use failure is not automatically site failure. Missing soft values are not zero-filled. Mission/equipment profiles remain optional.
- Proposal rows are not independent risk weights or 64 independent mission requirements. During later adoption, consolidate the same underlying requirement/quantity and preserve source dependencies; Sun/UV/photoemission proxies and related Apollo accounts must not be double-counted.
- Missing local demand, response, applicable capability/limit and adoption authority remain **Unknown**. Sparse primary radiation, bounded response windows, finite model horizons, short historical missions and unreadable/unreviewed PDF material remain declared limits—not invented operational evidence.
- **No numerical limit/weight is adopted.** The active register, engine, source pins, scoring and Stage 5 outputs are unchanged. A separate Stage 5 revamp/adoption and mission-specific engineering validation are future work, not unfinished Stage 3-4 deliverables.

## Radiation

- **Steps taken:** checked CRaTER instrument states, GOES quality flags, dates and separate detector/energy/platform/version groups; reviewed shielding scenarios and derived a terrain sky-openness indicator.
- **Findings:** CRaTER covers **1,091 dates / 94.1 million records** with five missing dates. GOES-16/19 cover **524/791 dates**, but only **10.48%/10.82%** of channel/time bins meet the strict filter. Primary data uses 660,000 sampled records from 33 sparse monthly files, not a complete event census.
- **Inference:** sky openness supports relative geometric comparisons. Orbital counts and the 96 published reference scenarios are **not candidate crew doses**; more shielding is not universally safer.
- **Dar_044 extension:** joined contemporaneous SEE FUV with the accepted CRaTER daily counter summaries on **1,050 valid UTC dates**. Descriptive Spearman correlation is **0.464**, not a dose relationship, causal result or site-safety rule; calibration, sampling and common time trends remain relevant.

## UV

- **Steps taken:** retained the candidate sunlight/UV-opportunity proxy; parsed downloaded SOLSTICE FUV/MUV daily spectra, accepting only complete 1-nm bands with quality=0 and finite nonnegative irradiance/uncertainty.
- **Findings:** the **2003-05-14 to 2020-02-25** solar-reference record contains **5,700 FUV / 5,760 MUV valid daily band integrals**. This is time-varying solar irradiance, not terrain-adjusted intensity or biological dose at our 21 candidates. The earlier northern LAMP pilot lacked south-polar coverage; Dar_044 reviews separate south-polar products below.
- **Inference:** lower opportunity can be a stated preference, but sunlight and UV share the same input and must not be counted twice as independent weights.
- **Dar_044 steps/results:** integrated **1,206 SEE daily spectra (June 2023-October 2026)**, retaining model-filled-bin/flare-removal and uncertainty context. Complete positive-bin screening supports **1,206 FUV days (115-180 nm), but only 139 EUV days (27-115 nm)**. Other EUV bands/dates were not substituted; unresolved zero bins are not zero exposure. SEE and historical SOLSTICE were not stitched as a calibrated single instrument.

## Plasma and charging

- **Steps taken:** retained three published charging regimes; read **36 ARTEMIS THB CDF files / 319,946 records**, masking publisher fill/out-of-range values and preserving spacecraft SSE-x/radius strata and measured cadence.
- **Findings:** observations span **2023-10-01 to 2026-09-29**. File-level median timestamp spacings range from **137.571 to 550.738 seconds**, unlike the nominal 96/384-second metadata description. Record counts therefore do not establish elapsed valid-time coverage. **Lower plasma density or more darkness is not automatically safer.**
- **Limit:** these are spacecraft plasma/field observations, not candidate surface-potential measurements. Geometry strata are not certified plasma regimes; local voltage and discharge risk remain Unknown.
- **Dar_044 steps/results:** read all **40 P2 merged files**, retaining position strata, plus **82 preselected ESA day files** (first/last available date per month, six modes separate). ESA Q fields are virtual: explicit native quality=0 screening was required. The reduced-electron mode has only **4.33% zero-quality-flag records before further screening**; 231 ambiguous/missing mode-clock records were withheld and 5,482 file-boundary context records excluded from nominal-day bins. FUV/P2 density has **1,095 paired valid dates, correlation 0.135**: weak descriptive association, not a surface-charging response.

## Temperature and heat

- **Steps taken:** compared Diviner temperature by location, local time and solar phase; checked fixed observation cohorts, terrain relationships and dated-product quality.
- **Findings:** **812 dated query products** across three regions yield **zero strict-quality rows**. Existing phase products provide five complete candidate thermal profiles, but only one passes the current context filters.
- **Inference:** cohort choice changes temperature summaries; no universal terrain correction was established. Phase averages are not instantaneous extremes or equipment temperatures. One supported candidate alone cannot establish a thermal preference winner.
- **Dar_044 steps/results:** read all **30 Apollo HFE tables / 520,977 records**, retaining flags and sensor identity; 131 undated records remain in diagnostics, not invented calendar dates. Processed all **2.88 million south-PRP model triangles** in chunks. The seven **bounding-box maxima** of modelled surface temperature are **305.95-342.08 K**; triangle-centre inclusion is not candidate-footprint validation. Annual mean at 2 cm and maximum at the surface are different quantities, not a thermal-cycle amplitude. These model/reference inputs do not qualify the rejected dated Diviner rows or supply equipment temperatures.

## Sunlight, shadow and communications

- **Steps taken:** compared solar/Earth visibility and modelled terrain horizons for seven regional reference points in two 30-day windows; varied observer height, horizon radius and sampling.
- **Findings:** geometry changes with those assumptions. Zero sampled solar blocking does not guarantee continuous sunlight; average Earth visibility does not establish a working radio link.
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
- **Findings:** the 58/59 catalog entries are related, not 117 independent events. The 222 selected crater detections do not establish local mission-window impact probabilities.
- **Dar_044 steps/results:** decoded **731 MHZ files / 415.5 million raw vertical samples** and **730 ATT timing files** across 1973-1974. About **2.04%** of each channel family's sample values use the missing code. Response metadata is available at both ends of all MHZ traces, but no response removal or event detection was performed. Clock gaps, raw-count variation and crew/active-source signals are not moonquake rates or candidate ground acceleration.

## Dust, resources and imagery

- **Steps taken:** reviewed dust/chemistry evidence coverage and environmental image/radar context.
- **Findings:** ShadowCam covers 3/21 examples and Mini-RF 19/21. Darkness, radar backscatter and spectral indicators do not prove recoverable ice, soil strength or safety. Candidate-specific dust contamination and equipment degradation remain unqualified.
- **Dar_044 dust:** processed all 36 LDEX current/mass tables, including **677,271 current records on 166 recorded dates**. Current/background remain separate; mass summaries retain quality and saturation classes rather than inventing a science-good event class or surface dust loading.
- **Dar_044 LAMP:** sampled all four southern map families at fixed stride 4, joining quality=0, positive exposure and SNR>=3. Supported fractions of the sampled south-polar domain are **46.51% long, 98.77% Lyman-alpha, 3.79% off-band and 28.82% on-band**. `ERROR` is SNR, not an error bar. White/masked pixels are not proof of darkness or zero UV; brightness/albedo are not local irradiance.
- **Dar_044 neutrons/resources:** read complete records on **74 preselected LEND dates**, first/last available date per month. SETN and CSETN2 each have all-zero supported spectra on **52 selected dates**; channel activity/background/response remain unqualified, so these zeros do not establish absence of neutrons or safe radiation. Raw spectra and PRP model ice-stability depths do not establish recoverable ice.

## Exosphere

- **Steps taken:** analysed 36 preselected NMS orbit/species files, keeping native abundance, reported uncertainty and spacecraft sampling context.
- **Findings:** **10,869 records**, covering 12 sampled dates each for Ar/He/Ne; sampled spacecraft altitudes span **1.88-145.01 km**. Species, orbit selection and historical 2013-2014 dates remain separate.
- **Limit:** this is a sparse orbital cohort, not a surface concentration, modern atmosphere or life-support assessment. Apollo outgassing/background cases reinforce the need for contamination checks.

## Equipment and past missions

- **Steps taken:** compared Apollo resource predictions with actual usage; analysed laboratory batteries, Apollo soil tests and nominal crew-load sensitivities.
- **Findings:** **16/18 Apollo 17 resource consumptions exceeded predictions**. Rounded oxygen headroom reaches zero, reinforcing the need for contingency analysis. Battery protocols and six historical soil tests are references, not qualification of our lunar equipment. Crew-rate sensitivities are not actual stocks or life-support adequacy.
- **Dar_044 PDF cases:** coded seven source/page-linked cases covering calibration, deployment/dust, outgassing and duty cycle, signal attribution, illumination, conditional decisions and equipment cooling. They guide analysis and later rule applicability; historical redlines and secondary journal diagnoses were not adopted as modern requirements.

<a id="newly-acquired-inputs-and-pdf-leads-10-november-2026"></a>
## New-download EDA ? executed Dar_044 (11 November 2026)

[Dar_044 notebook](Moon/Stage3_Requirements/Dar_044_acquired_environment.ipynb) has **three saved executed code cells, no notebook errors**, and produces **18 tables / 10 plots**. It analysed **2,986 science files across ten source families**, generating 70 series, 45,465 daily rows, 2,469 monthly rows and 874 quarterly rows. This is the declared cohort, **not every downloaded file or an event census**.

- **Full selected collections:** 1,206 SEE days; 40 P2 monthly files; 30 HFE tables; 36 LDEX tables; all 2.88 million PRP triangles.
- **Bounded collections:** 82 ESA days; 36 NMS orbit/species files; 74 LEND days, selected by calendar filenames before values were read. LAMP uses stride 4 in 20 maps with aligned support. PSE covers two years of MHZ/ATT, not all three motion axes.
- **Method:** validate receipts/hashes and labels; screen quality, fill values and clock ambiguity; preserve body, depth, units, modes, gaps and provenance; aggregate UTC months/quarters without filling missing periods. SEE daily band maxima are maxima of daily means, not subdaily flare peaks.
- **Results:** see the environmental categories above. Contemporary FUV now supports matched-date context comparisons; it does not identify a safest month or prove surface dose/charging. No repeatable lunar-season claim or forecast is made.
- **Checks:** **43 targeted tests passed**; independent raw FUV integrals, binary spectral-group decoding and monthly medians matched. All 30 registered output hashes were verified; existing pipeline source/configuration hashes are unchanged. [Execution, cohorts and verification](../data/verification/latest_new_environment_eda.txt).
- **Handoff:** these are new Step 3 outputs only. Existing Step 4-5 source pins, adopted conditions, scores and operational statuses were **not changed**. Equipment response, local exposure, physical hazard rates and applicable limits remain unresolved; missing mandatory evidence stays Unknown.

Reproduce with `.venv/Scripts/python.exe "darrel stuff/EDA/Moon/Stage3_Requirements/stage3_acquired_eda.py"` or the notebook. Use `--sample` only for bounded checks. [Source/PDF applicability](../research/Research_Notes.md#expanded-pdf-library-and-environmental-impact-10-november-2026).

## Final results and findings

- The EDA supports **relative environmental comparisons**, not an absolute safest-site claim.
- All eleven subject studies and the Stage 4 synthesis are complete within their recorded scopes. Dated inputs retain month/quarter/four-month/half-year/year/two-year/calendar-season support; static products and short historical missions are not fabricated into histories. No safe-arrival month or absolute safest-site claim follows.
- Current illustrative filters retain **14 candidates and exclude seven**. The science view finds **two non-dominated trade-off options** using radiation geometry, UV opportunity and Earth visibility; the original visibility score remains a baseline.
- Thermal comparison is withheld because only one filter-passing candidate has a complete comparable profile. Plasma is not forced into a lowest-is-safest ranking.
- Mission/equipment inputs remain optional for the demo. Operational suitability stays Unknown without applicable requirements, response evidence and limits; preference benefits cannot compensate for mandatory safety failures.

## Evidence and notebook conventions

[Source register](../research/Research_Notes.md) | [Science/model assumptions](../research/lunar_science_models.json) | [Current results](../Pipeline_Proto/outputs/LATEST_RESULTS.md)

Detailed tables, figures and provenance remain in `../data/processed/analysis/` and the accepted notebooks, especially Dar_033-056. Original notes/results/instructions are archived through `../data/verification/latest_eda_notes_cleanup.txt`.

**Notebook conventions:** name new notebooks `Dar_0xx_descriptive_name.ipynb`, using the next unused number across Earth and Moon. Keep reference/ported names unchanged. Use `EDA/<planet>/<category>/` only when a category has more than two notebooks; otherwise keep notebooks directly under the planet. Store generated data, figures, manifests and execution/debug artifacts under `darrel stuff/data/`, not beside source notebooks.

### Python helper locations

| Folder (relative to `EDA/`) | Purpose |
| --- | --- |
| [shared/](shared/) | Reusable readers, provenance, terrain/site utilities, reference experiments and decision helpers. |
| [Moon/Stage3_Requirements/](Moon/Stage3_Requirements/) | Stage 3 subject/requirement analysis scripts and analysis JSON configs. |

Existing import names are preserved. Only helper/config locations and necessary search paths/file references changed; no new package structure was introduced. Notebook locations, data paths and analysis methods are unchanged. Restart open notebook kernels before using the updated paths.
