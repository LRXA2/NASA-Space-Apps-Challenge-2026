# Expanded Step 3 EDA - Moon only

**Date:** 9 November 2026 (Singapore). **Status:** expanded bounded Step 3 EDA completed, including the annual minimum and late acquisition refresh. No operational safety certification or Steps 4-6 implementation.

## 1. Outline review: sources and environmental pointers

Reviewed all of `outline.md`, not only section 2.2. The [27-factor crosswalk](outline_environment_crosswalk.csv) preserves each exact factor and outline line, applicable Moon interpretation, existing/expanded analysis and unresolved boundary. This is a one-time analytical crosswalk, not an ongoing download inventory.

| Outline pointer / source | Relevance and disposition |
| --- | --- |
| Section 2.1: [PGDA 104 SDEM](https://pgda.gsfc.nasa.gov/products/104) / its Zenodo archive | Relevant beyond CNN: local terrain, quality and shadow support. Reuse seven-region existing EDA; a 5 m grid is not 5 m independent measured support or verified soil/boulder hazard evidence. No duplicate SDEM processing. |
| Sections 2.1/2.2: [PGDA 90 LOLA](https://pgda.gsfc.nasa.gov/products/90) | Downloaded full 40 m DEM, height-error and effective-resolution rasters enable the new finite-terrain horizon experiment, including terrain outside the small ROI crops. MOON_ME/DE421, spherical height datum and source support retained. |
| Section 2.1: [PGDA 78 high-resolution LOLA](https://pgda.gsfc.nasa.gov/products/78) | Useful alternative: source height/slope uncertainty, point density and terrain clones for uncertainty propagation. Grid spacing alone is not direct measurement spacing. These alternative/cloned products were reviewed as a source option, not silently claimed as downloaded or processed here. |
| Section 2.2: [PGDA 69 illumination/Earth/sky visibility](https://pgda.gsfc.nasa.gov/products/69) | Existing static/mean-map EDA remains useful. Source explicitly distinguishes long-term averages from specific periods/heights; new Dar_036 addresses sampled local blocking, not complete power/contact adequacy. Sky-view solid angle is not a demonstrated radiator capacity. |
| Section 2.2: [Diviner](https://www.diviner.ucla.edu/data) | Existing phase and dated-channel EDA preserved. Dar_035's all-zero-quality cohort remains empty; phase bins, sparse dates and flagged brightness temperatures do not supply a qualified continuous thermal history. |
| Section 2.2: [Moon ODE](https://ode.rsl.wustl.edu/moon2/) and [LEND](https://pds-geosciences.wustl.edu/missions/lro/lend.htm) | Neutron/hydrogen and M3 mineralogy are relevant optional resource indicators. No site-matched extractability, yield, bearing strength or essential stock credit follows. No new neutron/M3 quantitative qualification is claimed; radar/ShadowCam/LCROSS do not substitute for it. |
| Section 2.2C: radiation/event/physical hazards | Expanded from three-day pilots to year-plus completed CRaTER/GOES coverage. Sparse catalog counts remain descriptive, not local quake/impact probabilities. No inferred exposure cutoff or certified SPE catalog. |
| Section 2.2E: constants/vacuum | Body-level baseline, not a spatial score. Do not invent terrestrial lunar wind, humidity or breathable atmosphere. Lunar dust still needs its own exposure/transport/response evidence. |
| Section 2.4: NASA-STD-3001 and actual equipment profiles | Reuse acquired standards and checked Apollo records. Actual mission period, activities, hardware response/capacity, stocks and applicable requirements are not supplied by an environmental download. No requirement was adopted or engine changed. |
| Stage 1 and Stage 2 pointers | Preserve CRS, height units, native/effective resolution, interpolation and spatial/time support. The present grid does not resolve individual rocks; roughness is not a boulder count. |
| Stages 3/4 and overview evaluation pointers | Missing mandatory evidence remains Unknown; preferences cannot compensate for failures/unknowns. Outputs are not survival probabilities, official certification or operational eligibility. Earth/Mars/CNN work remains excluded. |

## 2. New executed EDA

### Dar_036 - terrain-aware Sun/Earth-center blocking

[Notebook](../EDA/Moon/Stage3_Requirements/Dar_036_terrain_horizon_illumination_eda.ipynb). Uses the complete existing LOLA source rasters, not a synthetic or extrapolated terrain fill; existing SPICE kernels supply geometric Sun/Earth positions in MOON_ME with DE421.

Declared diagnostic axes: seven nearest-native-cell ROI-center points; observer heights 2/10 m; terrain search radii 10/20 km; bearings every 2 degrees and radial samples every 80 m; 30-day windows starting 1 June and 1 December 2020 at hourly cadence. Points, dates and heights are explicit exploratory choices, not intended mission facts or recommended bases. Earth and Sun are represented by their centers, without light-time correction or disk/antenna/panel modelling.

- **5,040 horizon bearings** and **80,752 target-center samples** retained. All sampled rays have complete finite-source coverage; this is not proof that unsampled terrain is irrelevant.
- Increasing search radius from 10 to 20 km raises the sampled skyline at **348/2,520 matched bearings**, by up to **4.418 degrees**. Raising the observer from 2 to 10 m lowers the sampled skyline at all matched bearings. Radius and hardware height therefore matter; a mean map alone is insufficient.
- At the Leibnitz reference point, jointly refining bearing/radial/time sampling to 1 degree/40 m/30 minutes increases sampled solar-center blocking by **2.36 percentage points** in June and **0.69 points** in December. At exact shared bearings, radial refinement raises the skyline by up to **1.141 degrees**. This does not demonstrate convergence or supply a confidence bound.
- The 2 m/20 km solar-center blocked fraction spans **0.0-98.06%** across the chosen point/windows. **Zero sampled blocking is NOT continuous sunlight or a usable-power pass**: distant terrain/solid-body horizon beyond the finite search radius, unresolved near-field obstacles and intermediate bearings can still block the target. The result is deliberately named sampled blocking, not visibility certification.
- Source height-error and effective-resolution values are retained at the controlling sampled terrain. They are not propagated as probabilistic confidence bounds and do not independently validate DEM accuracy.
- Blocked intervals retain first/last sampled timestamps and window-edge censoring. They are not measured uninterrupted darkness, solar-disk fractions, storage demand or communications availability. A working link additionally needs stations, antenna/relay geometry and a link budget.

Accepted run: `analysis/stage3_expanded_terrain/20261108T213605563555Z_8c254f`.

### Dar_037 - first year-plus GOES archive expansion

[Notebook](../EDA/Moon/Stage3_Requirements/Dar_037_expanded_space_weather_eda.ipynb). Frozen completed source-run selection: **394 consecutive daily GOES-16 files, 1 November 2023-28 November 2024**, rather than three pilot days.

- **2,950,272** recorded channel/time bins, **266,507 (9.03%)** strict-quality bins. **26 dates** contain no qualified bin under this policy; this does not mean zero radiation.
- Only **four direction/channel-days** have all 288 five-minute bins qualified; they are channel 0, both directions, on 24 March and 28 October 2024. Complete files are not complete usable exposure histories.
- Direction and energy bounds remain separate. Observed supported daily maxima are ranked only within matching direction/channel, not compared across energy bands or labelled as certified storms/worst cases.
- Flux and accepted-bin contributions retain their source units; they are not lunar surface or shielded crew dose. Instrument context: [NOAA SEISS/SGPS documentation](https://www.ncei.noaa.gov/products/goes-r-space-environment-in-situ).

Accepted run: `analysis/stage3_expanded_space_weather/20261108T213625014319Z_66adc9`.

### Dar_038 - annual CRaTER plus additionally completed GOES dates

[Notebook](../EDA/Moon/Stage3_Requirements/Dar_038_annual_radiation_context_eda.ipynb). Requested minimum is a year; two dense years are preferred only when actual completed data exists. Frozen selection contains **456 completed CRaTER dates over 1 July 2023-30 September 2024**, with missing dates retained, and **63 additional GOES-16 dates** beyond Dar_037. Isolated 2026 CRaTER/other-satellite GOES files do not constitute a second continuous year. Instrument configuration flags, physical counter validity, cadence and date gaps remain separate checks.

The representative two-endpoint CRaTER/two-file GOES sample passed before scaling. Full execution retained **39,356,608 CRaTER records**, with **39,328,269** satisfying the selected instrument-state checks; one negative/missing counter row is excluded separately. Four product days have fewer than 86,400 records; two intraday cadence gaps are recorded. Missing calendar dates are **19-20 June 2024**. Complete source products do not imply uninterrupted telemetry.

GOES after this first extension contains **457 completed dates**, including one isolated 7 April 2025 file after the main dense block. Its **67 missing calendar dates** are retained, not filled. There are **333,549/3,422,016** qualified channel/time bins. Accepted run: `analysis/stage3_annual_radiation/20261108T214216442281Z_e729e6`.

### Dar_039 - incorporate the late folder additions

[Notebook](../EDA/Moon/Stage3_Requirements/Dar_039_late_download_radiation_refresh_eda.ipynb). The required revisit found **38 new completed CRaTER dates and 38 GOES-16 dates** beyond the annual freeze. A one-day/one-file representative refresh passed, then the full delta was processed and appended without replacing prior observations.

Final frozen analysis:

| Instrument | Executed coverage | Remaining gaps / qualification |
| --- | --- | --- |
| CRaTER | **494 completed dates**, **1 July 2023-7 November 2024**; **42,639,808 SEC records**. | Two missing dates, four partial-record days and two intraday cadence gaps. Instrument-state checks accept 42,609,288 records; one invalid counter row is separately excluded. Counters are not local dose. |
| GOES-16 | **495 completed dates**: **494 consecutive dates from 1 November 2023-8 March 2025**, plus isolated 7 April 2025. | **29 missing dates** between the dense block and isolated file. **385,750/3,706,560 channel/time bins (10.41%)** meet strict quality; only four complete qualified direction/channel-days; 26 dates have no qualified bin. No zero-exposure substitution. |

The late observations also contain the largest selected-state daily median GOOD counter in this analyzed block: **4,062 on 9 October 2024**, versus **2,052** as the largest before the late extension. This is an orbital counter statistic, not a crew dose, identified solar event or local safety threshold; a typical/quiet day does not describe the observed counter range.

This meets the requested **one-year minimum with approximately 16 months of dense date coverage**. It does **not** establish two dense years, continuous qualified exposure, lunar crew dose, rare-event bounds or a complete storm census. Isolated later CRaTER/other-satellite files were not used to inflate annual coverage. Accepted run: `analysis/stage3_late_radiation_refresh/20261108T215757093675Z_372fd0`.

## 3. Acquisition refresh and validation

Initial source-run snapshot and receipt-based annual freeze are under `data/verification/stage3_expansion/`. These are point-in-time records, not claims that the downloader has finished or that every recorded job is an independent observation. Receipt-complete on-disk products can precede or exceed a running results file's snapshot; the annual extension therefore inspected the physical payloads and their receipts as well as job records. Incomplete/missing-receipt products are not consumed.

The [final external-folder revisit](../data/verification/stage3_expansion/final_external_recheck.json) was captured at **05:55:42 Singapore time on 9 November 2026** (21:55:42 UTC on 8 November). Source-run completed D07/D08 job counts advanced from **394 to 493 each**; these job counts are distinct from consumed file/day counts. The newly useful completed dates were incorporated in Dar_039. No new successful D20 job appeared: **80 downloaded, 25 no-observation and 386 error jobs** at this cutoff. Errors are not no-observation or zero temperature results. Other dataset families retained their recorded completion counts; 11 root PDFs were present. No unready payload was credited as data.

This cutoff is intentionally fixed: files arriving afterward are not automatically claimed as analyzed, and a continuously updating download does not force an endless rerun. The dated polar thermal-quality gap therefore remains unresolved at this recorded revisit.

[Final verification](../data/verification/stage3_expansion/verification.json) checks all four new notebook executions, consumed source/output hashes, **25 targeted tests**, exact preservation of prior annual rows, annual minimum/date gaps, nested-radius/height geometry relations, and all **42 prior notebooks unchanged**. All **30 retained output hashes** and **3,017 non-notebook consumed-input hash entries** passed verification (3,073 unique checked files including outputs and protected notebooks). These are software/data-handling checks, not physical engineering validation. Existing analyses/inputs remain unchanged. New tests include spherical curvature and local-angle convention, cyclic bearing lookup, censored/regular sampled intervals, radiation state versus counter validity, missing-date preservation and supported-bin-only integration. Sample checks exposed and fixed a window-endpoint grouping defect and an empty-log-plot case before scaling; no source quality was relaxed.

## 4. Remaining operational boundaries

This expansion adds source applicability, finite-terrain geometry and annual instrument context. It does not resolve every outline item: qualified mission thermal history, complete terrain/horizon/disk uncertainty, actual generation/load/storage, working communications links, local radiation transport/protection, dust/structural response, local soil/extraction capability, or actual mission/equipment/requirements remain needed. Severe applicable hazards cannot be traded away through preferences. No Steps 4-6 rule/engine work was performed.
