# Environmental EDA work plan

**Purpose:** one place for notebook scope, analysis questions and remaining work. Measured findings/runs belong in [EDA_Results.md](EDA_Results.md); algorithm integration belongs in [algorithm proposal](../Brief_Overview.md#algorithm-proposal); impact ranking and source/field definitions belong in [Research_Notes.md](../research/Research_Notes.md) and its CSV.

**Goal:** support Moon base-location comparison through temperature, illumination, Earth visibility and terrain evidence, retaining coverage and uncertainty. Local, regional and reference evidence are not interchangeable; exact CNN-patch matching is optional.

## Darrel notebook naming and current P1 implementation

New notebooks use `Dar_0xx_descriptive_name.ipynb`, numbered across Earth/Moon; legacy names stay unchanged. Categories with at least three notebooks use `EDA/<planet>/<category>/`; smaller groups remain at planet level. See the [folder guide](../Brief_Overview.md#notebook-organisation). [Naming rule](AGENTS.md). Dar_001–022 have executed on their documented scopes; **65 targeted EDA tests pass**. Completion of EDA is not completion of operational requirements or the selection engine.

| Notebook | Study | Data / scope |
| --- | --- | --- |
| [Dar_001](Moon/Thermal/Dar_001_temperature_local_time.ipynb) | Temperature/local time | D01; phase/hour coverage and fixed-cohort controls. |
| [Dar_002](Moon/Thermal/Dar_002_temperature_environment_relationships.ipynb) | Temperature/environment | D01–D06; native context joins, quality and cohort relationships. |
| [Dar_003](Earth/Climate/Dar_003_earth_climate.ipynb) | Five-site climate | Five variables, 2015–2024; coverage, seasonal and spatial summaries. |
| [Dar_004](Moon/Thermal/Dar_004_research_thermal.ipynb) | Research thermal | D20/D28/D38; RDR quality/coverage, Apollo depth and cumulative global context. |
| [Dar_005](Moon/Dar_005_research_radiation.ipynb) | Radiation | D07/D08/D31; counter/quality diagnostics and published scenario sensitivity. |
| [Dar_006](Moon/Terrain_And_Soil/Dar_006_research_terrain_support.ipynb) | Terrain support | D05/D06/D26; bounded image support, quality bands and Kaguya footprint checks. |
| [Dar_007](Moon/Dar_007_research_seismic.ipynb) | Seismic | D13/D14; catalog distinctions, clock/missingness checks and count-domain waveforms. |
| [Dar_008](Moon/Dar_008_research_imagery_change.ipynb) | Imagery/change | D15/D27/D33; image units/quality, footprint and crater-record diagnostics. |
| [Dar_009](Moon/Dar_009_research_lcross_spectra.ipynb) | LCROSS spectra | D16; calibrated pre-impact spectra, wavelength mapping and saturation. |
| [Dar_010](Moon/Environmental_Context/Dar_010_research_spice_geometry.ipynb) | Geometry benchmark | D19; kernel/frame checks and explicitly terrain-free reference geometry. |
| [Dar_011](Moon/Environmental_Context/Dar_011_research_p1_coverage_gaps.ipynb) | P1 coverage/gaps | All 34 P1 register rows; partial, gated, missing-record and baseline dispositions. |
| [Dar_012](Moon/Environmental_Context/Dar_012_joint_environmental_context.ipynb) | Joint environmental context | D01–D06; block/phase features and explicit support/missingness. |
| [Dar_013](Moon/Environmental_Context/Dar_013_feature_sensitivity_redundancy.ipynb) | Sensitivity/redundancy | Matched cohorts, quality, spatial grain and predictor dependence. |
| [Dar_014](Moon/Environmental_Context/Dar_014_rule_readiness_geometry_context.ipynb) | Geometry/readiness context | Reference sample runs, radiation sensitivity and unresolved requirement evidence. |
| [Dar_015](Earth/Dar_015_battery_reference_experiments.ipynb) | Battery reference | R01; unique cell histories, Ah/Wh integration and protocol/impedance quality. |
| [Dar_016](Moon/Terrain_And_Soil/Dar_016_apollo15_soil_reference.ipynb) | Apollo soil reference | R02; PDS4 units, probe geometry, depth correction and source limitations. |
| [Dar_017](Moon/Site_Assessment/Dar_017_lunar_base_environment_profiles.ipynb) | Regional profiles | Seven-region static distributions and matched-product temperature profiles. |
| [Dar_018](Moon/Site_Assessment/Dar_018_joint_environment_terrain_tradeoffs.ipynb) | Joint terrain/environment | Co-location sweeps, matched thermal subgroups and metric/reason exports. |
| [Dar_019](Moon/Site_Assessment/Dar_019_spatial_environment_connectivity.ipynb) | Spatial connectivity | Grid/origin/cut/adjacency controls, nominal component extent and boundary proxies. |
| [Dar_020](Moon/Site_Assessment/Dar_020_candidate_environment_profiles.ipynb) | Candidate profiles | Illustrative component-cell static/thermal profiles and point-association support. |
| [Dar_021](Moon/Site_Assessment/Dar_021_environment_preference_sensitivity.ipynb) | Preference sensitivity | Separate pools; Pareto, weights, normalization, rank stability and redundancy. |
| [Dar_022](Moon/Site_Assessment/Dar_022_environment_hard_soft_rule_influence.ipynb) | Hard/soft diagnostics | Proxy gate availability, filtering order, cohorts and unresolved readiness. |

## All research P1 — implemented EDA and remaining scope

The research P1 scope comprises **22 external datasets, 11 missing project-data requirements and one non-statistical baseline**. Dar_011 records 20 locally analysed external entries: eight bounded-EDA and 12 partial-scope cases; D21/D23 remain access-gated. This is not 20 completed mission questions. Original CSV statuses are kept separate from local execution.

R01 battery and R02 soil are additional reference experiments. Detailed findings, accepted runs, source hashes and verification are centralised in [the results report](EDA_Results.md). No implicit operational pass, safety limit or final base ranking follows from a completed notebook.

## EDA question register

The **32 related questions Q01–Q32** below extend Dar_017/018 and have corresponding comparisons/exports or explicit readiness findings. They are not independent experiments. Use the existing question → declared controls → comparison → findings format; proposed algorithm consumption is documented only in [the proposal](../Brief_Overview.md#10-how-the-eda-outputs-will-be-used-in-the-algorithm).

### Dar_019 — spatial connectivity

[Notebook](Moon/Site_Assessment/Dar_019_spatial_environment_connectivity.ipynb). Inputs: D02–D04 illumination and D06 terrain/quality rasters within the seven original D05 rectangles; source identities pinned to Dar_002. Analysis lattices: 60/120/240 m and a half-cell-shifted 60 m case. Joint cuts remain diagnostic.

| ID | Question / comparison | Evidence / output |
| --- | --- | --- |
| Q01 | What is finite versus unknown on each grid, and what native resolutions support it? | `native_source_grid_support.csv`; propagate coverage and resolution rather than assuming new measurements at the analysis spacing. |
| Q02 | Where do solar/Earth visibility and slope conditions occur together? | `connectivity_threshold_grid_sweep.csv`; joint spatial evidence, not a sum of unrelated regional advantages. |
| Q03 | How many connected zones exist, and how large is the largest projected diagnostic component? | Component catalog and sweep; potential evidence for a configured footprint requirement, not certified buildable area. |
| Q04 | Are favourable cells isolated? | Singleton counts and component sizes; a connected-zone preference must distinguish scattered samples from spatial opportunity. |
| Q05 | Does four/eight-neighbour adjacency change component counts or extent? | Grid/connectivity comparison; expose connectivity assumptions before a footprint check. |
| Q06 | Do 60/120/240 m lattices change apparent area or connectivity? | Same cuts across spacings; preserve resolution sensitivity rather than adopting the most favourable grid. |
| Q07 | Does a 30 m shift change the 60 m result? | Same-spacing origin control; quantify discretization sensitivity. |
| Q08 | Are components truncated at boundaries; what interior-distance proxies remain? | Component bounds, boundary flags and lattice diameter proxy; not a guaranteed physical minimum width or chosen base size. |

### Dar_020 — candidate environmental profiles

[Notebook](Moon/Site_Assessment/Dar_020_candidate_environment_profiles.ipynb). Uses the three largest components per region under the predeclared unshifted 60 m / four-neighbour illustration: solar ≥0.5, Earth visibility ≥0.5, slope ≤10°. This is a purposive diagnostic pool, **not an adopted policy or best-base selection**. Temperature comes from original Dar_002 paired observations on the 17 common products.

| ID | Question / comparison | Evidence / output |
| --- | --- | --- |
| Q09 | What environmental distributions describe each selected component? | `candidate_static_profiles.csv`; location-qualified inputs rather than copied regional medians. |
| Q10 | How different are median, q90 and maximum slope? | Separate summary statistics; choose the statistic required by a documented rule, not whichever passes. |
| Q11 | What shadow and sky-view context accompanies the selected light/terrain conditions? | Retained static profiles; neither field automatically becomes a positive/negative score. |
| Q12 | What zero-spot, elevation-error and effective-resolution support exists? | Quality distributions alongside metrics; evidence quality is not an extra independent physical reward. |
| Q13 | Which examples have no associated thermal centers or incomplete products? | `candidate_thermal_association_support.csv`; keep missing thermal evidence Unknown, not zero. |
| Q14 | How do phase-matched thermal distributions differ? | `candidate_common_product_thermal.csv`; evidence for later applicable thermal checks, not component temperatures. |
| Q15 | How much phase-average variation is observed at the same native center? | `associated_center_phase_spans.csv`; distinguish repeated-center variation from changing locations. Not mission extrema or a heating rate. |
| Q16 | How does complete-common selection change the thermal summary? | `candidate_thermal_summary.csv`; report both cohorts and missing groups instead of claiming a stable universal limit. |

Temperature association uses the containing diagnostic cell at a **point**; it does not establish full containment/co-registration of the 240 m thermal observation. Component area remains nominal projected lattice area.

### Dar_021 — soft-preference influence

[Notebook](Moon/Site_Assessment/Dar_021_environment_preference_sensitivity.ipynb). Keep two pools separate: original 1.2 km observed-center analysis blocks (including empty blocks) and Dar_020 connected-component examples. Use median solar/Earth fractions and slope q90. Compare a predeclared 15-point weight simplex and physical-domain/within-pool-percentile transformations. Higher solar/Earth and lower slope are **diagnostic preference assumptions**, not universal suitability laws.

| ID | Question / comparison | Evidence / output |
| --- | --- | --- |
| Q17 | Which units are nondominated across the three proxies? | `pareto_dominance.csv`; expose trade-offs before choosing weights; nondominated does not mean eligible/best. |
| Q18 | Which choices change when sunlight, Earth visibility or flatter terrain is prioritised? | Per-scenario rankings and regional representation; preference objectives must be explicit. |
| Q19 | How sensitive are ranks to diagnostic weights? | Weight-scenario scores; no weight is inferred from a correlation or selected as correct. |
| Q20 | Does normalization change ranks/top-five sets? | `normalization_comparison.csv`; show how the numerical scoring definition influences decisions. |
| Q21 | How unstable are ranks and top-five membership? | `diagnostic_rank_stability.csv`; scenario frequency is not a probability of being best. Ties remain ties. |
| Q22 | Do region composition and spatial grain alter interpretation? | Separate pool/regional summaries; do not mix block and component rankings or treat regional overlap as independent evidence. |
| Q23 | What happens at zero-weight simplex boundaries? | Declared pure-objective/omitted-weight cases; all three metric values remain required, with no silent missing-criterion renormalization. |
| Q24 | Are proxies correlated within each pool? | `preference_metric_correlations.csv`; review redundancy/double rewards, not causal weights or significance claims. |

These are **diagnostic preference scores only**. Actual mandatory readiness remains Unknown, and no operational ranking is enabled.

### Dar_022 — hard-rule influence and implementation handoff

[Notebook](Moon/Site_Assessment/Dar_022_environment_hard_soft_rule_influence.ipynb). Compare the same units under 27 declared proxy cut combinations and diagnostic preference weights (0.25, 0.25, 0.50). Thresholds apply to the explicitly named summary metrics, not whole-footprint guarantees. `DiagnosticMet`/`DiagnosticNotMet` are separate from operational Passed/Failed.

| ID | Question / comparison | Evidence / output |
| --- | --- | --- |
| Q25 | How many units meet each proxy combination? | `diagnostic_hard_gate_scenarios.csv`; threshold sensitivity and no-match handling. |
| Q26 | Which individual condition limits availability, and is joint availability smaller? | `marginal_and_joint_rule_availability.csv`; hard conjunction cannot be replaced by a weighted compensation score. |
| Q27 | Does filtering only an existing top five hide qualifying units? | `gate_before_top5_examples.csv`; compare gate-first versus late filtering on identical pools. |
| Q28 | What happens with absent metrics or known violations? | Unknown counts plus tested three-state comparison; known violations establish DiagnosticNotMet, otherwise incomplete required evidence remains Unknown. |
| Q29 | Does positive-spot/fixed-common selection change availability? | Same registered block set across cohorts; report sensitivity without adopting a quality exclusion policy. |
| Q30 | Which real requirements still lack needed inputs? | `actual_operational_requirement_readiness.csv`; power, thermal, communications, radiation and footprint requirements remain Unknown. |
| Q31 | How does the study follow the existing notebook decision flow? | `eda_to_algorithm_lineage.csv`; explicit mapping to notebooks 31–32 and Dar_017/018, not a claim of a fresh CNN-integrated run. |
| Q32 | Which methods are now reusable, and what remains proposed? | `rule_handoff_contract.json` and tested helper functions; no adopted requirements/weights, engine integration or best-base conclusion. |

## Retrievable dataset study scope

The **36 external dataset/geometry entries** below preserve the priority order of the earlier plan. Source URLs and field evidence are maintained in [environmental_data.csv](../research/environmental_data.csv), not copied into another acquisition register. Tier ordering reflects impact, not download completion. CSV-recorded status is distinct from local EDA; access-gated releases remain KIV.

Unsupplied project records, unselected LSDA studies, unverified PACE numeric access and the non-statistical planetary baseline are excluded from this retrievable-data plan, not deleted from the overall research report. Named fields require the source label/calibration and supported spatial/time context. These data do not automatically provide equipment response or mission limits.

| Tier | Dataset | Current scope / remaining question | EDA types and fields |
| --- | --- | --- | --- |
| 1 | **D01 — LRO Diviner south-polar seasonal PCP tables** | Dar_001/002/017/020 executed; cumulative phase/local-time context, not dated mission extremes. | Spatial/phase and cyclic-local-time EDA: tbol, ltim, clon/clat, validity, source product and phase IDs. |
| 1 | **D20 — LRO Diviner calibrated RDR observation records** | Local EDA: [Dar_004](Moon/Thermal/Dar_004_research_thermal.ipynb) - partial scope. Remaining: RDR quality/coverage diagnostics; polar-site/date/strict-quality comparison unresolved. | Dated observation EDA: observation time, footprint, channel thermal measurements and quality. |
| 1 | **D04 — LOLA sky-visibility raster** | Dar_002/017/020 executed; solid-angle/thermal context, not measured cooling capacity. | Spatial/relationship EDA: decoded sky-view solid angle, temperature, region and phase. |
| 1 | **D02 — LOLA mean solar visibility and permanent-shadow rasters** | Dar_002/012/018–020 executed; static solar/PSR context, not dated terrain shadows or endurance. | Raster/class and paired EDA: solar visibility, PSR class, temperature, region/phase and support. |
| 1 | **D19 — NAIF SPICE ephemeris, time and frame kernels** | Local EDA: [Dar_010](Moon/Environmental_Context/Dar_010_research_spice_geometry.ipynb) - partial scope. Remaining: Reference-sphere geometry; terrain horizons and mission profile missing. | Geometry/input-coverage checks: kernel time span, frames and Sun/Earth/Moon geometry. |
| 1 | **D07 — LRO CRaTER calibrated and derived particle/LET data** | Local EDA: [Dar_005](Moon/Dar_005_research_radiation.ipynb) - partial scope. Remaining: SEC counters available; LET/event spectra require another selected product. | Event/spectral EDA: time, detector energy/LET, housekeeping and quality. |
| 1 | **D08 — GOES SEISS/SGPS solar proton data** | Local EDA: [Dar_005](Moon/Dar_005_research_radiation.ipynb) - partial scope. Remaining: Two pilot days have no strict accepted averages; retained ERR DQFs are not silently relaxed. | Event/time-series EDA: proton flux by energy channel, timestamps and quality. |
| 1 | **D31 — REDMoon radiation shielding and mission-scenario study tables** | Local EDA: [Dar_005](Moon/Dar_005_research_radiation.ipynb) - bounded EDA. Remaining: Published scenarios; project transport/approved limits still required. | Modeled scenario/sensitivity EDA: published dose profiles, shielding and mission schedules. |
| 1 | **D03 — LOLA mean Earth-visibility rasters** | Dar_002/012/018–020 executed; static Earth visibility, not RF links or outage histories. | Spatial/joint-coverage EDA: Earth visibility versus location, thermal/solar cohorts and terrain support. |
| 1 | **D10 — LADEE LDEX calibrated dust-impact data** | CSV status: Not started. Continue: Select calibrated or derived products explicitly; compare occurrence across supported orbital/time bins. | Event/geometry EDA: detector impacts, calibrated dust parameters, time and observing geometry. |
| 1 | **D05 — South-polar SDEM terrain and quality layers** | Dar_006 bounded SDEM support; Dar_019 uses original region rectangles, not full image-supported terrain views. | Spatial/scale/support EDA: elevation, slope/roughness, image/solar-bin coverage and best-input resolution. |
| 1 | **D06 — LOLA regional terrain uncertainty and effective-resolution layers** | Dar_002/006/013/019/020 selected-map EDA; unfinished slope-error raster remains excluded. | Quality/uncertainty EDA: height/slope error, effective resolution, spot count and native terrain values. |
| 2 | **D13 — Apollo expanded seismic-event catalog** | Local EDA: [Dar_007](Moon/Dar_007_research_seismic.ipynb) - bounded EDA. Remaining: Two distinct catalogs; no polar recurrence estimate. | Event-catalog EDA: event class, time, available location and uncertainty. |
| 2 | **D14 — Apollo Passive Seismic Experiment waveforms** | Local EDA: [Dar_007](Moon/Dar_007_research_seismic.ipynb) - partial scope. Remaining: Actual MHZ plus ATT; instrument response and event windows still missing. | Waveform/spectral EDA: station/channel records, event duration, noise and response. |
| 2 | **D23 — Chandrayaan-3 ILSA surface vibration observations** | Local EDA: [Dar_011](Moon/Environmental_Context/Dar_011_research_p1_coverage_gaps.ipynb) - login required. Remaining: Authorised ILSA release, response, timing and disturbance/activity metadata needed. | Waveform/transient EDA: local acceleration, spectra, noise and activity timing. |
| 2 | **D15 — LROC NAC calibrated imagery** | Local EDA: [Dar_008](Moon/Dar_008_research_imagery_change.ipynb) - partial scope. Remaining: CDR pixel/quality EDA; calibrated map-projected site overlap unestablished. | Image/coverage EDA: calibrated brightness, footprints, geometry and quality. |
| 2 | **D27 — KPLO ShadowCam calibrated 32-bit radiance map COGs** | Local EDA: [Dar_008](Moon/Dar_008_research_imagery_change.ipynb) - partial scope. Remaining: North-polar pilot; physical unit and south-polar co-registration unresolved. | Shadow-region image EDA: calibrated radiance COGs, texture and PSR/terrain overlap. |
| 2 | **D33 — LROC new-crater shapefile and before/after image identifiers** | Local EDA: [Dar_008](Moon/Dar_008_research_imagery_change.ipynb) - partial scope. Remaining: Crater catalog EDA; image-time brackets and search-effort normalization missing. | Event/spatial EDA: crater location/diameter and before/after image IDs. |
| 2 | **D16 — LCROSS calibrated near-IR and visible spectra** | Local EDA: [Dar_009](Moon/Dar_009_research_lcross_spectra.ipynb) - partial scope. Remaining: Calibrated pre-impact spectra only; no post-impact/species fit. | Spectral/event EDA: calibrated near-IR/visible spectra, time, saturation and geometry. |
| 2 | **D18 — NASA OSDR OSD-82: microbial monitoring in ISS Kibo** | CSV status: Not started. Continue: Apply sequence-processing controls; compare supported microbial community patterns. | Compositional/community EDA: 16S sequences and sample location/time metadata. |
| 2 | **D11 — ARTEMIS P1/P2 merged plasma and magnetic-field data** | CSV status: Not started. Continue: Subset merged data; derive and document regime/geometry labels. | Regime/time/position EDA: plasma, magnetic field and spacecraft coordinates. |
| 2 | **D22 — Chandrayaan-3 RAMBHA-LP current-voltage observations** | Access: PRADAN registration/login required; not retrieved here. CSV status: Not started. Continue: Review sweep quality, calibration and fitting before interpreting density/electron temperature. | Instrument-fit/local-time EDA: current-voltage sweeps and corrected fitted parameters. |
| 2 | **D21 — Chandrayaan-3 ChaSTE surface/subsurface thermal observations** | Local EDA: [Dar_011](Moon/Environmental_Context/Dar_011_research_p1_coverage_gaps.ipynb) - login required. Remaining: Authorised ChaSTE release, calibration, depth/deployment and heater-state metadata needed. | Depth/time-profile EDA: sensor temperatures, depth/deployment and heater state. |
| 2 | **D28 — Apollo 15/17 Heat Flow Experiment concatenated calibrated tables** | Local EDA: [Dar_004](Moon/Thermal/Dar_004_research_thermal.ipynb) - bounded EDA. Remaining: Historical Apollo sensor/time/depth context, not polar seasonal response. | Historical depth/time-series EDA: calibrated sensor records, gaps and corrections. |
| 2 | **D09 — SORCE SOLSTICE solar spectral irradiance** | CSV status: Not started. Continue: Choose a documented product version; compare supported bands and dates. | Spectral/time EDA: wavelength, irradiance, date, uncertainty and quality. |
| 3 | **D38 — LRO Diviner Global Cumulative Products (GCP)** | Local EDA: [Dar_004](Moon/Thermal/Dar_004_research_thermal.ipynb) - bounded EDA. Remaining: Coarse polar cumulative context, not site-level mission extremes. | Coarse spatial/local-time EDA: mean brightness temperatures and latitude/longitude/time bins. |
| 3 | **D26 — Kaguya Terrain Camera DTM maps v2.0** | Local EDA: [Dar_006](Moon/Terrain_And_Soil/Dar_006_research_terrain_support.ipynb) - partial scope. Remaining: Equatorial tiles do not overlap the seven polar study regions. | Cross-source spatial EDA: overlapping DTM elevation/slope and support. |
| 3 | **D29 — LRO LEND reduced neutron records and derived products** | CSV status: Not started. Continue: Select documented products; join thermal/PSR context at the true footprint scale. | Neutron/position/time EDA: quality-filtered reduced or derived measurements. |
| 3 | **D32 — LRO LAMP polar gridded brightness and albedo products** | CSV status: Not started. Continue: Check coverage/noise; separate historical monthly variables from cumulative absorption maps. | Raster/supported-month EDA: UV brightness/albedo with exposure, error and quality maps. |
| 3 | **D36 — Diviner Level-3 rock-abundance and soil-temperature maps** | CSV status: Not started. Continue: Check polar coverage and fit uncertainty; compare supported terrain/imagery context. | Model-retrieval/relationship EDA: fitted rock fraction, soil temperature and fit RMS. |
| 3 | **D37 — USGS Unified Geologic Map of the Moon GIS v2** | CSV status: Not started. Continue: Join regional summaries; retain coarse map scale and uncertain boundaries. | GIS/spatial-group EDA: mapped geological units, contacts and linework. |
| 3 | **D24 — Chandrayaan-2 DFSAR L/S-band polarimetric radar products** | Access: PRADAN registration/login required; not retrieved here. CSV status: Not started. Continue: Select science modes/products; compare geometry, terrain and PSR context. | Radar/polarimetric EDA: calibrated DFSAR backscatter and documented polarimetric measures. |
| 3 | **D30 — LRO Mini-RF map-projected calibrated radar and global mosaics** | CSV status: Not started. Continue: Review numeric products and geometry; cross-check anomalies, not browse-image brightness. | Radar/mosaic EDA: calibrated Mini-RF map products and backscatter. |
| 3 | **D34 — Chandrayaan-1 Moon Mineralogy Mapper (M3) spectral data** | CSV status: Not started. Continue: Select processing level; check thermal/photometric effects before contextual joins. | Hyperspectral/coverage EDA: calibrated spectra, indices and footprints. |
| 3 | **D12 — Lunar Prospector calibrated magnetometer data** | CSV status: Not started. Continue: Handle coordinates and altitude before spatial comparisons or surface inference. | Field/position/altitude EDA: calibrated magnetic components and geometry. |
| 3 | **D35 — LADEE NMS calibrated and derived exosphere observations** | CSV status: Not started. Continue: Select documented species/products; compare supported geometry/time bins. | Species/time/altitude EDA: calibrated or derived neutral-gas abundance. |

## TODO — Moon environmental EDA

### Completed on the stated diagnostic scopes

- [x] Dar_001/002: temperature versus local time and illumination/terrain relationships.
- [x] Dar_017/018: regional profiles, matched-product/cohort comparisons and joint-condition evidence.
- [x] Dar_019/020: connected diagnostic zones and illustrative candidate profiles; nominal projected extent and center-only thermal association are not validated engineering footprints.
- [x] Dar_021/022: counterfactual preference/gate sensitivity, missing/no-match handling and filtering-order comparisons; no operational policy adopted.

### Remaining work

- [ ] Validate physical co-registration and the spatial support required by any actual footprint/layout criterion; exact CNN association is optional.
- [ ] Generate dated terrain-aware illumination/contact histories for an explicitly specified scenario before endurance or continuity checks.
- [ ] Resolve documented product-quality/calibration/coverage holds and the unfinished slope-error support where needed; preserve absent evidence.
- [ ] Obtain authorised access for gated datasets when available; do not substitute unrelated missions as equivalent observations.
- [ ] Supply applicable mission/equipment/layout requirements and justified preferences before operational screening/ranking. Implementation details and applicability rules belong in [the proposal](../Brief_Overview.md#algorithm-proposal), not another EDA plan.

## Sources and reproducibility

- Original bounded research selections are pinned in `data/manifests/eda_datasets/20261106T053410890901Z/inventory.json`; raw pilots are under `data/moon/eda_pilots/Dxx/<source-hash>/`. Notebook readers check selected paths, source URLs, sizes and download-receipt hashes. Original raw files are unchanged.
- Eight small, necessary supplements were retrieved under **`data/moon/eda_support/`**: an actual MHZ channel/label and the PSE missing-value documentation, the NSP1 wavelength mapping/label, and Apollo depth/label/bitmask documentation. Exact URLs and sizes are recorded in `data/verification/p1_research_support_inventory.json` and the reusable [support selection](../download_script/p1_research_eda_support.json). Their total is **10,001,995 bytes**; the primary pilots were not replaced. TLS certificate verification remained enabled.
- The existing environment record is [requirements.txt](../requirements.txt). Research readers additionally use `netCDF4`, `obspy`, `spiceypy` and `pyshp`; do not create another environment merely to read these notebooks.

From the repository root, if these extra packages are not installed:

```cmd
.\.venv\Scripts\python.exe -m pip install netCDF4 obspy spiceypy pyshp
```

To restore **only the eight supplements**, from `darrel stuff/download_script` (matching completed files are checked/skipped):

```cmd
..\..\.venv\Scripts\python.exe download_environmental.py --datasets D14 D16 D28 --selections p1_research_eda_support.json --download --workers 3
```

This is an explicit supplement selection, not a change to the default downloader scope. Use a trusted `REQUESTS_CA_BUNDLE` if required by the local TLS configuration; do not disable certificate checks.

**Next research work:** resolve the documented product/quality/footprint/response holds before extending the affected comparisons. Obtain authorised D21/D23 releases and the missing mission/equipment records when available. Keep those requirements Unknown rather than substituting other missions or published study limits.

## Notebook implementation references

| Notebook | Role / changes |
| --- | --- |
| [Moon 05](Moon/Terrain_And_Soil/05_lunar_terrain_environment.ipynb) | Existing terrain preparation and decoded native environmental crops. Verify the exact SDEM/LOLA/illumination inputs; preserve grids, units and masks. |
| [Moon 06](Moon/Thermal/06_diviner_temperature.ipynb) | Existing Diviner regional exports retain local time, temperature and provenance. Reuse them; change preprocessing only for a demonstrated input/export issue. |
| [Moon 13](Moon/Terrain_And_Soil/13_build_lunar_terrain_views.ipynb) | Existing separate full-context and image-supported terrain views. Reuse without pooling them as independent observations. |
| [Moon 25](Moon/Environmental_Context/25_environment_native_support_eda.ipynb) | Unchanged reference for native illumination decoding, coverage/phase analyses and containing-pixel joins. The requested new analyses now live in Dar_001/002 rather than modifying this reference notebook. |
| [Earth 03](Earth/Climate/03_earth_climate.ipynb), [26](Earth/Climate/26_earth_environment_expansion.ipynb), [27](Earth/Climate/27_five_site_environment_eda.ipynb) | Existing climate preparation and five-site EDA, relevant only to Earth training-site questions. |

The **legacy reference route** is **05 → 06 → 13 → 25**, after its required inputs are verified, when recreating the original terrain views/native-support analyses. It remains separate from the new Dar_001–011 route and is not a prerequisite for the new raw-input research notebooks. Select the correct notebook kernel; base dependencies are in [requirements-processing.txt](../../notebooks/requirements-processing.txt), with the research additions listed above. Neither route by itself completes every unresolved scientific or mission/equipment requirement.

Use completed local runs and their provenance; retain source labels, documented units and quality masks. Write generated outputs under `darrel stuff/data/`, in each notebook's isolated run directory. Missing inputs should fail clearly, not trigger fabricated data or silent substitutions.
