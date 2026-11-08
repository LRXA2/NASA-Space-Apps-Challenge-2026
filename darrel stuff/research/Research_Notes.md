# Stage 3 Environmental Research Report

This report covers **all 53 entries** in [environmental_data.csv](environmental_data.csv): 38 external dataset/catalog entries, 14 project-data requirements and one planetary baseline. It is not limited to locally downloaded data. The original CSV priorities and statuses are preserved.

## Required Stage 3 targets - first priority

**Controlling objective:** [outline Stage 3 - Environmental and Equipment Suitability Engine](../../outline.md#stage-3--environmental-and-equipment-suitability-engine): evaluate whether an intended mission can operate at a selected Moon or Mars site. Our current implementation/data concern the Moon; lunar evidence is not silently applied to Mars. These required inputs/processes come before optional research additions.

| Required input / analysis | Evidence needed and current work | Remaining boundary / algorithm use |
| --- | --- | --- |
| Environmental conditions at site and operating period | D01-D08/D19/D20 and relevant terrain/environment records; Dar_029 input audit, Dar_030 time/season/terrain EDA, Dar_032 native support, existing notebook 13 terrain views. | Static/phase maps are available, but no dated terrain-aware illumination/contact history generator was found in the original notebooks. Retrieve/generate dated conditions for an explicit scenario before continuity/endurance checks. |
| Mission duration and intended activities | M04/M14 project scenario; Dar_029 input contracts and Dar_031 duration/load sensitivity. | No selected mission is supplied. Reference/sensitivity axes do not define a mission or its applicability. |
| Crew requirements | M02/M10/M11/M12 and adopted crew/consumable requirements; Dar_031 S01 BVAD/S02-S03 reference applicability and crew-day scaling. | Published rates are references, not actual stocks, recovery performance or total life-support adequacy. |
| Equipment capabilities and limitations | M01/M03-M09/M13-M14 as relevant; Dar_031 battery/soil/shielding response domains and readiness. | Select the actual configuration and evidence for thermal response, power/storage, protection, communications and other applicable capacity-demand cases. Public observations cannot supply unknown hardware limits. |
| Safety requirements, margins and uncertainty | Documented applicable requirements and hard/soft classification; Dar_028 pipeline and Dar_029-031 coverage/readiness. | Estimate supported margins; identify failed/uncertain requirements and limitations. **Passed / Failed / Unknown**; missing mandatory evidence is not a pass. Apply preferences only after all mandatory conditions pass. |

[Executed findings](../EDA/EDA_Results.md#14-golden-stage-3-revamp), [notebook work plan](../EDA/EDA_Notes.md), [algorithm recommendations](../purposal.md). S01-S03 (crew/standards) and R01/R02 (battery/soil) are supplemental references, not replacements for the register's project-data requirements.

<a id="priority-eda-for-the-stage-3-algorithm"></a>

## Research priorities - original register tags

The tables below follow the CSV's **P1 - P2 - P3**, not a new impact-tier ranking or algorithm weights. Categories within a priority retain register order. Local availability/download size does not reduce the importance of missing mission/equipment evidence. Mission activities determine which requirements apply; a P2/P3 hazard is not automatically safe to ignore.

<a id="tier-1--most-direct-impact-on-mission-feasibility-and-essential-protection"></a>

### P1 - survival/protection research (34 entries)

| Category | Register entries | Stage 3 use / EDA focus | Boundary / limits |
| --- | --- | --- | --- |
| Temperature & Thermal | D01, D04, D20, D21, D28, D38, M01 | Surface/phase/local-time and depth contrasts; component thermal response and operating margins. | Surface brightness temperature, historical depth profiles and component temperature are different quantities. |
| Radiation | D07, D08, D31, M06 | Quiet/event and shielding contrasts; applicable exposure/protection margins. | Orbital detectors and published shielding cases do not establish local crew dose. |
| Illumination & Shadows | D02, D27, M07 | Terrain/shadow context; dated generation, darkness and storage requirements. | Static maps and dark-region images are not chronological power histories. |
| Terrain & Surface Properties | D05, D06, D15, D26, D33, M05 | Native-support/uncertainty checks; terrain-environment joins and tested mobility/foundation response. | Slope, radar texture and morphology do not certify soil capacity; avoid duplicate terrain penalties. |
| Seismic Activity | D13, D14, D23 | Event classes, location uncertainty and waveform spectra/duration. | Sparse historical/local records do not establish south-polar recurrence or structural qualification. |
| Resources & Sample Chemistry | D16, M09 | Spectral/material context and measured sample-release/containment response. | Remote chemistry and one impact experiment are not cabin toxicity or local resource certification. |
| Communications & Geometry | D03, D19, M08 | Visibility/dated geometry, then contact/outage and link-margin checks. | Mean Earth visibility and sphere-horizon samples are not terrain-aware working links. |
| Habitat & Human Health | M02, M10 | Protected-system atmosphere, supplies/quality, performance and mode-specific noise/vibration. | External maps and analog studies cannot replace internal telemetry or approved health requirements. |
| Mission Safety & Reliability | M04, M13, M14 | Equipment/limit inventory, recovery scenarios and landing/plume/layout response. | Mission-specific configuration, applicability and validated models/tests are required. |
| Planetary Baseline | C01 | Apply vacuum, unbreathable exterior and reduced gravity as baseline design conditions. | Not a time-varying EDA or evidence that a selected system is adequate. |

<a id="tier-2--substantial-but-more-dependent-on-the-activity-or-specific-evidence-gap"></a>

### P2 - long-term health/reliability (12 entries)

| Category | Register entries | Stage 3 use / EDA focus | Boundary / limits |
| --- | --- | --- | --- |
| Radiation | D09, D29 | Quiet/event and shielding contrasts; applicable exposure/protection margins. | Orbital detectors and published shielding cases do not establish local crew dose. |
| Illumination & Shadows | D32 | Terrain/shadow context; dated generation, darkness and storage requirements. | Static maps and dark-region images are not chronological power histories. |
| Dust | D10, M03 | Exposure/occurrence versus measured wear, filtration and cooling changes. | Orbital dust is not cabin loading or tested hardware degradation. |
| Plasma & Magnetic Environment | D11, D22, D25 | Time/geometry/regime and field contrasts; identify charging-model needs. | Plasma observations are not discharge rates or ionizing crew dose. |
| Habitat & Human Health | D17, D18, M11, M12 | Protected-system atmosphere, supplies/quality, performance and mode-specific noise/vibration. | External maps and analog studies cannot replace internal telemetry or approved health requirements. |

<a id="tier-3--indirect-context-alternatives-or-specialised-extensions"></a>

### P3 - supporting context (7 entries)

| Category | Register entries | Stage 3 use / EDA focus | Boundary / limits |
| --- | --- | --- | --- |
| Terrain & Surface Properties | D24, D30, D36, D37 | Native-support/uncertainty checks; terrain-environment joins and tested mobility/foundation response. | Slope, radar texture and morphology do not certify soil capacity; avoid duplicate terrain penalties. |
| Exosphere & Vacuum | D35 | Sparse exosphere context and relevance to contamination/operations. | Not breathable air, atmospheric wind or internal habitat pressure. |
| Plasma & Magnetic Environment | D12 | Time/geometry/regime and field contrasts; identify charging-model needs. | Plasma observations are not discharge rates or ionizing crew dose. |
| Resources & Sample Chemistry | D34 | Spectral/material context and measured sample-release/containment response. | Remote chemistry and one impact experiment are not cabin toxicity or local resource certification. |

## Register status versus local progress

CSV statuses describe the recorded source/reuse review, not a live acquisition or execution audit. Use [EDA results](../EDA/EDA_Results.md) for accepted runs and [EDA notes](../EDA/EDA_Notes.md) for remaining work. Completing an environmental download does not establish a requirement pass.

## Recommended work

1. Resolve the required Stage 3 scenario/configuration and applicable requirement gaps before optional features.
2. Reuse supported original notebook methods and their actual source datasets; [36-notebook inventory](../data/verification/source_port_review/original_notebook_dataset_inventory.csv) records dependencies and local readiness.
3. Generate dated terrain-aware conditions only for an explicitly documented observer/window and validated terrain/geometry model; retain sampling, horizon and link-model limitations.
4. Continue P1, then relevant P2/P3 questions with units, support, uncertainty and observed/modelled distinctions preserved. Do not infer equipment limits or scoring weights from correlations.

## Environmental EDA Dimensions

Keep the **environmental category** (temperature, radiation, dust, etc.) separate from the **dimensions** used to explore it. A dataset does not need to support every dimension.

| Dimension | Example question / required information |
| --- | --- |
| Time and duration | How does a quantity change by observation date, and how long do events last? Requires dated observations and sampling/gap information. |
| Location | How do quantities differ between sites? Requires coordinates or georeferenced footprints. |
| Elevation and terrain shape | Do ridges, depressions, slopes or aspects differ? Usually requires a join to an elevation model. |
| Local solar time and illumination geometry | How does a quantity vary with solar position or shadow? Use local solar time, solar angles or explicit geometry calculations to investigate rotation-related effects. |
| Depth / measurement altitude | How does temperature change below the surface, or an orbital measurement with spacecraft altitude? These are separate from terrain elevation. |
| Surface properties | How do quantities differ by mapped material, geology or rock abundance? Requires compatible surface-property maps. |
| Events and environmental regimes | What changes before, during and after an event, or between plasma regimes? Define intervals/classes and control instrument changes. |
| Spatial scale | How do patterns differ between supported footprints, patches and regions? Preserve effective resolution and aggregation scale. |
| Relationships between variables | Are temperature, illumination and terrain associated? Match locations, time support, resolution and reference frames before joining. |
| Variability and extremes | Where are spreads, observed extremes or rates of change largest? Means alone cannot reconstruct extremes or short events. |
| Coverage and uncertainty | Could gaps, observation count, quality flags or errors explain a pattern? Check these before comparing sites or times. |

Distinguish calendar date, local solar time, seasonal/solar-phase bins and event-relative time. A cumulative phase-bin average is not a dated time series. Static terrain/geology does not supply monthly environmental change. Compare orbital altitude, surface elevation and subsurface depth only as their own defined quantities.

Frame each analysis as: **How does [environmental variable] vary with [dimension], within [region/time window], accounting for [coverage and uncertainty]?**

## Dataset Fields for EDA

The register now includes `EDA Dimensions`, `Documented Fields`, `Derived Fields / Joins`, `Suggested EDA`, `Field Evidence` and `Field Review`. Dimensions describe feasible analyses, including the explicitly listed joins; they do not mean every field is directly supplied. Field descriptions are semantic summaries unless literal names are shown. Evidence links point to official documentation; review dates record documentation checks, not successful data ingestion. Blank mapping cells mean this pass has not reviewed those fields, not that the dataset lacks them.

Useful analysis directions are listed below. Refer to the EDA work plan for current local coverage rather than treating these directions as unstarted tasks:

| EDA direction | Register entries | Additional work |
| --- | --- | --- |
| Temperature by dated observation, location and local solar time | D20: Diviner RDR | Existing dated sample is not a qualified polar mission series; select/quality-filter comparable polar coverage and join terrain before site claims. |
| Polar temperature by solar phase and region | D01: Diviner PCP | Reuse Dar_001/002/017/020/025; retain phase bins, cohorts and missingness. |
| Global temperature by location and local solar time | D38: Diviner GCP | Coarse cumulative context; use D01/D20 for finer polar questions. |
| Temperature by depth | D21: ChaSTE; D28: Apollo heat flow | Calibration and sensor/deployment metadata; local historical records. |
| Illumination, Earth visibility and sky view by location | D02-D04 | Reuse Dar_002/012/017–020; dated illumination/outages still require terrain horizons plus D19 geometry. |
| Terrain, scale and uncertainty | D05-D06 | Reuse terrain analyses; join environmental data at compatible support. |
| Dust by time or altitude/local-time bin | D10: LADEE LDEX calibrated and separate derived tables | Choose the product; orbital geometry needs a separate join. |
| Plasma and magnetic field by time, position and regime | D11: ARTEMIS | Subset merged data; derive altitude/regime labels explicitly. |
| Seismic events by time, type and available location | D13: Apollo event catalog | Retain location uncertainty and detection/coverage limitations. |
| Polar UV properties by location and supported historical month | D32: LAMP | Retain exposure/error maps; absorption-feature maps are cumulative. |

Dataset availability does not establish equipment limits or operational suitability. Existing EDA completion statuses remain separate from this documentation review. Begin with a small science-data sample and its label before planning a full download.

## Contents
- **[environmental_data.csv](environmental_data.csv)** — Source register of datasets, access links, limitations and recorded statuses; local execution progress is maintained in the EDA documents.

## Using the Register
Rows are organised by `Environmental Group`, then priority and dataset ID. Each entry has one primary group; `Related Factors` retains its other applications. `Type` distinguishes observations, models, project-data requirements and baseline context.

1) Review `Existing EDA / Reuse` to avoid duplicating analysis.
2) Check data access, coverage and limitations before selecting a dataset.
3) Update `Check` and `EDA Status` as analysis progresses; unchecked entries may have partial work.

Keep additional dataset findings in the same CSV rather than creating duplicate lists.

## Public sources and remaining evidence gaps

**Source review: 6 November 2026; local R01/R02 results: 7 November.** These dates identify the evidence snapshot, not a live availability guarantee. Public reference observations, scenario outputs we must generate, and the chosen mission/equipment configuration are different evidence types. Sources alone do not establish applicability or a requirement pass; the original CSV statuses remain unchanged.

| Gap / register entry | Verified online source or generation route | What it can provide / what remains missing |
| --- | --- | --- |
| Dated illumination / M07 | [NASA PGDA lunar polar illumination](https://pgda.gsfc.nasa.gov/products/69) plus [NAIF surface-observer geometry](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/azlcpo_c.html). | PGDA explains its typically long-period average products and offers contact for site/duration-specific needs. **Proposed route:** use suitable DEM + SPICE directions to generate terrain-aware histories. This is not a verified ready-made dated CSV and does not supply our loads/storage. |
| Communications geometry / part of M08 | [NAIF surface-observer geometry](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/azlcpo_c.html). | Public geometry tools can calculate azimuth/elevation for specified observers/targets. **Proposed route:** add terrain occlusion and explicit station/relay geometry. Antenna/link requirements and service schedules remain separate inputs. |
| Battery response / reference support for M01 and power research | [NASA PCoE repository, section 5 Batteries](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/) and [NASA battery dataset field description](https://data.nasa.gov/dataset/li-ion-battery-aging-datasets). | R01 is now locally retrieved and analysed in [Dar_015 results](../EDA/EDA_Results.md#8-new-datasets--executed-reference-eda-7-november-2026). Charge/discharge/impedance experiments support method development, not lunar-vacuum qualification or the selected mission battery. |
| Soil mechanics / reference support for M05 | [Apollo 15 PDS4 soil-mechanics bundle](https://pds-geosciences.wustl.edu/missions/apollo/a15lsrp.htm), now configured as **R02** in the [consolidated downloader](../download_script/download_environmental.py). | R02 is now locally retrieved and analysed in [Dar_016 results](../EDA/EDA_Results.md#8-new-datasets--executed-reference-eda-7-november-2026). Six numeric Apollo tests retain geometry, units and source depth/collapse caveats; they are not polar-site or selected-wheel/foundation measurements. |
| Project radiation transport / part of M06 | [Geant4](https://geant4.web.cern.ch/) or [NASA OLTARIS](https://oltaris.nasa.gov/). | Geant4 is an openly available particle-transport toolkit: results must be generated and validated for specified fields/materials/geometry. OLTARIS supports radiation/shielding studies but requires registration and approval, so **KIV**. Neither is a ready-made result for our chosen design; impact vulnerability is a separate calculation. |
| Equipment configuration / M04 | The outline's [equipment-requirements section](../../outline.md#24-equipment-and-human-survival-requirements) explicitly calls for a project-created structured equipment database. | Public capability documents can be cited **after selecting the actual reference hardware and applicable conditions**. Mission dates, crew, tasks, routes, required reserves and equipment selection are configuration choices, not a universally downloadable dataset. No values are invented here. |
| M02/M09/M10/M13/M14 and remaining project-specific records | Published research may provide reference cases, but **no directly applicable project dataset was established by this source check**. | Do not interpret this as proof that no public records exist. Habitat telemetry, containment/release tests, water/air assays, plume/layout tests and rescue/reliability evidence must match the actual system/scenario. Reports describing a system are not automatically downloadable time-series data or validation of a different design. |
| D21/D22/D23/D24 | [ISRO Chandrayaan-3 archive FAQ](https://pradan.issdc.gov.in/ch3/faq.xhtml), [Chandrayaan-2 FAQ](https://pradan.issdc.gov.in/ch2/faq.xhtml). | Documented archive routes exist and the FAQ discusses authenticated sessions. Remain **KIV pending authorised access**, as requested; no alternative source is claimed to be the same calibrated science files. |

**Manual-source update:** D27's southern scene and D30's global CPR mosaic now have executed [Dar_026/027 findings](../EDA/EDA_Results.md#13-manual-shadowcam-and-mini-rf-incorporation). These extend local image/scattering context; they do not establish resource/ice availability, local impact probability or new equipment limits. The impact ordering above and historical CSV statuses are not silently rewritten.

Operational modelling/consumption is maintained in [the proposal](../purposal.md); measured local results belong in [EDA_Results.md](../EDA/EDA_Results.md).
