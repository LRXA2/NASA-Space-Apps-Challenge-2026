# Moon environmental pipeline

**Single active configuration: `config.yml` (`south_pole_environment_comparison`).** One input CSV produces separate Operations and Survival-conditions scores. The YAML controls reference ranges, flow weights and independent assessment toggles.

## One input CSV

Open and edit **[inputs/sites.csv](inputs/sites.csv)**. This is the single main pipeline input: 83 rows (**17 Artemis-region-labelled, 6 Apollo-labelled baseline scenarios, 30 synthetic and 30 dummy**) containing `id`, optional UTC window columns and the original measurement columns, including `median_visible_sky_fraction` and `median_earth_visibility_fraction`.

Most measurement cells are populated in the original 77 fixtures, including four intentional dummy blanks. The six Apollo-labelled baseline rows are populated where supported, using the measured references, conditional models and explicit test assumptions documented below, except that unsupported Apollo spacecraft-potential cells remain blank. The 77 non-Apollo fixtures use fictional eight-day requested windows spread across 2000-2026; synthetic neighbours share their EDA baseline windows; Apollo rows instead use historical landing-to-ascent UTC windows. Non-Apollo windows are test scenario dates, not the observation dates of their borrowed or randomized measurements; changing those dates does not reconstruct historical site conditions. The original seven EDA-labelled baselines and all synthetic scenarios use equally sized 1.2 km patches and the same map statistics. The ten additional EDA-labelled scenarios have assumed values, including geometry, without a measured footprint. These are controlled software fixtures, not verified NASA site assessments; static maps are not filtered to that future window. NASA labels identify a declared region, not a NASA-selected exact patch or approval of the assumed conditions.

EDA-labelled IDs reference the combined names in the [2022 announcement](https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/) and [2024 announcement](https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/). Shared names appear once. This is a dated declaration-name inventory, not a claim that all entries remain selected today or that differently named regions have disjoint geographical boundaries.

| ID | Declared region name | Announcement |
| --- | --- | --- |
| `eda_001` | Leibnitz Beta Plateau | 2022 |
| `eda_002` | Malapert Massif | 2022, 2024 |
| `eda_003` | de Gerlache-Kocher Massif | 2022 |
| `eda_004` | Haworth | 2022, 2024 |
| `eda_005` | Faustini Rim A | 2022 |
| `eda_006` | de Gerlache Rim 2 | 2022, 2024 |
| `eda_007` | Connecting Ridge Extension | 2022 |
| `eda_008` | Peak Near Shackleton | 2022 |
| `eda_009` | Connecting Ridge | 2022 |
| `eda_010` | de Gerlache Rim 1 | 2022 |
| `eda_011` | Nobile Rim 1 | 2022, 2024 |
| `eda_012` | Nobile Rim 2 | 2022, 2024 |
| `eda_013` | Amundsen Rim | 2022 |
| `eda_014` | Peak near Cabeus B | 2024 |
| `eda_015` | Mons Mouton Plateau | 2024 |
| `eda_016` | Mons Mouton | 2024 |
| `eda_017` | Slater Plain | 2024 |

Synthetic IDs `001`-`007`, `008`-`014`, `015`-`021` and `022`-`028` are respectively east, west, north and south neighbours of baselines `eda_001`-`eda_007`; `029`-`030` are northeast neighbours of the first two. Offsets are 1,200 m on each applicable projected axis. Baseline lower-left coordinates are region-rectangle centres rounded down to the 1,200 m grid, using `region_bounds_m` in `EDA/Moon/Stage3_Requirements/stage3_acquired_config.json`. Each synthetic row shares its baseline's nongeometry test assumptions. These are EDA-informed project proposals, not evidence that NASA will use them; the scorer does not verify slope, landing access or resource suitability.

Additional NASA scenarios and randomized dummy values use Python `random.Random(20261112)`. NASA scenario ranges are assumed test ranges, not source measurements. Dummy ranges are broader to exercise preference boundaries and optional gate configurations while keeping fractions in 0-1, temperature span equal to high minus low, and sunlight duration within the 192-hour window. Dummy `001`-`010` retain controlled gate/boundary/toggle cases alongside randomized fields; blanks are Sun visibility (`005`), link margin (`006`), UV (`007`) and seismic (`008`). No generated values were tuned to improve NASA scores.

### Apollo reference inputs

Apollo 11, 12, 14, 15, 16 and 17 provide historical reference cases. Their `apollo_<mission>_<site>_assumed` IDs identify scenarios combining mission records, declared models and incomplete evidence, not six fully measured environments. Apollo 13 did not land and is not included.

| Input family | Preparation rule |
| --- | --- |
| Dates and location | Use the respective mission's actual landing-to-ascent UTC window and [NASA landing coordinates](https://www.nasa.gov/wp-content/uploads/static/history/SP-4029/Apollo_18-27_LM_Lunar_Landing.htm). Keep the mission identity, site and time basis together. |
| Sun and Earth visibility | Compute each mission's geometry at its own coordinates and dates using [JPL Horizons](https://ssd-api.jpl.nasa.gov/doc/horizons.html). A flat, unobstructed horizon is an explicit model assumption, not measured terrain visibility or a functioning radio link. Do not substitute a short mission-window result for a long-period map average. |
| Thermal | The Apollo fixture uses a conditional 17-instant landing-to-ascent model, not measured Diviner phases. With solar elevation `e` and source local albedo `A`, the model is `T = [104^4 + (390^4 - 104^4) * (1-A) * max(0, sin(e))]^(1/4)` K. Use radians for `sin`, then take the minimum, maximum and difference across the cohort. The constants are model assumptions, not equipment limits. [NASA HLS environment reference](https://ntrs.nasa.gov/api/citations/20230014980/downloads/HLS-PAP-039%20HLS%20White%20Paper%20Non-Design.pdf). |
| Historical UV and upstream plasma | Use reconstructed irradiance or archived solar-wind data matched to each mission window, with their native quality and coverage limits. [LASP LISIRD](https://lasp.colorado.edu/lisird/) and [NASA OMNI](https://omniweb.gsfc.nasa.gov/) provide these reference families; they are not automatically on-site measurements. |
| On-site plasma | Prefer compatible mission data from the [Apollo SWS archives](https://pds-geosciences.wustl.edu/missions/apollo/). Match record times, reject fills/bad fits and preserve flow-angle assumptions. Where supported, estimate total ions as `n_p * (1 + alpha/proton)` and electrons as `n_p * (1 + 2 * alpha/proton)` under the declared proton/helium and charge-neutrality assumptions. These are density estimates, not voltage measurements. |
| Spacecraft potential | No compatible mission-specific spacecraft-potential statistic is established for the Apollo controls. Keep it blank rather than insert a shared modern value, lunar-surface voltage or detector bias. Missing values follow the configured pipeline mode. |
| Seismic and soil | Select the mission's station/sample evidence and retain native units, measurement definitions and support. Do not manufacture numerical differences or relabel another mission's reference as an on-site observation. |

Some fixture quantities still use shared historical/modern references or explicit estimates. These remain reference assumptions, not individual Apollo measurements. Genuine equal values can occur after independent preparation; equality alone is neither an error nor evidence of copying. Unsupported values must not be presented as measured ground truth.

[sample_input.csv](sample_input.csv) has the same input headers and scenario categories as `inputs/sites.csv`. It contains EDA-labelled, synthetic, dummy and Apollo control examples, not an independent measured-site catalogue. `start_utc` and `stop_utc` retain scenario support and enable optional window-dependent gates; neither is a basis for inferring missing environmental measurements.

## Where and how to obtain the input values

**These are offline preparation instructions, not runtime dependencies.** The current `inputs/sites.csv` is a software fixture: its four map-geometry columns for `eda_001`-`eda_007` and all synthetic patches were extracted from native LOLA products, while their other values are test assumptions. All values for `eda_008`-`eda_017` and dummy rows are assumptions/randomized test inputs, apart from the explicitly blank dummy cells. To prepare real measurements for another site/period, obtain the source products below and calculate the declared quantities before supplying the CSV. Do not treat invented fixture values as source observations. The script itself never downloads data, opens these products or follows the links.

### Labels and dates you supply yourself

- `id`: assign any unique assessment label, such as `site_001`.
- `candidate_id`: optional metadata supported by the config, not a required column in the current input. It is a label, not a coordinate lookup performed by the script. Document the actual footprint/point separately.
- `start_utc`, `stop_utc`: optionally enter the requested analysis window. Use both, with a timezone, or omit both. These fields do not filter raw observations inside this script; prepare the measurements for the intended window yourself.
- Keep the original source, product/version, coordinates, quality filters, valid-day coverage and actual observation dates in your preparation notes. A numeric CSV cell alone does not establish local applicability.

### Source and preparation guide

| Input field(s) | Where to obtain the source | How to calculate the CSV value |
| --- | --- | --- |
| `median_sun_visibility_fraction` | [NASA LOLA polar illumination maps](https://pgda.gsfc.nasa.gov/products/69), average solar-illumination products. | Apply label scaling/fill masks, select the documented candidate cells and take their median. Supply a fraction, e.g. `0.52`, not `52`. This remains a long-period map summary for the EDA/non-Apollo fixtures. The six Apollo scenario rows instead use the explicitly authorized landing-to-ascent model support described above; do not treat those supports as interchangeable. |
| `median_earth_visibility_fraction` | [NASA LOLA polar Earth-visibility maps](https://pgda.gsfc.nasa.gov/products/69), alongside the solar products. Local files: `env_algo_task/data/moon/illumination_2016/geotiff/south/earth_visibility/`. | Mask native fills before applying the paired label's scale/offset. Select the same documented footprint/support as the Sun/shadow summary and take the median Earth-disc visibility fraction, 0-1. Partial-disc visibility does not prove DSN/relay contact or a working RF link. |
| `window_continuous_sunlight_hours` | A candidate-local, time-resolved illumination calculation using a documented terrain/horizon model and [NAIF/SPICE ephemerides](https://naif.jpl.nasa.gov/naif/data.html), for the requested UTC window. This is a derived quantity, not a static-map lookup. | Under a documented visibility criterion, calculate the uninterrupted supported sunlight duration in the candidate window, in hours. Preserve cadence, gaps and boundary censoring. A sampled clear run alone does not prove continuous sunlight between samples; leave this field blank if continuity cannot be established. Do not multiply map-average visibility by window duration or substitute a regional reference. A valid supplied duration cannot exceed its requested window. |
| `window_minimum_link_margin_db` | A mission-specific, qualified RF link-budget calculation using the actual spacecraft/surface antenna, DSN or relay configuration, geometry, losses, noise, data rate and required receiver performance. It is not supplied by an Earth-visibility raster. | Evaluate available-minus-required link margin at the supported times/configurations across the requested candidate window; supply the qualified minimum in dB. Preserve outages and inadequate geometry/support; do not summarize only successful contacts to hide loss of service. Leave blank without the required engineering inputs. This field is ignored when the domain's hard gates are disabled. |
| `median_visible_sky_fraction` | The same [LOLA sky-visibility products](https://pgda.gsfc.nasa.gov/products/69). | Select the candidate's supported sky-solid-angle pixels, take the median in steradians, then divide by `4*pi`. Do not substitute a radiation dose or divide by `2*pi`. |
| `permanently_shadowed_cell_fraction` | The same [LOLA permanent-shadow products](https://pgda.gsfc.nasa.gov/products/69). | Count candidate cells classified as permanent shadow and divide by the supported candidate-cell count. Keep the grid, mask and footprint consistent. |
| `lowest_phase_median_temperature_kelvin`, `highest_phase_median_temperature_kelvin`, `phase_median_temperature_range_kelvin` | [LRO Diviner derived temperature products](https://pds-geosciences.wustl.edu/missions/lro/diviner.htm) and their labels, using the same documented phase-product cohort. | For candidate-associated points, calculate a median for each selected phase product. Only with the complete common cohort: take the lowest median, highest median and their difference. Do not replace these with raw instantaneous temperature minima/maxima. If the cohort is incomplete, leave the three values blank. A profile from a different EDA footprint/cohort does not automatically apply to the current 1.2 km patches. Non-Apollo thermal test values are assumptions. The six Apollo scenarios use the separately declared complete 17-instant mission-window model cohort, not Diviner products or a full-cycle cohort. |
| `regional_reference_sun_visibility_fraction`, `regional_reference_longest_shadow_sample_span_hours` | A regional horizon/illumination calculation using a documented lunar elevation model, Sun ephemerides and [NASA NAIF/SPICE kernels](https://naif.jpl.nasa.gov/naif/data.html). These are calculated values, not a ready-made pair of downloadable measurements. | To reproduce the earlier EDA reference, use the same region center, 2020-2021 period, 2 m height, 20 km horizon radius and hourly sampling. Clear fraction = clear samples / recorded samples. For each blocked run, measure first-to-last sampled time and keep the longest span. Preserve gaps/censoring; it is not guaranteed continuous darkness. These remain regional reference values, not candidate-local measurements. |
| `orbital_radiation_counter_median`, `orbital_radiation_counter_maximum` | [LRO CRaTER archive](https://pds-ppi.igpp.ucla.edu/data/lro-crater/), secondary science (`SEC`) tables with their labels. | For the current project's selected-state cohort, retain `BIASCMD=1`, `CALLOW=0`, `CALHIGH=0`, all six `PROCDFLAG=1`, and finite nonnegative `GOOD`/`REJECT`/`TOTAL` counters. Compute each UTC day's `GOOD` median and maximum. The first CSV value is the median of valid daily medians; the second is the maximum of valid daily maxima. This cohort is a project selection, not complete instrument qualification. Preserve counts per SEC record; no dose conversion is implied. |
| `median_solar_far_uv_irradiance_w_m2` | [TIMED SEE Level 3 daily spectra](https://lasp.colorado.edu/see/data/daily-averages/level-3/), NetCDF products and README. | Use the complete supported 115-180 nm band. Integrate the daily spectral irradiance across the band using wavelength-bin widths, then take the median of valid daily band integrals. Result: W/m2. Retain model-assisted/flare-removed/1-AU scope; this is not a local surface UV reading. |
| `median_spacecraft_ion_density_per_cm3`, `median_spacecraft_electron_density_per_cm3`, `median_spacecraft_electric_potential_volts` | [THEMIS/ARTEMIS data access](https://themis.ssl.berkeley.edu/data_products/index.php?nlist=2&ntype=2_tha-2_thb-2_thc-2_thd-2_the): select `thb` / ESA L2 (ARTEMIS P1), not an arbitrary Earth-orbit plasma product. | Use `thb_peif_density`, `thb_peef_density` and a separately declared spacecraft-potential series. The configured potential reference uses `thb_peif_sc_pot`; do not pool distinct modes. Apply native fill/valid-range, unique-clock and quality==0 selection. Keep full-ion and full-electron modes separate. Compute daily record medians, then the median of valid daily medians. Preserve native density/potential units; spacecraft potential is not surface charging voltage. |
| `historical_median_dust_detector_current_charges_per_second` | [LADEE LDEX calibrated data](https://sbnarchive.psi.edu/pds4/ldex/ladee_ldex_20240411/data_calibrated/), `current/` tables plus paired XML labels. Existing local copies are under `D:\projects\NASA Dataset\datasets\D10\` and the earlier `env_algo_task/data/moon/eda_pilots/D10/` baseline. | Read native `CURRENT`, apply clock/fill handling, retain signed background-subtracted values, take daily medians and then the median across valid days. Unit: elementary charges/s. Do not insert impact-catalog counts or mass-deposition estimates into this field. |
| `historical_median_vertical_seismic_rms_counts` | [Apollo PSE archive](https://pds-geosciences.wustl.edu/missions/apollo/apollo_pse.htm): MiniSEED or equivalent GeoCSV with metadata, selecting station S12 for the original reference, location/mode `00`, channel `MHZ`; select the relevant Apollo station and document its source interval when preparing a different control. | Reproduce the project's daily median-centred RMS count statistic: for valid samples `x`, RMS = `sqrt(mean((x - median(x))^2))`, with the same trace/gap handling. Then take the median of supported daily RMS values. This is a project-defined count statistic, not a NASA ground-motion safety limit, event rate or acceleration measurement. |
| `historical_median_orbital_helium_density_per_cm3` | [LADEE NMS archive and calibrated collections](https://pds.nasa.gov/ds-view/pds/viewBundle.jsp?identifier=urn:nasa:pds:ladee_nms&version=2.0), helium abundance tables and labels. | Use `He_ABUNDANCE`; retain valid, unambiguous clocks and supported abundance values. Calculate daily medians, then their median. Native `P/Cc` means particles per cubic centimetre; no numerical unit conversion was made by renaming the header. Preserve orbital altitude/local-solar-time and uncertainty context; do not treat it as surface atmosphere. |
| `soil_mean_grain_size_um` | `D:/projects/NASA Dataset/soils_hb.pdf` (*Handbook of Lunar Soils*, JSC 19069); [Dar_057](../EDA/Moon/Stage3_Requirements/Dar_057_lunar_soil_properties.ipynb), extracted `soil_samples.csv` field `Mz_um`. | Average accepted nonmissing values for the relevant Apollo mission and round to two decimals, in micrometres. Use mean grain size, not median; retain compatible source fractions. |
| `soil_maturity_is_feo` | Same handbook and Dar_057, field `Is_FeO`. | Average accepted mission values and round to two decimals. This is the reported Is/FeO maturity index, not FeO concentration; it cannot be calculated from FeO alone. |
| `soil_agglutinates_percent` | Same handbook and Dar_057, field `agglutinates_percent`. | Average compatible accepted mission percentages and round to two decimals; retain the source modal basis. Apollo 11/12/15 have no accepted values in this extraction: their fixture uses the shared 38.05% estimate, not mission measurements. |
| `soil_feo_wt_percent` | Same handbook and Dar_057, field `FeO`. | Average accepted mission FeO concentrations and round to two decimals, in wt% (e.g. `15.80`, not `0.158`). Do not substitute elemental Fe or another iron-oxide basis. |

For soil, Apollo controls use these mission aggregates; EDA-labelled, synthetic and dummy values are randomized test scenarios, not measured site soils. For a real candidate, use compatible site-specific evidence or leave unsupported fields blank. Editing the example does not update the default `inputs/sites.csv`.

For all daily summaries, use equal weight per valid day, not an average pooled across unequal record counts. Missing days are not zero. Do not combine different instruments, versions, species or modes under one measurement name.

The earlier regional model reference covers 2020-2021, dust/helium references cover 2013-2014, and the seismic reference covers 1973-1974. These do **not** become 2030 observations because the test CSV carries 2030 requested dates. Static product label acquisition dates are not a candidate-window chronology either. The active assumption policy uses fictional scoring mappings; it does not qualify these references as local hazard measurements. Source summaries, quality masks and aggregation steps are preparation choices; changing them requires documenting the new meaning, not silently retaining an incompatible header.

### Local data and EDA cross-checks

Paths below are relative to the repository root unless they start with `D:/`.
Use the original labels/README and quality flags along with the numeric files.

| Source family | Existing local source location | Relevant EDA cross-checks |
| --- | --- | --- |
| Sun/Earth/sky visibility and permanent shadow | `env_algo_task/data/moon/illumination_2016/`; documented region extents under `env_algo_task/data/moon/sdem/` | Dar020 candidate support, Dar021 preference sensitivity and Dar054 reference-point/time/footprint limits |
| Phase thermal | `env_algo_task/data/moon/diviner/`; additional model/reference files under `D:/projects/NASA Dataset/datasets/D20_PRP/` and `D28/` | Earlier Diviner phase/cohort analyses; Dar047 depth-specific historical thermal and Dar050 static polar model are different quantities, not replacements for missing phase profiles |
| Radiation | `D:/projects/NASA Dataset/datasets/D07/`, with earlier local support under `env_algo_task/data/moon/eda_pilots/` | Dar041, Dar043 and Dar049: instrument/cohort/time support and nonlocal dose limitations |
| Solar UV | `D:/projects/NASA Dataset/datasets/D09_SEE/` | Dar044 and Dar045: complete spectral-band support, quality and time coverage |
| Plasma / spacecraft potential | `D:/projects/NASA Dataset/datasets/D11_ESA/`; separate P2 context in `D11_P2/` | Dar044 and Dar046: full/reduced modes, clocks and native quality selection must not be pooled |
| Historical dust | `D:/projects/NASA Dataset/datasets/D10/` | Dar044 and Dar048: signed current, uncertainty and mass-threshold distinctions |
| Historical seismic | `D:/projects/NASA Dataset/datasets/D14_PSE/` | Dar044 and Dar053: S12 channel/mode, gap handling and raw-count/response distinctions |
| Historical exosphere | `D:/projects/NASA Dataset/datasets/D35/` | Dar044 and Dar051: species, uncertainty, orbital sampling and clock handling |

See [EDA notes](../EDA/EDA_Notes.md) and [research/source notes](../research/Research_Notes.md) for the accepted scopes. Cross-checking studies does not make different footprints, instruments, epochs or statistics interchangeable. Preserve original file/version, coordinates, masks, supported counts, actual dates and aggregation choices in preparation notes. The standalone scorer cannot verify that provenance from a numeric cell.

### Where do thresholds and multipliers come from?


The deployment target is **NASA's planned south-polar lunar-base operations**, not the Soviet Luna missions. Base gates on applicable mission/crew/equipment requirements; use Apollo as historical reference under its own duration and hardware assumptions. Derive project weights from the intended deployment priorities, not from Apollo success or arbitrary fitting. Planned infrastructure is not an established operating-base baseline. Do not loosen long-duration requirements simply to make Apollo controls pass.

| Configuration element | Basis |
| --- | --- |
| Hard gates | Applicable crew, equipment and mission requirements for the intended south-polar deployment; match units, duration and system assumptions. |
| Scoring thresholds | Documented operating/survival ranges, or clearly labelled project assumptions. Observed Apollo ranges are not automatically preferred or safe. |
| Weights | Deployment priorities: duration, power/storage, communications, protection and activities. The two scoring flows are Operations and Survival, not crewed/uncrewed profiles. Do not describe project percentages as NASA-approved weights. |
| Apollo references | Historical measurements and operational lessons under Apollo-specific mission windows and hardware assumptions, not universal base acceptance limits. |
| NASA south-polar base plans | Deployment objectives and relevant engineering scenarios. Distinguish plans, adopted requirements and demonstrated capabilities. |

Define the deployment scenario before choosing limits or weights. Uncrewed hardware also needs survival limits. Do not substitute orbital radiation counters for crew dose, ground temperature for component temperature, or sunlight fraction for battery endurance. Unsupported requirements remain unresolved or explicit assumptions, not certified gates. The Operations/Survival split uses the comparison-only configuration below; its weights are project assumptions, not NASA deployment approval.

Sources: [NASA Moon Base overview](https://www.nasa.gov/moon-base-frequently-asked-questions/), [NASA human-spaceflight standards](https://www.nasa.gov/ochmo/human-spaceflight-and-aviation-standards/), and [NASA uncrewed surface-operations study](https://ntrs.nasa.gov/citations/20220004927). These support the context and requirement families, not the pipeline's numerical weights.

They are **configuration decisions, not another downloadable measurement**. Use a justified applicable screening requirement for a hard threshold, documented utility reference bounds for a preference, and explicit project priorities for multipliers. An observed maximum is not automatically a safety limit. Validate sensitivity to multiplier choices; do not label project weights as NASA weights. The active numerical policy combines sourced reference scales with explicitly assumed preference directions and flow weights; unsupported mission hard gates are disabled, not replaced by assumed NASA limits. Change them in `config.yml`; do not infer them from the fixture min/max.

## Run

From the repository root:

```powershell
python "env_algo_task/env_pipeline/env_pipeline.py" --output "env_algo_task/env_pipeline/outputs/results.csv" --overwrite
```

`inputs/sites.csv` remains the single default input. `--input` selects one replacement CSV. No input values, headers, IDs or dates are changed by scoring. Every row runs through both Operations and Survival. Each flow has one weight map in `assessments.<flow>.weights`; there is no crewed/uncrewed selector or `--profile` option. Both scores remain experimental comparisons, not qualified crew/equipment survival assessments.

`--detailed` adds each assessment's measurement utilities, omitted inputs, domain contributions, gate details and configuration hash in JSON cells. `--compact` is the default. Output files are protected unless `--overwrite` is supplied. The script needs Python 3.10+ and PyYAML; it does not import the EDA or legacy files at runtime.

## Simple output

One row per input site, in one CSV:

```text
ID,
operations_thermal_score, operations_solar_illumination_score,
operations_dust_score, operations_plasma_charging_score,
operations_earth_visibility_score, operations_soil_score,
survival_radiation_score, survival_thermal_score,
survival_plasma_charging_score, survival_uv_score,
operations_status, survival_status,
operations_fail_reason, survival_fail_reason,
operations_score, survival_score
```

Domain columns follow the scorer's domain order within each assessment. Both total scores are 0-100; higher means more favourable under the stated comparison policy. There is **no combined habitability score**. Prefixes keep separate rules unambiguous if a domain is allocated to both assessments. Displayed scores use two decimals; calculation uses unrounded values.

Each status is **Pass, Fail or Unknown**:

- **Pass:** the configured comparison can be scored and any enabled, evaluated gates pass. With the default gate-free policy this means calculable comparison, **not safe deployment**.
- **Fail:** an enabled gate has a known failure. That assessment's total is blank; the other assessment is unaffected.
- **Unknown:** missing required evidence/configuration or no usable scoring data prevents the assessment. Domain diagnostics can still be shown.

The scores are environmental comparisons, not operational approval. Coverage is omitted from the simple output. Optional detailed output retains the supplied/selected score-metric count; it is not a confidence percentage. A low preference score is not an automatic gate failure, and a good Operations result cannot override a Survival gate.

## Pipeline flow (matching the code)

1. Read the one YAML, reject duplicate/unknown keys, and validate its shared input registry, flow weights and independent assessment rules.
2. Read one CSV; validate IDs, paired UTC dates, registered headers, finite numbers and configured physical data bounds. Blank is not zero.
3. Compose the two flows, Operations and Survival, independently from shared metric definitions, each flow's weights and per-assessment overrides.
4. Allocate domains using each flow's own weight map. Unallocated domains cannot contribute scores or gates to that assessment.
5. Normalize scoring measurements to 0-1 with the configured preference and optional curve. Form each domain score as a weighted mean times 100.
6. Apply each assessment's enabled gates independently. Known failure dominates Unknown; missing-data mode determines how blanks are handled.
7. Form each eligible total: `sum(domain_score * domain_weight) / sum(included_domain_weights)`.
8. Export the two scores and separate statuses/reasons in one row; coverage is available only in detailed output. There is no cross-score averaging or NASA-label/Apollo-ID exemption.

Schema 1 is supported for archived single-score configurations. `legacy_3` preserves the previous engine and policy; it is not read by the active pipeline. The active schema is 2.

## Domain allocation and weights

| Domain | Operations weight | Survival weight |
| --- | ---: | ---: |
| Solar illumination | 30% | - |
| Earth visibility | 25% | - |
| Dust reference | 15% | - |
| Soil reference | 10% | - |
| Radiation proxy | - | 40% |
| Thermal variation | 15% | 35% |
| Plasma charging | 5% | 15% |
| UV proxy | - | 10% |
| **Total** | **100%** | **100%** |

Earth visibility is the geometric view of Earth, not radio-link performance. The active YAML domain is `earth_visibility` and its output is `operations_earth_visibility_score`; the input `median_earth_visibility_fraction` is unchanged. Archived configurations can still use the old domain alias, but both names cannot be declared together.

Seismic and exosphere remain context only and contribute to neither total. Only thermal variation and plasma charging overlap. A dash means the domain is not allocated to that flow; it does not mean the measured value is zero. Each flow applies the same configured allocation to every row, without mission-dependent exclusions. Both flows process every input row; no input or hidden setting labels it crewed or uncrewed.

Operations weights emphasize solar-power opportunities and Earth visibility, with thermal, charging and experimental dust/soil-reference contributions. Survival weights emphasize radiation and thermal conditions, with charging and UV contributions. The overlapping domains currently share the same measurement-to-score mapping; their different weights change the contributions, not the measurements or claimed physical limits. These are **project priorities**, not NASA-issued percentages or demonstrated equipment/crew survival limits. Each flow totals 100, but only relative multipliers matter. Available-data mode renormalizes the weights when contributions are missing or disabled.

Edit the two independent maps in the single `config.yml`:

```yaml
assessments:
  operations:
    weights:
      solar_illumination: 30.0
      earth_visibility: 25.0
      dust: 15.0
      soil: 10.0
      thermal: 15.0
      plasma_charging: 5.0
  survival:
    weights:
      radiation: 40.0
      thermal: 35.0
      plasma_charging: 15.0
      uv: 10.0
```

Retain each flow's `domain_overrides` and `metric_overrides` when editing. Omitting a domain from a flow's weight map removes its score and gates there. Shared metric definitions live under `domains`. Thermal variation and plasma charging are allocated to both flows. To give a shared domain different scoring rules in the two flows, use `assessments.<flow>.metric_overrides` for genuinely different rules. Do not duplicate a proxy merely to increase its influence.

### Why these domains overlap or remain separate

This is a fixed project scoring allocation, not a claim that a domain has no physical effects outside its assigned flow. It applies consistently to every row and can be changed only through the YAML configuration.

| Domain | Allocation rationale |
| --- | --- |
| Thermal variation | Both: temperature variation is relevant to equipment performance during work and to environmental stress on systems. Operations gives it 15%; Survival gives it 35%. The current surface-span proxy is not a measured component temperature or an operating/survival tolerance. |
| Plasma charging | Both: electrical conditions are relevant to interference with activities and to electrical stress. Operations gives the proxy 5%; Survival gives it 15%. Spacecraft potential does not directly measure surface interference, discharge or equipment failure. |
| Solar illumination | Operations only: the available fraction describes a solar-power opportunity. The input does not establish darkness endurance or energy reserves, so it is not also scored as survival capability. |
| Earth visibility | Operations only: the fraction describes a geometric opportunity for contact. It does not establish an emergency link or system survival, so it is not duplicated in Survival. |
| Dust reference | Operations only, experimental: the current score is resemblance to an orbital instrument reference, not measured wear or critical-system damage. No additional Survival contribution is claimed. |
| Soil reference | Operations only, experimental: the existing Apollo-reference comparison is retained as agreed. It is not a bearing-strength or structural-failure measurement, so it does not contribute to Survival. |
| Radiation proxy | Survival only: this project assigns the relative exposure proxy to environmental protection conditions. There is no separate activity-disruption metric to justify a second Operations contribution. Counts are not dose or demonstrated protection. |
| UV proxy | Survival only: this project assigns the relative UV proxy to exposure/protection conditions. There is no separate task-performance metric for an Operations contribution; the input is not a surface dose or material-damage limit. |
| Seismic and exosphere | Context only: the retained raw seismic counts and orbital helium density do not currently provide a supported operational-performance or survival scoring relationship. |

The two totals remain independent. Shared thermal/charging values are not averaged back into a combined total, and a good Operations result cannot compensate for an enabled Survival gate failure. These allocations and weights are project assumptions, not NASA-issued priorities.

## Reference ranges and input roles

Numbers below are **scoring scales or data-validity bounds**, not certified mission operating/survival limits. Reference scales use actual source EDA, never the sample CSV distribution. Source paths, series, counts and SHA256 pins for the orbital references are recorded as comments in `config.yml`; the numbers are frozen at runtime.

| Input field(s) | Operations use | Survival use | Numeric basis / interpretation |
| --- | --- | --- | --- |
| `median_sun_visibility_fraction` | Higher preference | Not included | 0-1 maps to 0-100; the direction favours solar-power opportunity, not actual generated energy. |
| `median_earth_visibility_fraction` | Higher preference | Not included | 0-1 maps to 0-100; geometry is not an RF link or relay assessment. |
| `historical_median_dust_detector_current_charges_per_second` | Continuous reference resemblance | Not included | 100 only at the observed median, 38,230 elementary charges/s. Declines linearly to zero at p05=14,332.5 and p95=100,711.25; values beyond these anchors remain zero. Dar_048 LDEX_CURRENT daily reference. These anchors describe reference distance, not harmful-current limits. Signed current is not local deposition, abrasion or maintenance demand; preferring resemblance to the median is an experimental project assumption. |
| `soil_mean_grain_size_um` | Reference-band resemblance | Not included | 100 at 53.01-91.5975 um; zero at 14.4225 and 130.185. |
| `soil_maturity_is_feo` | Reference-band resemblance | Not included | 100 at 42.6225-72.47 Is/FeO; zero at 12.775 and 102.3175. |
| `soil_agglutinates_percent` | Reference-band resemblance | Not included | 100 at 35.351-40.058%; zero at 30.644 and 44.765%. Preserve source modal basis. |
| `soil_feo_wt_percent` | Reference-band resemblance | Not included | 100 at 6.4375-15.71 wt%; zero at -2.835 and 24.9825. Negative scoring anchors are extrapolated coordinates, not valid chemical measurements; input must be 0-100 wt%. |
| `orbital_radiation_counter_median` | Not included | Lower proxy preference | 24-104.5 counts/SEC maps to 100-0. Dar_049 selected-state CRaTER daily medians p05/p95. Not crew dose or electronics radiation tolerance. |
| `phase_median_temperature_range_kelvin` | Lower variation preference | Lower variation preference | 0-300 K span maps to 100-0. Retained project comparison scale, not a fitted hardware limit. NASA/Diviner's roughly 400 K equatorial day versus below 100 K night illustrates the contrast; it does not define a south-polar safe interval. |
| `median_spacecraft_electric_potential_volts` | Zero-centred proxy preference | Zero-centred proxy preference | 100 at 0 V; declines linearly to zero at +/-32.918969440460 V. Scale is Dar_046 p95(abs(daily median)), selected ESA_v01_thb_peif_sc_pot series. Choosing zero as preferred is a project assumption, not an arcing threshold or surface-voltage inference. |
| `median_solar_far_uv_irradiance_w_m2` | Not included | Lower proxy preference | 0.021529459636-0.026638514010 W/m2 maps to 100-0. Dar_045 SEE_v012_FUV_115_180 daily band integrals p05/p95. Not surface dose or a material/crew exposure limit. |
| `lowest_phase_median_temperature_kelvin`, `highest_phase_median_temperature_kelvin` | Context | Context | Nonnegative K. No universal 40/390 K gate: surface temperature is not component temperature. |
| `orbital_radiation_counter_maximum` | Context | Context | Nonnegative native counts. No universal 7,500-count gate. |
| `median_spacecraft_ion_density_per_cm3`, `median_spacecraft_electron_density_per_cm3` | Context | Context | Nonnegative native density; no universal preferred/safe density interval. |
| `median_visible_sky_fraction`, `permanently_shadowed_cell_fraction`, `regional_reference_sun_visibility_fraction` | Context | Context | Fractions 0-1. Sky openness is not radiation dose; shadow fraction is not energy autonomy. |
| `regional_reference_longest_shadow_sample_span_hours`, `window_continuous_sunlight_hours` | Context | Context | Nonnegative hours. Regional sampled shadow and mission-window sunlight are different quantities; neither is a battery requirement. No universal 156-hour sunlight gate. |
| `window_minimum_link_margin_db` | Context unless an applicable gate is configured | Context | Signed dB. Zero is the zero-margin boundary by definition, not a universal required engineering reserve. No default gate. |
| `historical_median_vertical_seismic_rms_counts` | Context only | Context only | Nonnegative native counts, not response-qualified candidate-site structural demand. |
| `historical_median_orbital_helium_density_per_cm3` | Context only | Context only | Nonnegative native density; no demonstrated habitability or survival threshold. |

Dust has no flat 100-point interval. A zero dust score means outside the selected central reference interval, not a failed physical safety requirement; negative background-subtracted values must not be reinterpreted as negative dust burden. Equal inputs legitimately receive equal scores; this curve does not measure operational damage.

All four soil metrics have multiplier 1; a complete soil score is their arithmetic mean. Their preferred bands are p05/p95 of rounded Apollo mission means from Dar_057. Scores fall to zero one band-width outside, with physical percentage validation retained. This is reference resemblance, not mechanical stability. Apollo mission means are historical-reference controls; missing Apollo 11/12/15 agglutinates retain the declared cross-mission estimate. Randomized EDA/synthetic/dummy inputs remain scenarios, not observations. Differences in mission window, method, epoch and support prevent interpreting these totals as like-for-like deployment certification.

## Evidence supporting the configuration

| Reference | Project use |
| --- | --- |
| [NASA LOLA illumination and Earth-visibility products](https://pgda.gsfc.nasa.gov/products/69) | Geometry definitions and map preparation; visibility is not generated power or radio-link performance. |
| [NASA Lunar Surface Data Book](https://ntrs.nasa.gov/api/citations/20230007818/downloads/ACD-50044%20Lunar%20Surface%20Data%20Book%20Rev%20A.pdf) | Lunar-environment and deployment context; scenario examples are not universal system limits. |
| [NASA NESC lunar environment study](https://ntrs.nasa.gov/api/citations/20220017053/downloads/20220017053.pdf) | Environmental interpretation; surface conditions are not component operating/survival tolerances. |
| [NASA/PDS LDEX documentation](https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/LADEE/ldex.html) | Instrument quantity, units and applicability of the dust reference. |
| [NASA cis-lunar charging study](https://ntrs.nasa.gov/api/citations/20200001582/downloads/20200001582.pdf) | Distinguish spacecraft potential from lunar-surface charging. |
| [NASA human-spaceflight standards](https://www.nasa.gov/ochmo/human-spaceflight-and-aviation-standards/) | Applicable requirement families; raw instrument counters cannot be treated as crew dose. |

Reference scales and project weights do not constitute NASA safety certification. Compatible requirements must be established before enabling operational hard gates.

## Pipeline mode and independent assessment toggles

- `pipeline_mode: available_data`: omit blank scoring measurements and renormalize remaining metric/domain weights. Supplied measurements still face any enabled applicable gate. A missing gate measurement is skipped under the inherited available-data policy, not a physical pass.
- `pipeline_mode: strict`: require all selected score metrics; a missing one withholds only its assessment's total. Missing enabled gate evidence remains Unknown. A complete gate-free comparison can still be scored.
- `domains.<domain>.enabled: false`: disable the domain by default in both assessments. An explicit per-assessment `domain_overrides.<domain>.enabled` can override that shared default for its assessment; enabled inputs still undergo physical validation.
- `include_in_score: false`: omit its contribution, without automatically disabling its gates. `hard_gates_enabled: false`: disable gates without disabling scores. Each flow's weights control allocation, not source measurements.
- All unsupported hard gates are **off by default**, with no hidden fallback gates. Pass therefore refers to comparison-policy evaluation, not readiness for crew or hardware survival.

For a genuinely applicable Operations link-margin check, the supported structure is:

```yaml
assessments:
  operations:
    domain_overrides:
      earth_visibility:
        hard_gates_enabled: true
    metric_overrides:
      window_minimum_link_margin_db:
        role: gate
        hard_gate:
          operator: above_threshold
          threshold: 0.0
          rationale: Adopt only if this zero-margin criterion applies to the declared link budget.
```

This is a configuration example, **not an adopted default mission requirement**. Retain the other assessment and settings when editing. Qualified programs may require a positive reserve instead. Overlapping domains can similarly override `preference` independently; units, source identity and input meaning cannot be silently changed. Numeric preferences and gate limits are separate: never use a good Operations score to compensate for a failed Survival condition.
