# Stage 3 Environmental Research Report

This report summarises **all 53 entries** in [environmental_data.csv](environmental_data.csv): **38 external dataset/catalog entries, 14 project-data requirements and one planetary baseline**. It covers the whole register, not just downloaded data or the current notebooks.

## Research Focus

Our scope is [Stage 3 — Environmental and Equipment Suitability Engine](../../outline.md#stage-3--environmental-and-equipment-suitability-engine): evaluate environmental conditions against mission requirements and equipment capabilities. Its assessment feeds [Stage 4](../../outline.md#stage-4--planetary-operational-suitability-assessment). Human safety/health comes first, followed by base operations and vehicle/robot operations.

The CSV supplies the dataset descriptions, impacts, limitations and recorded EDA statuses. **The impact ordering below is a recommendation for our scope, not a ranking stated in the outline, a validated risk score or a change to the CSV's priorities.** It does not define a new AI model.

## Priority EDA for the Stage 3 algorithm

### How impact is judged

Higher-impact evidence can directly change whether a mission requirement is met, expose an essential protection/equipment gap, or materially change an operating margin. Supporting evidence helps interpret those decisions; indirect context is less able to answer them on its own.

**Local availability, download size and existing notebook coverage do not determine impact.** Missing equipment or life-support records may be more important than a complete environmental map. A lower position does not mean a hazard is safe to ignore. Mission duration, activities and equipment can change the ordering—for example, subsurface records matter more for buried systems, and plume records matter more for landing operations.

The numbered rows are an ordered review of related evidence packages, not numerical weights. Each dataset retains its own measurement/model limitations.

### Tier 1 — Most direct impact on mission feasibility and essential protection

| Order / consideration | CSV entries and evidence | Why it matters to Stage 3 / EDA focus | Boundary on conclusions |
| --- | --- | --- | --- |
| **1. Mission definition, limits and recovery** | **M04:** mission/equipment/protective-limit tables; **M14:** reliability, return/rescue and medical scenarios. | Establish what must be assessed before comparing sites. Review activities, duration, crew/equipment needs, reserves, recovery times and bottlenecks; test sensitivity to scenario assumptions. | These are required project records, not environmental maps. Missing limits cannot become invented thresholds; synthetic scenarios are not measured failure probabilities. |
| **2. Protected occupancy and essential supplies** | **M02:** habitat/suit/crewed-rover atmosphere telemetry; **M10:** water, air and surface quality-monitoring records. | Assess pressure/air-quality excursions, recovery times, treatment performance and supply/monitoring limitations for occupied systems. | External lunar measurements cannot substitute for internal-system telemetry or water-quality tests. Compare against documented applicable requirements. |
| **3. Thermal environment and hardware response** | **D01:** Diviner polar seasonal PCP; **D20:** dated Diviner RDR; **D04:** LOLA sky visibility; **M01:** component thermal/thermal-vacuum records. | Explore temperature by location, local time and phase/date; compare sky-view context and actual component response, load and cycling. This can inform thermal-control and operating-margin checks. | PCP averages are not mission extrema; RDR sampling is incomplete. Surface brightness temperature and sky-view angle are not component temperature or demonstrated cooling capacity. |
| **4. Power continuity and shadow survival** | **D02:** solar visibility/permanent shadow; **D19:** SPICE geometry; **M07:** time-resolved illumination/thermal-power outputs. | Compare lighting/shadow context, then examine dated generation/load, dark/recharge sequences and battery/thermal margins for the stated mission. | Mean visibility does not reveal longest darkness, generated power or endurance. Geometry kernels alone do not supply terrain shadows or battery behaviour. |
| **5. Radiation exposure and protection** | **D07:** CRaTER; **D08:** GOES solar-proton records; **D31:** REDMoon study outputs; **M06:** project radiation-transport/impact-vulnerability results. | Examine quality-filtered quiet/event contrasts, spectra, event durations/fluence and modeled protection sensitivity. Identify which radiation requirements can actually be evaluated. | Orbital/Earth-orbit detector data and published scenarios are not a crew surface-dose assessment. Keep radiation transport and impact-damage models distinct; do not transfer study thresholds as approved limits. |
| **6. Communications continuity** | **D03:** mean Earth visibility; **M08:** communications link/relay/outage records. | Compare geographic visibility, then actual or explicitly simulated contact states, link margins, outage durations and recovery/autonomy needs. | Seeing Earth does not establish antenna coverage, relay availability or a functioning link. Mean visibility cannot provide an outage schedule. |
| **7. Dust exposure and equipment degradation** | **D10:** LADEE LDEX dust observations; **M03:** dust-exposure/equipment-wear experiments. | Separate orbital dust occurrence from tested surface/equipment exposure. Investigate loading/duration versus wear, leakage, filtration and cooling changes. | LDEX does not measure local suit wear or cabin dust. Experimental/simulant results require stated applicability; dust impact is not determined by having an orbital dust map. |
| **8. Terrain-related operating and equipment constraints** | **D05:** SDEM terrain/support; **D06:** LOLA terrain uncertainty/effective resolution; **M05:** geotechnical/mobility/slope-stability observations. | Relate environment to terrain and source quality; examine tested loading, slope, sinkage/slip and stability responses where available. | Keep the separate terrain-assessment contribution identifiable. Elevation/slope maps do not measure soil strength, small obstacles or certify passability; avoid counting the same terrain penalty twice. |
| **9. Landing/launch effects on protective assets** | **M13:** lander-plume, layout and impact-protection test/model records. | For missions including landing/launch, compare particle/debris loads, visibility effects and asset response across stated layouts. | Requires lander/site-specific evidence. Natural impact ejecta cannot replace plume tests or validated simulations. Its importance rises with the operation included. |

**Baseline, not an EDA task — C01:** the CSV records lunar vacuum, absence of breathable exterior air and reduced gravity as planetary conditions. Apply these as background requirements for protection and equipment; do not invent atmospheric-wind or external-airflow datasets. Lack of a time-varying EDA does not make this baseline low impact.

### Tier 2 — Substantial, but more dependent on the activity or specific evidence gap

These can move into Tier 1 for a relevant mission. Their position reflects how directly the listed evidence supports our assessment, not the severity of an unmeasured hazard.

| Order / consideration | CSV entries | EDA and relevance to our scope | Main limitation |
| --- | --- | --- | --- |
| **10. Seismic and structural context** | **D13:** Apollo event catalog; **D14:** Apollo seismic waveforms; **D23:** Chandrayaan-3 ILSA vibration observations. | Examine event classes, timing/location uncertainty, waveform duration/spectra and local disturbances to inform structural-evidence gaps. Particularly relevant to long-lived bases. | Sparse historical stations and short campaigns do not supply south-polar site recurrence or certify structural resilience. Unknown transients are not automatically moonquakes. |
| **11. Visual/obstacle and surface-change evidence** | **D15:** LROC NAC imagery; **D27:** ShadowCam radiance maps; **D33:** LROC new-crater catalog. | Inspect usable coverage, lighting-dependent features, shadowed terrain and before/after detections for operations needing surface inspection. | Image visibility and search effort affect detections. Neither raw crater density nor image texture gives local impact probability, soil strength or safe travel. |
| **12. Sample-handling chemistry and containment** | **D16:** LCROSS spectra; **M09:** contained polar-sample chemistry/release tests. | Compare spectral changes and measured release/containment response under specified handling conditions. High impact when samples enter occupied systems. | One impact experiment is not a Moon-wide toxicity map or indoor-exposure measurement; direct handling tests remain necessary. |
| **13. Crew performance and occupied-system habitability** | **D17:** LSDA investigation catalog; **M11:** approved analog sleep/workload/performance records; **M12:** acoustic/vibration measurements; **D18:** ISS Kibo microbial study. | Select relevant studies, examine workload/rest/performance, mode-specific noise/vibration and contamination patterns. | Study selection/access, consent and measurement controls matter. Analog/ISS associations are not lunar health outcomes, infection probabilities or project-system certification. |
| **14. Plasma/charging context** | **D11:** ARTEMIS plasma/field data; **D22:** RAMBHA-LP current-voltage observations; **D25:** Kaguya PACE numerical products. | Explore quality, local time, geometry and plasma regimes; assess corrected/fitted probe parameters where documented. | These are not surface discharge rates, atmospheric wind or crew ionizing-radiation dose; equipment response needs additional modeling/test evidence. |
| **15. Subsurface thermal design** | **D21:** ChaSTE thermal observations; **D28:** Apollo heat-flow tables. | Examine temperature versus depth/time, gradients, disturbances and heater-on/off periods for buried-service/foundation questions. | Local campaigns and historical stations cannot be transferred directly to polar conditions; active heating must not be treated as ambient temperature. |
| **16. UV/material-exposure context** | **D09:** SORCE SOLSTICE irradiance. | Inspect supported spectral-band/time variation and uncertainty for questions about exposed optics, coatings or protection. | Irradiance at the stated reference geometry is not visor-transmitted exposure, local shadowed exposure or demonstrated material lifetime. |

### Tier 3 — Indirect context, alternatives or specialised extensions

Retain these in the report, but do not let them displace missing essential mission/equipment evidence. Elevate an entry when a specific question makes it decision-relevant.

| Order / consideration | CSV entries | Useful EDA / role | Why it is less direct for the current scope |
| --- | --- | --- | --- |
| **17. Broad thermal comparison** | **D38:** Diviner Global Cumulative Products. | Compare coarse spatial/local-time patterns and missingness. | Global cumulative means do not resolve site-specific polar extremes or continuous exposure. |
| **18. Alternative topography** | **D26:** Kaguya Terrain Camera DTM. | Compare overlapping elevation/slope and source support with SDEM/LOLA. | An alternative elevation source, not missing geotechnical or equipment-response evidence; harmonise datum and effective resolution. |
| **19. Surface-property and geological context** | **D29:** LEND neutron products; **D32:** LAMP UV maps; **D36:** Diviner rock-abundance/soil-temperature maps; **D37:** USGS geological GIS. | Compare supported spatial units, shadow/thermal context and retrieval quality. | Indirect proxies or coarse/model-derived properties do not establish crew dose, recoverable resources, individual obstacles or construction suitability. |
| **20. Mineral/resource characterisation** | **D24:** Chandrayaan-2 DFSAR; **D30:** Mini-RF; **D34:** Moon Mineralogy Mapper. | Explore calibrated radar/spectral patterns at matched support and examine geometry/processing effects. | Radar/spectral anomalies are not proof of accessible ice, safe samples, bearing strength or equipment performance. More relevant to a defined resource activity. |
| **21. Magnetic/exosphere background** | **D12:** Lunar Prospector magnetometer; **D35:** LADEE NMS exosphere observations. | Examine field or neutral-gas variation by position, altitude, time and local solar time. | Neither supplies habitat air quality, breathable atmosphere, local discharge rates or effective radiation shielding. |

## What the register currently records

These are **CSV statuses**, not a fresh audit of local files or a claim that Darrel's copied notebooks have run.

| Recorded EDA status | Entries |
| --- | ---: |
| Done — saved notebook | 2 |
| Partial — phase summaries, mean-map EDA or processing | 4 |
| Not started | 31 |
| Blocked — project data missing | 14 |
| Needs study selection / access | 1 |
| Not applicable — planetary baseline | 1 |
| **Total** | **53** |

The two recorded completed entries are the sky-visibility and SDEM studies. Partial entries cover polar temperature, solar/shadow and Earth-visibility means, and LOLA processing. All 14 project-data entries are recorded as blocked. That makes **mission/equipment evidence a major coverage gap**, even where public environmental observations exist.

A recorded completed study does not mean the associated Stage 3 requirement has passed. Nor does a public archive's existence mean its science data has been downloaded, parsed or validated here. Refer to each CSV row for source URLs, field evidence and the exact recorded status.

## Recommended work arising from the impact review

1. **Define one mission/equipment profile first.** Use the highest-impact packages to decide which requirements apply and which essential evidence is missing.
2. **Plan EDA by decision impact, independently of file availability.** Request or generate documented project/test records where appropriate; do not demote them merely because they cannot be downloaded.
3. **Reuse relevant existing analyses without narrowing the overall report to them.** The [Moon EDA work plan](../EDA/EDA_Notes.md#todo--moon-environmental-eda) records the executed studies and remaining questions. Local notebooks [05](../EDA/Moon/Terrain_And_Soil/05_lunar_terrain_environment.ipynb), [06](../EDA/Moon/Thermal/06_diviner_temperature.ipynb), [13](../EDA/Moon/Terrain_And_Soil/13_build_lunar_terrain_views.ipynb) and [25](../EDA/Moon/Environmental_Context/25_environment_native_support_eda.ipynb) support those parts, not the complete report.
4. **Keep interpretation traceable.** Preserve units, location/time or phase support, uncertainty, provenance and observed-versus-modeled distinctions. Explore coverage and missingness before associations; do not turn correlations into equipment limits.
5. **Report requirements as Passed, Failed or Unknown using sufficient evidence.** Missing applicable evidence remains Unknown. As stated in Stage 3, preference scores apply only after mandatory conditions are satisfied; EDA does not by itself establish a pass.

This is a research synthesis and proposed impact ordering based on the CSV, prepared on **6 November 2026**. It introduces no new measurements, model architecture, thresholds, algorithm weights or completion claims. Detailed dataset findings and progress remain in the register rather than being duplicated as a second acquisition checklist.

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

The 5 November 2026 field review maps 14 existing entries and adds D38 (Diviner global cumulative temperatures). Useful starting points are:

| EDA direction | Register entries | Additional work |
| --- | --- | --- |
| Temperature by dated observation, location and local solar time | D20: Diviner RDR | Select a small quality-filtered subset; join terrain for elevation/aspect. |
| Polar temperature by solar phase and region | D01: Diviner PCP | Reuse notebook 25; retain phase bins and missingness. |
| Global temperature by location and local solar time | D38: Diviner GCP | Coarse cumulative context; use D01/D20 for finer polar questions. |
| Temperature by depth | D21: ChaSTE; D28: Apollo heat flow | Calibration and sensor/deployment metadata; local historical records. |
| Illumination, Earth visibility and sky view by location | D02-D04 | Reuse notebook 25; dated illumination/outages require terrain horizons plus D19 geometry. |
| Terrain, scale and uncertainty | D05-D06 | Reuse terrain analyses; join environmental data at compatible support. |
| Dust by time or altitude/local-time bin | D10: LADEE LDEX calibrated and separate derived tables | Choose the product; orbital geometry needs a separate join. |
| Plasma and magnetic field by time, position and regime | D11: ARTEMIS | Subset merged data; derive altitude/regime labels explicitly. |
| Seismic events by time, type and available location | D13: Apollo event catalog | Retain location uncertainty and detection/coverage limitations. |
| Polar UV properties by location and supported historical month | D32: LAMP | Retain exposure/error maps; absorption-feature maps are cumulative. |

Dataset availability does not establish equipment limits or operational suitability. Existing EDA completion statuses remain separate from this documentation review. Begin with a small science-data sample and its label before planning a full download.

## Contents
- **[environmental_data.csv](environmental_data.csv)** — Main register of datasets, access links, limitations and EDA progress. Each entry explains what can be analysed by location and time.
- **Lunar_Base_Conditions_Research_Backup (1).xlsx** — Original research workbook retained for reference.

## Using the Register
Rows are organised by `Environmental Group`, then priority and dataset ID. Each entry has one primary group; `Related Factors` retains its other applications. `Type` distinguishes observations, models, project-data requirements and baseline context.

1) Review `Existing EDA / Reuse` to avoid duplicating analysis.
2) Check data access, coverage and limitations before selecting a dataset.
3) Update `Check` and `EDA Status` as analysis progresses; unchecked entries may have partial work.

Keep additional dataset findings in the same CSV rather than creating duplicate lists.

## Public sources and remaining evidence gaps

This source review was checked on **6 November 2026**, with the R01/R02 local-execution status updated on **7 November**. It is not a new online availability audit. Public reference observations, scenario outputs we must generate, and the chosen mission/equipment configuration are different evidence types. Sources alone do not establish applicability or a requirement pass; the original CSV statuses remain unchanged.

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

Operational modelling/consumption is maintained in [the proposal](../Brief_Overview.md#algorithm-proposal); measured local results belong in [EDA_Results.md](../EDA/EDA_Results.md).
