# Moon Research Notes

**Purpose:** identify the evidence available for our Moon environmental assessment, what it can support and what remains unresolved. Analysis methods belong in [EDA Notes](../EDA/EDA_Notes.md); algorithm choices belong in [Feature decisions](../purposal.md).

**Stage 3-4 scope:** [Dar_045-055](../EDA/EDA_Notes.md#expanded-subject-eda-and-time-windows) cover the subject studies; Dar_056 defines the source/field/outline and requirement proposal. Dated analyses use month, quarter, four-month term, half-year, year, two-year and calendar-season labels; these are not lunar seasons. Static PRP does not supply a chronology. Full/sparse/experimental scope and unresolved qualification must remain explicit. The separate [Stage 5 pipeline](../env_pipeline/README.md) uses `assumption_NASA_values`, not adopted NASA limits.

**Source-quality checks:** review native invalid constants and physical-domain validity for PRP depth, component-clock handling for NMS, and declared units for LEND before using values. Keep clock policy separate from orbital sampling and do not infer a missing unit. These are evidence-use/applicability checks, not operational limits or site failures.

**Stage 4 boundary:** subject proposals retain source/units/scope, adoption gaps and Passed/Failed/Unknown semantics. Existing H_/B_/R_ requirements supplement research references, not the active YAML test policy. Missing local response, applicable limits and capability require qualification; no mission/equipment profile or NASA safety weight is inferred. Consolidate shared evidence during adoption rather than treating proposal rows as independent risks. The standalone scorer reads only its CSV and YAML, not `environment_rule_register.json`.

**Operational source use:** retain source/page context for calibration, coupled essential services, contingency return, maintenance/duty cycle and condition-specific decisions. These are project interpretation topics, not a recovered NASA base-selection algorithm. Document index/header/hash checks separately from page review and retain extraction holds. Historical normal/moving-traverse communications provisions and flight/trainer battery capacities are not universal modern defaults.

[Source register](environmental_data.csv) | [Outline coverage](outline_environment_crosswalk.csv) | [Downloads](../download_script/Download_Dataset_Instructions.md) | [Pipeline](../env_pipeline/README.md)

## Files in this folder

| File | Purpose |
| --- | --- |
| [environmental_data.csv](environmental_data.csv) | Source register: datasets, fields, priorities and limitations. |
| [outline_environment_crosswalk.csv](outline_environment_crosswalk.csv) | Moon-relevant outline factors and evidence gaps. |
| [environment_rule_register.json](environment_rule_register.json) | Step 4 requirements, evidence guards and permitted uses. |
| [lunar_science_models.json](lunar_science_models.json) | Science sources, proxy definitions and preference-view settings. |

This is already a dedicated research folder; its file paths are kept stable. The local spreadsheet backup remains covered by [../.gitignore](../.gitignore).

## Source coverage

- **Register:** 53 entries: 38 external D-sources, 14 project M-inputs and C01 planetary baseline. It records official links, fields, joins, feasible analysis dimensions and review dates. Blank fields mean unreviewed, not absent data.
- **Core collection:** Diviner polar phase, LOLA/SDEM terrain and visibility products; Earth analog/climate collections are reference-only. Use D01-D06 lunar applicability first. New small pilots do not replace established core data.
- **Bounded Dar_029 audit:** record selected public sources, access-gated products, project-supplied inputs and baseline references separately. Check the frozen manifest rather than inferring whole-archive completeness from a bounded selection.

Availability comes from frozen manifests and receipts, not a live tracker. Register statuses are historical, not a current download audit. D21-D24 remain pending authorised archive access; no bypass or substitute science files are assumed.

## Environmental research areas

The table groups related evidence without changing the CSV's original priorities or source membership.

| Category | P tag | Register references | Research use | Important limit |
| --- | --- | --- | --- | --- |
| Temperature & Thermal | P1 | P1: D01, D04, D20, D21, D28, D38, M01 | Surface/phase/local-time and depth contrasts; thermal response and operating margins. | Brightness temperature, subsurface profiles and component temperature are not interchangeable. |
| Radiation | P1, P2 | P1: D07, D08, D31, M06; P2: D09, D29 | Quiet/event contrasts, shielding and applicable exposure margins. | Orbital counts and published shielding cases are not local crew dose. |
| Illumination & Shadows | P1, P2 | P1: D02, D27, M07; P2: D32 | Terrain/shadow and UV context; dated generation, darkness and storage needs. | Static maps and dark-region images are not chronological power or UV-dose histories. |
| Terrain & Surface Properties | P1, P3 | P1: D05, D06, D15, D26, D33, M05; P3: D24, D30, D36, D37 | Native-support/uncertainty checks, terrain joins and tested mobility/foundation response. | Slope, radar and morphology do not certify soil capacity; avoid duplicate terrain penalties. |
| Seismic Activity | P1 | P1: D13, D14, D23 | Event classes, location uncertainty, waveform spectra and duration. | Historical/local records do not establish south-polar recurrence or structural qualification. |
| Resources & Sample Chemistry | P1, P3 | P1: D16, M09; P3: D34 | Spectral/material context and measured release/containment response. | Remote chemistry or one impact experiment does not certify resources or cabin toxicity. |
| Communications & Geometry | P1 | P1: D03, D19, M08 | Visibility, dated geometry, contact/outage and link margins. | Mean visibility and sphere-horizon samples are not terrain-aware working links. |
| Habitat & Human Health | P1, P2 | P1: M02, M10; P2: D17, D18, M11, M12 | Protected atmosphere, supplies/quality, performance, noise and vibration. | External maps and analogs cannot replace internal telemetry or approved requirements. |
| Mission Safety & Reliability | P1 | P1: M04, M13, M14 | Equipment/limit inventory, recovery scenarios and landing/plume/layout response. | Requires mission-specific configuration, applicability and validated models/tests. |
| Planetary Baseline | P1 | P1: C01 | Vacuum, unbreathable exterior and reduced gravity as design conditions. | A baseline is not time-varying EDA or proof that a system is adequate. |
| Dust | P2 | P2: D10, M03 | Exposure/occurrence versus wear, filtration and cooling changes. | Orbital dust is not cabin loading or tested hardware degradation. |
| Plasma & Magnetic Environment | P2, P3 | P2: D11, D22, D25; P3: D12 | Time, geometry, regimes and field contrasts; charging-model needs. | Plasma observations are not discharge rates or ionizing crew dose. |
| Exosphere & Vacuum | P3 | P3: D35 | Sparse exosphere and contamination/operations context. | Not breathable air, atmospheric wind or internal habitat pressure. |

### How to read the priorities

| P tag | Research focus | Register entries |
| --- | --- | --- |
| <a id="tier-1--most-direct-impact-on-mission-feasibility-and-essential-protection"></a> **P1** | Survival/protection research | 34 |
| <a id="tier-2--substantial-but-more-dependent-on-the-activity-or-specific-evidence-gap"></a> **P2** | Long-term health/reliability | 12 |
| <a id="tier-3--indirect-context-alternatives-or-specialised-extensions"></a> **P3** | Supporting context | 7 |

For mixed-priority categories, the register references retain each source's own P tag.

These are **research priorities, not hard/soft gates, algorithm weights or a new impact ranking**. Core-collection selections use a separate scheme. Mission activities determine applicability: a P2/P3 hazard is not automatically safe to ignore, and missing mission/equipment evidence does not become less important because other files are easier to download.

## NASA mission and equipment evidence

### Earlier curated extraction

Screen supplied PDFs for extractable text, page images and review holds. Text screening is not full manual review; image-only handbooks/press kits require their own extraction approach. Missing priority PDFs are not assumed available.

**File identity corrections:** `AP7_Prelaunch Mission Operation Report.pdf` is Apollo **17**, not Apollo 7. The file labelled full LRV handbook transcripts contains only a 30-page segment.

The curated extraction retains source/page images, context, holds and provenance in `../data/processed/analysis/mission_equipment_extraction/20261108T205148887009Z_evidence/`:

| Extract | Scope |
| --- | --- |
| Context records | Mission/equipment identity, configuration and source-page context. |
| EVA percentage remaining | Paired predictions and recorded resource fractions; retain missing predictions and original crew/resource distinctions. |
| Primary Apollo 17 suit records | EVA/crew/resource tables with visual source-page verification. |
| LM totals | Oxygen/water balances; vehicle and suit resources remain separate. |

### Source evidence and limits

Page numbers below are PDF pages, with printed references in parentheses where available.

| Source / pages | Evidence and applicability |
| --- | --- |
| Apollo 17 prelaunch pp.16-17 (10-11) | Activity/return context, not a universal modern plan. |
| LM10 handbook pp.329/369/380 (2.5-1, 2.6-1, 2.6-16) | Configuration-specific EPS/ECS dependencies. |
| Apollo 16 report p.97 | Rover parking, covers and radiator dust maintenance. |
| Apollo 17 postflight pp.139-141 | Fender repair and temperature indication: operational response evidence. |
| Apollo 17 flight rules p.33 (2-8, item 2-27) | Seven-hour plan, 30-minute post-EVA EMU reserve and conditional five-minute communications provisions. Preserve the LCRU/antenna exception; not a universal cutoff. |
| Same, p.50 (3-15, item 3-64) | Rover 125 F for EVAs 1/2 and 140 F for EVA 3, with management/traverse responses. Temperature alone did not mandate abandoning the rover. |
| Apollo 17 postflight p.144 (9-6, Table 9-II) | Primary suit data; pp.137-138 and 144-145 support LM balances. |

**Interpretation rules:** retain lb/Ah; Ah is not Wh. Preserve printed totals, rounding and any discrepancy with displayed component sums rather than silently correcting them. Initial-minus-consumed balances do not validate a new mission. Reconstructions and primary reports are related evidence, not independent experiments. Further OCR/dense-table extraction requires explicit scope.

### Expanded PDF library and environmental impact

The external [PDF relevance index](file:///D:/projects/NASA%20Dataset/PDF_Relevance_Index.md) and [journal review](file:///D:/projects/NASA%20Dataset/Apollo_Journal_PDF_Review.md) describe the library under `keep/` and `discard/`. Check PDF identity, page coverage and extraction holds before using a source. Pointers below are one-based PDF pages, including covers; extracted text is not numerical/image verification.

| Category / source in `keep/` | Evidence topic | Impact on Steps 3-5 |
| --- | --- | --- |
| Radiation - `a08-biomed_eval.pdf`, pp.74-81 | Instrument calibration, dose quantities and postflight cross-check methodology. | Step 3: separate instruments, calibration and actual exposure intervals. Step 4: require measurement validity before an operational radiation decision. Not a polar dose map or current limit. |
| Thermal/dust - `A16_MissionReport.pdf`, pp.28-31; Apollo 17 postflight report, pp.37, 40-41 | Sensor thermal control, deployment, dust, outgassing and instrument operating conditions. | Step 3: distinguish instrument, ambient and subsurface temperatures and operational gaps. Step 4: preserve deployment, maintenance and duty-cycle dependencies. |
| Exosphere - Apollo 17 postflight report, pp.40-41 | Outgassing, background and instrument-state interpretation. | Step 3: retain contamination/background metadata when using LADEE or historical surface references; a detected signal is not automatically an uncontaminated environmental concentration. |
| Seismic - `A16_MissionReport.pdf`, pp.28-30 | Crew/rover attribution, deliberate active sources and other seismic observations. | Step 3: cross-reference waveforms with operations records before estimating natural-event rates. Apollo stations do not supply candidate-specific south-polar recurrence. |
| Terrain/illumination - `as08-analysis_photography_visual_obs.pdf`, pp.6-7, 26; `a08lunar_landmark_locations-8-10-11-12.pdf`, pp.3, 11-12; `as10-day4-pt13.pdf`, pp.3, 7-9 | Mapping/calibration methodology, lighting-dependent visibility and geolocation context. | Step 3: retain geometry, resolution and coordinate uncertainty. Qualitative orbital viewing is not a dated surface-irradiance or uninterrupted-darkness history; no slope/visibility cutoff follows. |
| Conditional decisions - `a10-mission-rules-19690415.pdf`, pp.276-278; `a17_final-flight-mission-rules_19720068065.pdf`, pp.33, 49-53, 234 | Historical confirmation requirements, configuration-specific reserves, thermal responses and operating conditions. | Step 4: preserve rule structure, provenance and applicability; do not adopt historical values as modern limits. The active test policy remains separately declared in YAML. |
| Equipment/habitat - LM handbook p.369; EVA assessment pp.47, 62, 65; LRV fragment pp.8-10; `as10-day6-pt25.pdf`, p.47 | ECS dependencies, dust/resource context and cooling-system interpretation. | Optional equipment extension only. Journal editorial diagnosis needs primary-report corroboration; Earth-orbit hardware references are not local lunar environment measurements. |

**Document use:** frame source-backed EDA questions and evidence-quality/conditional-rule proposals without automatically changing YAML limits or declaring operational safety. The PDF library is not a runtime pipeline input. Sources remain under `keep/` or `discard/`; use move logs to resolve historical root-level paths without rewriting extraction provenance.

**EDA source handoff:** [Dar_044](../EDA/Moon/Stage3_Requirements/Dar_044_acquired_environment.ipynb) defines initial environmental/PDF screening with SEE overlap checks, ESA virtual-Q/clock handling, historical HFE/PSE support, PRP model context and LAMP/LADEE/LEND quality handling. Retain each cohort definition rather than treating a selected sample as a full archive. [Methods and scope](../EDA/EDA_Notes.md#new-download-eda---dar_044). This does not automatically adopt a radiation/thermal/charging requirement.

## Supporting references and model routes

| Source | Useful for | Boundary |
| --- | --- | --- |
| S01 BVAD Rev2 (2022) | Official nominal-rate reference route. | Respect archive access requirements; nominal rates are not actual mission loads. |
| S02 NASA-STD-3001 V2 F; S03 V1 C | Acquired requirements-reference PDFs. | Applicable requirements/limits need explicit adoption. |
| R01 NASA PCoE battery aging | Laboratory cycling/impedance histories. | Protocol-specific, not lunar-vacuum or selected-hardware qualification. |
| R02 Apollo 15 soil mechanics | PDS4 six-test numeric history. | Local, geometry-dependent reference, not polar capacity. |
| DEM + DE421/MOON_ME | Dar_036 finite-terrain scenarios. | Observer configuration, terrain uncertainty, solar disk and energy/link models still needed. |
| Geant4 / OLTARIS | Possible design-specific transport modelling. | Results must be generated/validated; OLTARIS requires approved access. Not ready-made local crew dose. |

## Questions to explore in EDA

Frame each analysis as: **How does [variable] vary with [dimension], within [region/time window], accounting for [coverage and uncertainty]?** Not every dataset supports every dimension.

| Dimension | Check or question |
| --- | --- |
| Time and duration | Dated changes, event duration, sampling and gaps. |
| Location | Coordinates or georeferenced footprints for site comparisons. |
| Elevation and terrain shape | Ridge/depression, slope and aspect; join to a DEM where needed. |
| Local solar time and illumination geometry | Solar position, shadow and rotation-related effects. |
| Depth / measurement altitude | Subsurface depth and spacecraft altitude, each distinct from terrain elevation. |
| Surface properties | Compatible material, geology or rock-abundance maps. |
| Events and environmental regimes | Defined intervals/classes; control instrument changes. |
| Spatial scale | Preserve effective footprint, resolution and aggregation scale. |
| Relationships between variables | Match locations, time support, resolution and reference frames before joining. |
| Variability and extremes | Spread, observed extremes and rates of change; means cannot reconstruct short events. |
| Coverage and uncertainty | Observation counts, flags, errors and missingness before comparisons. |

Calendar date, local solar time, solar phase and event-relative time are different. Cumulative phase-bin averages are not dated time series; static terrain/geology does not supply monthly change.

### Implemented time-period evidence — Dar_043

- **D09 UV:** original downloader packages contain the historical SOLSTICE daily FUV/MUV spectra (2003–2020), not just the candidate sunlight proxy. Only complete quality=0 spectra are integrated; missing/filled spectral bins withhold the daily band value. [Publisher products](https://lasp.colorado.edu/sorce/data/) and [user guide, section 4.3](https://docserver.gesdisc.eosdis.nasa.gov/repository/Mission/SORCE/3_Product_Documentation/Product%20Requirements%20and%20Designs/SORCE_Data_User_Guide.pdf).
- **D11 plasma:** use ARTEMIS THB monthly CDF files with native Q-variable selection, fill/range attributes, position and measured timestamp spacing. SSE-x/radius bins are descriptive geometry choices, not safety thresholds or certified plasma regimes. [NASA dataset description](https://cdaweb.gsfc.nasa.gov/cgi-bin/eval2.cgi?dataset=THB_L2_MERGED&index=sp_phys); preserve the exact local CDF metadata with preparation notes.
- **D07/D08 radiation:** monthly/quarterly comparisons reuse checked daily SEC counter and platform/channel/version-separated GOES summaries. They do not convert counts/flux into dose or sparse primary samples into an event census.
- **Step 4 E14-E16:** preserve calendar/support meaning; reject simultaneous relationships between non-overlapping histories; retain Unknown local charging/protection. Calendar quarters are not [lunar seasons](https://svs.gsfc.nasa.gov/5229), and a low historical value is not a safe mission window. [Analysis methods](../EDA/EDA_Notes.md#monthly-and-quarterly-comparisons--dar_043).

## Bottom line

- The outline crosswalk groups Moon-relevant factors and their unresolved evidence boundaries.
- Existing sources support environmental comparisons and historical/reference lessons, not automatic operational approval.
- Mission/equipment inputs remain optional for the demo. Actual suitability still needs applicable configuration, requirements, limits and response evidence; missing mandatory evidence stays **Unknown**.
