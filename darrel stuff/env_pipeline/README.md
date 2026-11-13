# Moon environmental pipeline

**Single active configuration: `config.yml` (`assumption_NASA_values`).** This file controls thresholds, preferences, domain weights and toggles.

## One input CSV

Open and edit **[inputs/sites.csv](inputs/sites.csv)**. This is the single main pipeline input: 83 rows (**17 Artemis-region-labelled, 6 fully populated Apollo-labelled baseline scenarios, 30 synthetic and 30 dummy**) containing `id`, optional UTC window columns and the original measurement columns, including `median_visible_sky_fraction` and `median_earth_visibility_fraction`.

Most measurement cells are populated in the original 77 fixtures, including four intentional dummy blanks. The six Apollo-labelled baseline rows are fully populated, using the measured references, conditional models and explicit test assumptions documented below. The 77 non-Apollo fixtures use fictional eight-day requested windows spread across 2027-2040; synthetic neighbours share their EDA baseline windows; Apollo rows instead use historical landing-to-ascent UTC windows. The original seven EDA-labelled baselines and all synthetic scenarios use equally sized 1.2 km patches and the same map statistics. The ten additional EDA-labelled scenarios have assumed values, including geometry, without a measured footprint. These are controlled software fixtures, not verified NASA site assessments; static maps are not filtered to that future window. NASA labels identify a declared region, not a NASA-selected exact patch or approval of the assumed conditions.

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

Additional NASA scenarios and randomized dummy values use Python `random.Random(20261112)`. NASA scenario ranges are assumed test ranges, not source measurements. Dummy ranges are broader to exercise both sides of configured gates while keeping fractions in 0-1, temperature span equal to high minus low, and sunlight duration within the 192-hour window. Dummy `001`-`010` retain controlled gate/boundary/toggle cases alongside randomized fields; blanks are Sun visibility (`005`), link margin (`006`), UV (`007`) and seismic (`008`). No generated values were tuned to improve NASA scores.

Apollo rows identify the six [historical NASA landing sites](https://nssdc.gsfc.nasa.gov/planetary/lunar/apolloland.html): Apollo 11 (Mare Tranquillitatis), 12 (Oceanus Procellarum), 14 (Fra Mauro), 15 (Hadley-Apennine), 16 (Descartes Highlands) and 17 (Taurus-Littrow). The existing `apollo_<mission>_<site>_assumed` IDs identify baseline scenarios mixing sourced dates, measured historical/modern references, conditional geometry/thermal models and an explicit nominal RF assumption. The estimates below are not NASA measurements. Missing values are not zero-filled. Apollo 13 did not land and has no site row.

| Apollo | `start_utc` (landing) | `stop_utc` (ascent) |
| --- | --- | --- |
| 11 | `1969-07-20T20:17:39Z` | `1969-07-21T17:54:00Z` |
| 12 | `1969-11-19T06:54:36Z` | `1969-11-20T14:25:47Z` |
| 14 | `1971-02-05T09:18:11Z` | `1971-02-06T18:48:42Z` |
| 15 | `1971-07-30T22:16:29Z` | `1971-08-02T17:11:23Z` |
| 16 | `1972-04-21T02:23:35Z` | `1972-04-24T01:25:47Z` |
| 17 | `1972-12-11T19:54:58Z` | `1972-12-14T22:54:37Z` |

Landing sources: [NASA landing table](https://www.nasa.gov/wp-content/uploads/static/history/SP-4029/Apollo_18-27_LM_Lunar_Landing.htm); Apollo 14 uses [first pad contact in its timeline](https://www.nasa.gov/wp-content/uploads/static/history/SP-4029/Apollo_14i_Timeline.htm), not the table's two-seconds-later confirmation time. Ascent sources: NASA summaries for [11](https://www.nasa.gov/wp-content/uploads/static/history/SP-4029/Apollo_11a_Summary.htm), [12](https://www.nasa.gov/wp-content/uploads/static/history/SP-4029/Apollo_12a_Summary.htm), [14](https://www.nasa.gov/wp-content/uploads/static/history/SP-4029/Apollo_14a_Summary.htm), [15](https://www.nasa.gov/wp-content/uploads/static/history/SP-4029/Apollo_15a_Summary.htm), [16](https://www.nasa.gov/wp-content/uploads/static/history/SP-4029/Apollo_16a_Summary.htm) and [17](https://www.nasa.gov/wp-content/uploads/static/history/SP-4029/Apollo_17a_Summary.htm). Values use published whole-second precision; the Apollo 17 summary's corrected ascent is 22:54:37 UTC, not its erroneous 05:54:37 text.

| Existing Apollo input fields | Researched preparation / reason for leaving blank |
| --- | --- |
| `historical_median_vertical_seismic_rms_counts` | **Source-local native PSE references at Apollo 11, 12, 14, 15 and 16.** Apollo 12 retains its 654-day S12/location-00/MHZ median `2.62109086492859` counts, 1973-01-01 through 1974-10-16, from [Dar053](../data/processed/analysis/subject_seismic/20261110T183033924956Z_ba610a/daily_context.csv). Apollo 11/14/15/16 use their own station's three post-ascent archive days as documented below, not copied S12 values. Apollo 17 still has the explicitly borrowed S12 reference: the PSE archive has no S17 station and a different seismic instrument is not silently substituted. These epochs/cohorts differ; no response/gain normalization, quiet-event selection or physical ground-motion conversion is claimed. |
| Sun/Earth/sky visibility and permanent-shadow fraction | **Conditional mission-window model, not mapped measurements:** use a uniform flat, unobstructed reference patch at the [NASA landing coordinates](https://www.nasa.gov/wp-content/uploads/static/history/SP-4029/Apollo_18-27_LM_Lunar_Landing.htm). Apollo `median_sun_visibility_fraction = 1` describes the landing-to-ascent window, not a full lunar cycle. Sun and Earth full-disc elevations remain above the assumed horizon in the JPL geometry described below; Earth visibility remains `1`. Sky fraction remains `2*pi/(4*pi) = 0.5`; permanent-shadow fraction remains `0`. Relief, rocks, hardware and pixel distributions are not reconstructed; these are not native LOLA raster summaries. |
| Regional reference Sun fraction and longest shadow span | **Idealized proxy, not Dar054 history:** Sun fraction `0.5`; nominal half-cycle shadow span `29.5 * 24 / 2 = 354 h`. The rounded 29.5-day phase cycle is a generic reference, not a computed maximum over 2020-2021 or a real terrain-shadow record. |
| `window_continuous_sunlight_hours` | **Conditional flat-horizon estimate:** [NASA HLS-PAP-039, section 3.6](https://ntrs.nasa.gov/api/citations/20230014980/downloads/HLS-PAP-039%20HLS%20White%20Paper%20Non-Design.pdf) gives morning landings, ascent before noon and positive geometric solar elevations across the crew stays. With the explicitly assumed unobstructed local horizon, estimate the daylit run *inside the supplied window* as `(stop_utc - start_utc)/3600`. This is censored at both mission boundaries and is not the site's maximum attainable sunlight run, not a measured power-supply duration and not proof against local terrain/hardware occlusion. Values range from approximately 21.6 to 75.0 h. With `cap_to_window_duration: true`, the sunlight requirement is the smaller of the configured 156 h and this requested window duration; no dates or measurements are extended to force a pass. |
| Three phase-median thermal columns | **Mission-window thermal MODEL cohort, not observed Diviner phases:** use 17 equally spaced instants including landing and ascent. Each instant represents the spatial median of the same uniform flat reference patch. With JPL Sun elevation `e_k` and local albedo `A` from [NASA HLS-PAP-039 Rev A, table 3.6-1](https://ntrs.nasa.gov/api/citations/20230014980/downloads/HLS-PAP-039%20HLS%20White%20Paper%20Non-Design.pdf), calculate `T_k = [104^4 + (390^4 - 104^4) * (1-A) * max(0,sin(e_k))]^(1/4)` K (convert degrees to radians). Supply minimum/maximum/difference across these 17 modeled spatial medians. **Model assumptions:** the existing 390 K dark-equatorial upper anchor, 104 K floor and approximate optical-albedo-as-solar-reflectance treatment are retained. NASA generic temperature endpoints do not validate this response law. No conduction, thermal inertia, emissivity calibration, self-heating, real footprint or propagated uncertainty is included. Apollo uses a mission-window cohort; this is not a measured temperature history or a component operating limit. |
| Radiation counters, spacecraft potential, LDEX current and NMS orbital helium | **Shared measured reference proxies**, not reconstructed Apollo conditions. No defensible mission/site-specific replacement was established for these instrument-specific quantities. Their repeated values are intentional reference assumptions and must not be counted as six independent historical observations. |
| FUV irradiance | Use each mission's **NRLSSI2 historical reconstruction** from [LASP LISIRD](https://lasp.colorado.edu/lisird/data/nrl2_files/). Integrate all 65 complete 1-nm bins centred 115.5-179.5 nm, then take the median of the supported UTC daily band integrals whose dates overlap landing through ascent. Results are modeled daily 1-AU references, not Apollo instrument measurements or subdaily/local surface dose. Whole UTC days include portions outside the precise crew window. They are not cross-calibrated here against the modern SEE fixture cohort. |
| Spacecraft ion/electron density | Where available, use [NASA OMNI](https://omniweb.gsfc.nasa.gov/html/ow_data.html) **near-Earth upstream proxies** during fully contained mission hours, not lunar surface or P1 ESA observations. Mask proton fill `999.9`, reject nonpositive/nonfinite density and missing spacecraft ID. With valid alpha/proton ratio `r`, estimate ion density `n_p*(1+r)` and electron density `n_p*(1+2*r)`; without alpha support, approximate both as proton density (H-only quasi-neutral model). Medians use supported hours only; coverage is incomplete, especially Apollo 11. These are conditional density proxies, not an ESD/surface-charging model. |
| `window_minimum_link_margin_db` | **Explicit TEST ASSUMPTION:** nominal `0 dB`, because no qualified historical minimum RF-margin series has been reconstructed. This is not derived from received power in dBm or Earth visibility. The comms gate remains disabled by the existing config; do not treat the placeholder as engineering evidence if enabling it. |

Earth-clearance geometry uses [JPL Horizons](https://ssd-api.jpl.nasa.gov/doc/horizons.html) airless apparent target-centre elevation and angular diameter at the actual landing coordinates and historical UTC windows. Full-disc clearance is `elevation_deg - angular_diameter_arcsec / 7200`. It supports only the stated unobstructed-horizon mission-window model, not local terrain clearance, actual DSN contact or an RF margin.

These are **fully populated baseline scenarios, not a fully measured Apollo dataset**. Numeric completeness does not establish historical accuracy. The approximate map geometry, modern reference epochs and modeled mission-window thermal cohort are not like-for-like measured support. They permit all nine diagnostic domain scores to run, subject to the configured gates. The upper ground-temperature gate is a globally applied 390 K project surface-model envelope, consistent with the generic equatorial noon anchor. Historical NASA site selection is a positive calibration reference for intended operations, not a proof that these proxy rows are measured historical truth. This project envelope is not a component qualification limit or NASA-certified safety threshold, and there is no ID-based Apollo exemption.


Apollo mission-window geometry and thermal preparation:

- Query the [JPL Horizons API](https://ssd-api.jpl.nasa.gov/doc/horizons.html) for Sun `COMMAND=10` and Earth `COMMAND=399`, with `EPHEM_TYPE=OBSERVER`, `CENTER=coord@301`, `COORD_TYPE=GEODETIC`, and `SITE_COORD=east_longitude,latitude,0` (degrees, degrees, km). Coordinates below follow NASA's IAU Mean Earth landing table; Horizons uses its lunar Mean Earth frame. The nominal reference-surface elevation is an assumption, not surveyed local height.
- Set `START_TIME` and `STOP_TIME` from the row's retained UTC dates, `TIME_TYPE=UT`, `TIME_DIGITS=FRACSEC`, `STEP_SIZE=256` (256 equal intervals, 257 samples including endpoints), `QUANTITIES=4,13`, `CSV_FORMAT=YES` and `APPARENT=AIRLESS`. Require complete, finite geometry; do not replace missing ephemerides with defaults. Query parameters are passed as quoted values per the API documentation.
- Use every sixteenth Sun sample to form the complete 17-instant thermal cohort. Treat each modeled instant as a uniform-patch spatial median. The table lists these modeled cohort extrema, not raw measured temperature extrema. Sun elevations increase across these morning windows.
- For this explicit scenario, piecewise-linear interpolation of the supported positive full-disc clearance defines the continuous flat-horizon visibility model. Its Sun visibility fraction is 1 and its window-censored sunlight duration equals the retained visit duration. This interpolation is not proof of actual uninterrupted sunlight: local shadows, terrain, surface assets and unmodeled occultations are not reconstructed. Earth visibility is likewise conditional and does not establish communications service.
- Keep regional Sun visibility `0.5` and regional shadow span `354 h` as long-cycle reference assumptions, not mission-window outputs. No radiation/current/potential/helium unit conversion is introduced.

| Apollo | East longitude / latitude (deg) | Albedo | Sun elevation, landing / ascent (deg) | Modeled low / high / span (K) | Minimum full-Earth-disc clearance (deg) |
| --- | --- | ---: | --- | --- | ---: |
| 11 | 23.47297 / 0.67408 | 0.078 | 10.703 / 21.707 | 252.398 / 298.754 / 46.356 | 57.917 |
| 12 | -23.42157 / -3.01239 | 0.098 | 5.149 / 21.079 | 210.948 / 295.104 / 84.156 | 60.338 |
| 14 | -17.47136 / -3.64530 | 0.114 | 10.349 / 27.265 | 247.964 / 311.865 / 63.900 | 65.008 |
| 15 | 3.63386 / 26.13222 | 0.094 | 12.025 / 41.416 | 258.446 / 343.438 / 84.991 | 66.587 |
| 16 | 15.50019 / -8.97301 | 0.196 | 14.760 / 50.014 | 263.649 / 345.785 / 82.136 | 71.921 |
| 17 | 30.77168 / 20.19080 | 0.094 | 13.350 / 47.797 | 265.005 / 353.213 / 88.207 | 43.029 |

**Interpretation:** Apollo thermal and Sun-visibility fields describe short mission windows, while non-Apollo geometry/thermal fixtures retain their existing long-period or phase-cohort assumptions. Their numerical scores are not like-for-like long-term habitat rankings. Differences in temporal support do not establish superior long-term habitability. The flat-patch spatial median is a modeling identity, not a measured footprint statistic. The HLS solar-angle compilation also uses Horizons, so agreement is not independent ephemeris validation. The [NASA Apollo thermal discussion](https://nasa.gov/wp-content/uploads/static/history/alsj/WOTM/WOTM-ThermalEnvrnmnt.html) provides useful context but its cable thermocouple temperatures are not direct validation of this uniform-ground model. All other Apollo values retain the source/assumption limitations documented here.

Apollo reference values and preparation (shared references are distinguished from mission-window replacements; no label-dependent fitting):

| Input | Value | Reference cohort / statistic |
| --- | --- | --- |
| Orbital radiation median / maximum | `28` / `71` counts per SEC record | [Dar049 daily context](../data/processed/analysis/subject_radiation_time/20261110T233725005604Z_72515a/daily_context.csv), `RAD_CRATER_SEC_selected_state`. Representative day 2023-09-19, selected by nearest daily median to the 1,091-day cohort median, earliest date as tie-break. Both statistics are from that SAME day, not a three-year maximum or Apollo exposure reconstruction. |
| FUV irradiance | Mission-specific; see table below | NRLSSI2 daily reconstruction. These values describe reconstructed historical daily irradiance, not modern SEE observations. |
| Ion / electron density | Mission-specific where OMNI coverage exists; **Apollo 15 retains** `3.481162190437317` / `5.511419773101807 cm^-3` | Apollo 15 has no valid OMNI proton hours in its fully contained mission hours; no density is invented or interpolated. Its retained values are explicitly the previous 2023-2026 Dar046/P1 reference, NOT reconstructed Apollo 15 plasma. Other rows use the conditional historical proxies below. |
| Spacecraft potential | `3.2584742307662964 V` | Same Dar046 file, median of 1,140 supported `ESA_v01_thb_peif_sc_pot` daily medians. Not surface voltage. |
| LDEX current | `38230 charges/s` | [Dar048](../data/processed/analysis/subject_dust/20261110T231630522312Z_a8ddbb/current_daily_context.csv), median of 166 supported `LDEX_CURRENT` daily medians, 2013-2014; not surface deposition. |
| Orbital helium | `6460 particles/cm3` | [Dar051](../data/processed/analysis/subject_exosphere/20261110T233735590232Z_dffb7c/daily_context.csv), median of 148 supported `NMS_He_ABUNDANCE` daily medians, 2013-2014; not Apollo LACE or total exosphere density. |

Station-specific seismic source and preparation: [NASA PDS Apollo PSE archive](https://pds-geosciences.wustl.edu/lunar/urn-nasa-pds-apollo_pse/data/xa/continuous_waveform/). The sample policy is declared **before** examining values: use the three archive UTC dates starting two calendar days after each mission's ascent date, with station `S<mission>`, location `00`, channel `MHZ`. This targets post-crew site references, not the crew's exposure or an annual quiet-site distribution. Reuse the exact `raw_statistics()` function from the existing `stage3_seismic_eda.py`: exclude nonfinite samples and `-1` fills, centre each valid daily file on its median, compute `sqrt(mean((x-median(x))^2))`, then take the median of the three daily RMS values. No filtering, interpolation, response removal or exclusion of high-count days is applied.

| Apollo station | Archive dates | Median daily RMS counts | Per-day valid / recorded samples |
| --- | --- | --- | --- |
| S11 | 1969-07-23, 1969-07-24, 1969-07-25 | 67.3878981781 | 540868/571800; 305494/570872; 569829/572360 |
| S14 | 1971-02-08, 1971-02-09, 1971-02-10 | 7.40550277151 | 571510/572436; 570611/572432; 570761/572432 |
| S15 | 1971-08-04, 1971-08-05, 1971-08-06 | 17.178313181 | 570816/572432; 558343/572432; 562639/572432 |
| S16 | 1972-04-26, 1972-04-27, 1972-04-28 | 20.6313294233 | 570907/572436; 571340/572440; 571361/572436 |

These small native-count samples are not directly comparable calibrated hazard levels. Instrument response, heating, archive clock support, telemetry gaps and ADC-endpoint samples can affect the statistic. StationXML assigns the same nominal peaked-mode sensitivity to the selected location-00/MHZ channels (3,579,160,000 counts per metre); this is NOT evidence that their nominal gains differ. Equal nominal response does not make these short raw-count samples a qualified structural demand or provide an adopted 15-count site-failure limit. In particular, S11's middle sample has substantial gaps. Preserve these limitations rather than treating a high count RMS as proof of an unsuitable site. The stored 15-count threshold is retained for configuration compatibility, but `seismic.hard_gates_enabled: false` disables that unsupported hard gate for **every row**. No source value is reduced and no Apollo ID is exempted. The nine domain definitions and their test-score aggregation are retained; raw-count scores are descriptive test proxies, not calibrated structural-risk rankings. Apollo 12 retains its broader, different historical cohort, so this is not a controlled cross-station experiment. The config's legacy S12 evidence-family label is a software grouping identifier, not sufficient row-level station provenance; use the actual station/source references here.

Native source receipts (relative to the PDS `continuous_waveform/` URL above; no external baseline file is loaded by the scorer):

| Source path | SHA256 | ADC-endpoint samples (0 or 1023; not automatically reclassified) |
| --- | --- | --- |
| `s11/1969/204/xa.s11.00.mhz.1969.204.0.mseed` | `6ea8794b3148b5e843655d80842a6c4b1b054bd4f7d8843f47f3b99547c0f5af` | 6835 |
| `s11/1969/205/xa.s11.00.mhz.1969.205.0.mseed` | `7f88e3466a9faeee3a83ac6680a59d55c5b4f1643fb3999e8c1b24cac7d24e9d` | 3411 |
| `s11/1969/206/xa.s11.00.mhz.1969.206.0.mseed` | `25ec27059c179465de101ffaa6025ed98c33c06b3c137ed2ace6c45630661046` | 3709 |
| `s14/1971/039/xa.s14.00.mhz.1971.039.0.mseed` | `65f4acf27138641ab9489a8d4a12d6fd34d3e5aaad0d2f311501c23d9cc13521` | 652 |
| `s14/1971/040/xa.s14.00.mhz.1971.040.0.mseed` | `e9b15082a42a6a8eefa0ca988b0a1aaa77ff77b562a2090721379170d4f62db9` | 0 |
| `s14/1971/041/xa.s14.00.mhz.1971.041.0.mseed` | `2a4c73625677421e2d537fb2d16bf20eed503e486bd43aa494b68af9ac46e248` | 5 |
| `s15/1971/216/xa.s15.00.mhz.1971.216.0.mseed` | `9d76666a614aaf7ea88bd2a405e4fa50c745cb1413ec02b0915b33a5dd26167e` | 502 |
| `s15/1971/217/xa.s15.00.mhz.1971.217.0.mseed` | `061b790602160c0a61848469c4968e9e8165e2afd164ef4b4b249e5304d87a8d` | 1894 |
| `s15/1971/218/xa.s15.00.mhz.1971.218.0.mseed` | `b7d7389850ed07adcf36a17210391ca5a3b8b1e3ce2d7b6aa98d3259efcb0b06` | 0 |
| `s16/1972/117/xa.s16.00.mhz.1972.117.0.mseed` | `2aac9da7ec33e839eb073c33f978b2434b6316db2ced525b6a1a9d818dd104be` | 2749 |
| `s16/1972/118/xa.s16.00.mhz.1972.118.0.mseed` | `7df0056d93dfcdf6ae95dc62dd0dac14d40fe43e6e1297177d7b050b463d59bd` | 708 |
| `s16/1972/119/xa.s16.00.mhz.1972.119.0.mseed` | `ce53afdf48c22f52d23f928fef2b39eb2967f8dd998d523a0b287b889cb10f8e` | 345 |

Mission-specific evidence (no random perturbation):

| Apollo | NASA local albedo | Reconstructed FUV W/m2 | Ion proxy cm^-3 | Electron estimate cm^-3 | Valid OMNI proton hours / fully contained hours | Supported alpha-ratio hours |
| --- | --- | --- | --- | --- | --- | --- |
| 11 | 0.078 | 0.0253984304063 | 8.1 | 8.1 | 3 / 20 | 0 |
| 12 | 0.098 | 0.0258952640179 | 3.9 | 3.9 | 23 / 31 | 0 |
| 14 | 0.114 | 0.0256690829819 | 3.9 | 3.9 | 14 / 32 | 0 |
| 15 | 0.094 | 0.0245966059219 | shared modern reference | shared modern reference | 0 / 66 | 0 |
| 16 | 0.196 | 0.0251757139422 | 9.6824 | 10.2648 | 53 / 70 | 53 |
| 17 | 0.094 | 0.0239239812599 | 11.8623 | 12.2746 | 58 / 74 | 58 |

Proton coverage is not continuous mission coverage: partial first/last hours are excluded; the reported hours also have gaps. Apollo 12 and 14 legitimately share a 3.9 proton-density median despite different underlying windows. No manufactured numerical differences are added. Density inputs are context-only under the existing scoring rules; the shared spacecraft-potential input still controls the plasma score.

Reproduction: LASP endpoint `https://lasp.colorado.edu/lisird/latis/dap/nrl2_ssi_P1D.jsond`, filtered to each row's UTC start/stop **dates** and `115 <= wavelength <= 180` nm; require the exact 65-bin grid and finite positive values for every included day. OMNI annual ASCII files are at `https://spdf.gsfc.nasa.gov/pub/data/omni/low_res_omni/omni2_<year>.dat`; word 24 is proton density and word 28 is alpha/proton ratio. Alpha fill `9.999` is not a measured ratio. Both substitutions retain their source/quantity limitations above.

Source-response SHA256 receipts (historical files may later be revised):

| Apollo | LASP query response SHA256 |
| --- | --- |
| 11 | `1832e0df9bf5d931484365f0406f35ef293809a721b64437ba9c20b4dc29a871` |
| 12 | `a4acb8de82e2bc9710173c84e4ad2160752a7f1125423d4bb35125ea88bff73c` |
| 14 | `e6bae19458daf46ac22cc8bfa688bb733743d05baa5c47d664d9be9a2572e4c9` |
| 15 | `def3a45c3b355340b20053da79d66693d4179413e06a03d3dbc5ac78ca9b6a2c` |
| 16 | `844131ce4f11c76b01cfb583587b9b03c0c9b104d4f163e6a0b3730f5cf13eff` |
| 17 | `ea9fb50eefb1010a22e93a847b3e74509727e183309c84db7008d39c305ad567` |

- `omni2_1969.dat`: `8bb9090254a1fbedd0d1b4dd0ec6004823c17e63ef3a1d40c03edfa2e8b2bcc7`
- `omni2_1971.dat`: `8235e7ebb443161860bf7ef4b61c69267a23bdbb19ead75ee3e03af5905a294c`
- `omni2_1972.dat`: `be11befb620501125c494e92c1ddc2689d0b5c102e4a3f5ebc46a228f0fff2f1`

Earth and Sun visibility are 1 in all six conditional flat-horizon mission-window cases; the regional long-cycle reference Sun fraction remains 0.5. Repeats follow the geometry rather than invented site differences. Shared radiation/dust/helium/voltage and the remaining Apollo 17 borrowed seismic reference are still unresolved limitations, **not independent site validation**. Different NASA landing sites do not imply every global reference or every clipped/plateau score must differ. The output layout does not carry per-cell provenance; consult this section before interpreting an Apollo row as measured ground truth.

The [approximately 29.5-day phase cycle](https://science.nasa.gov/moon/moon-phases/) supports the regional 354 h half-cycle only as an idealized reference; it must not be described as a measured longest shadow run. The mission dates remain in use by the capped sunlight gate and are intentionally retained.

Local primary-report sources under `D:/projects/NASA Dataset/keep/` (physical PDF page numbers, not printed section-page numbers):

- `A16_MissionReport.pdf`, pp. 28-31: central-station thermal-plate temperatures, abnormal seismic-instrument heating, received signal power and failed heat-flow deployment. Hardware temperatures are not phase-median ground temperatures; received power in dBm is not available-minus-required link margin in dB. Activity/impact seismic descriptions do not establish the configured daily RMS statistic.
- `Apollo_17_Postflight_Mission_Report_19730015117.pdf`, pp. 37-38, 40-44 and 76: station thermal management, heat-flow deployment, mass-spectrometer activation/background, ejecta detection, gravimetry, radiation-detector context and soil observations. A probe reading near insertion, internal component heating, particle-track counts or local surface mass spectroscopy cannot replace phase medians, CRaTER SEC counters, LDEX current or NMS orbital helium.
- `a17_final-flight-mission-rules_19720068065.pdf`, pp. 33 and 51: historical EVA/communications contingencies depend on crew activity, configuration and recovery options. They do not provide a footprint visibility fraction or numeric minimum RF margin.

These references have the quantity and instrument limitations described above. OCR can be imperfect; ambiguous figure or text values must not be treated as precise measurements.

There is no separate domain-score input CSV. Domain scores are calculated by the pipeline; do not enter scores in place of physical measurements.

[input_template.csv](sample_input.csv) has exactly the same input headers as `inputs/sites.csv`, with three clearly fictional examples: `dummy_example_pass`, `dummy_example_fail` and `dummy_example_unknown`. The failure supplies 155.99 h in a 192 h window; the Unknown example supplies sunlight duration but omits both dates. `start_utc` and `stop_utc` are retained because the adaptive sunlight gate requires them.

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
| `median_earth_visibility_fraction` | [NASA LOLA polar Earth-visibility maps](https://pgda.gsfc.nasa.gov/products/69), alongside the solar products. Local files: `darrel stuff/data/moon/illumination_2016/geotiff/south/earth_visibility/`. | Mask native fills before applying the paired label's scale/offset. Select the same documented footprint/support as the Sun/shadow summary and take the median Earth-disc visibility fraction, 0-1. Partial-disc visibility does not prove DSN/relay contact or a working RF link. |
| `window_continuous_sunlight_hours` | A candidate-local, time-resolved illumination calculation using a documented terrain/horizon model and [NAIF/SPICE ephemerides](https://naif.jpl.nasa.gov/naif/data.html), for the requested UTC window. This is a derived quantity, not a static-map lookup. | Under a documented visibility criterion, calculate the uninterrupted supported sunlight duration in the candidate window, in hours. Preserve cadence, gaps and boundary censoring. A sampled clear run alone does not prove continuous sunlight between samples; leave this field blank if continuity cannot be established. Do not multiply map-average visibility by window duration or substitute a regional reference. A valid supplied duration cannot exceed its requested window. |
| `window_minimum_link_margin_db` | A mission-specific, qualified RF link-budget calculation using the actual spacecraft/surface antenna, DSN or relay configuration, geometry, losses, noise, data rate and required receiver performance. It is not supplied by an Earth-visibility raster. | Evaluate available-minus-required link margin at the supported times/configurations across the requested candidate window; supply the qualified minimum in dB. Preserve outages and inadequate geometry/support; do not summarize only successful contacts to hide loss of service. Leave blank without the required engineering inputs. This field is ignored when the domain's hard gates are disabled. |
| `median_visible_sky_fraction` | The same [LOLA sky-visibility products](https://pgda.gsfc.nasa.gov/products/69). | Select the candidate's supported sky-solid-angle pixels, take the median in steradians, then divide by `4*pi`. Do not substitute a radiation dose or divide by `2*pi`. |
| `permanently_shadowed_cell_fraction` | The same [LOLA permanent-shadow products](https://pgda.gsfc.nasa.gov/products/69). | Count candidate cells classified as permanent shadow and divide by the supported candidate-cell count. Keep the grid, mask and footprint consistent. |
| `lowest_phase_median_temperature_kelvin`, `highest_phase_median_temperature_kelvin`, `phase_median_temperature_range_kelvin` | [LRO Diviner derived temperature products](https://pds-geosciences.wustl.edu/missions/lro/diviner.htm) and their labels, using the same documented phase-product cohort. | For candidate-associated points, calculate a median for each selected phase product. Only with the complete common cohort: take the lowest median, highest median and their difference. Do not replace these with raw instantaneous temperature minima/maxima. If the cohort is incomplete, leave the three values blank. A profile from a different EDA footprint/cohort does not automatically apply to the current 1.2 km patches. Non-Apollo thermal test values are assumptions. The six Apollo scenarios use the separately declared complete 17-instant mission-window model cohort, not Diviner products or a full-cycle cohort. |
| `regional_reference_sun_visibility_fraction`, `regional_reference_longest_shadow_sample_span_hours` | A regional horizon/illumination calculation using a documented lunar elevation model, Sun ephemerides and [NASA NAIF/SPICE kernels](https://naif.jpl.nasa.gov/naif/data.html). These are calculated values, not a ready-made pair of downloadable measurements. | To reproduce the earlier EDA reference, use the same region center, 2020-2021 period, 2 m height, 20 km horizon radius and hourly sampling. Clear fraction = clear samples / recorded samples. For each blocked run, measure first-to-last sampled time and keep the longest span. Preserve gaps/censoring; it is not guaranteed continuous darkness. These remain regional reference values, not candidate-local measurements. |
| `orbital_radiation_counter_median`, `orbital_radiation_counter_maximum` | [LRO CRaTER archive](https://pds-ppi.igpp.ucla.edu/data/lro-crater/), secondary science (`SEC`) tables with their labels. | For the current project's selected-state cohort, retain `BIASCMD=1`, `CALLOW=0`, `CALHIGH=0`, all six `PROCDFLAG=1`, and finite nonnegative `GOOD`/`REJECT`/`TOTAL` counters. Compute each UTC day's `GOOD` median and maximum. The first CSV value is the median of valid daily medians; the second is the maximum of valid daily maxima. This cohort is a project selection, not complete instrument qualification. Preserve counts per SEC record; no dose conversion is implied. |
| `median_solar_far_uv_irradiance_w_m2` | [TIMED SEE Level 3 daily spectra](https://lasp.colorado.edu/see/data/daily-averages/level-3/), NetCDF products and README. | Use the complete supported 115-180 nm band. Integrate the daily spectral irradiance across the band using wavelength-bin widths, then take the median of valid daily band integrals. Result: W/m2. Retain model-assisted/flare-removed/1-AU scope; this is not a local surface UV reading. |
| `median_spacecraft_ion_density_per_cm3`, `median_spacecraft_electron_density_per_cm3`, `median_spacecraft_electric_potential_volts` | [THEMIS/ARTEMIS data access](https://themis.ssl.berkeley.edu/data_products/index.php?nlist=2&ntype=2_tha-2_thb-2_thc-2_thd-2_the): select `thb` / ESA L2 (ARTEMIS P1), not an arbitrary Earth-orbit plasma product. | Use `thb_peif_density`, `thb_peef_density` and `thb_peef_sc_pot`, respectively. Apply native fill/valid-range, unique-clock and quality==0 selection. Keep full-ion and full-electron modes separate. Compute daily record medians, then the median of valid daily medians. Preserve native density/potential units; spacecraft potential is not surface charging voltage. |
| `historical_median_dust_detector_current_charges_per_second` | [LADEE LDEX calibrated data](https://sbnarchive.psi.edu/pds4/ldex/ladee_ldex_20240411/data_calibrated/), `current/` tables plus paired XML labels. Existing local copies are under `D:\projects\NASA Dataset\datasets\D10\` and the earlier `darrel stuff/data/moon/eda_pilots/D10/` baseline. | Read native `CURRENT`, apply clock/fill handling, retain signed background-subtracted values, take daily medians and then the median across valid days. Unit: elementary charges/s. Do not insert impact-catalog counts or mass-deposition estimates into this field. |
| `historical_median_vertical_seismic_rms_counts` | [Apollo PSE archive](https://pds-geosciences.wustl.edu/missions/apollo/apollo_pse.htm): MiniSEED or equivalent GeoCSV with metadata, selecting station S12 for the original reference, location/mode `00`, channel `MHZ`; the additional Apollo station references are explicitly identified above. | Reproduce the project's daily median-centred RMS count statistic: for valid samples `x`, RMS = `sqrt(mean((x - median(x))^2))`, with the same trace/gap handling. Then take the median of supported daily RMS values. This is a project-defined count statistic, not a NASA ground-motion safety limit, event rate or acceleration measurement. |
| `historical_median_orbital_helium_density_per_cm3` | [LADEE NMS archive and calibrated collections](https://pds.nasa.gov/ds-view/pds/viewBundle.jsp?identifier=urn:nasa:pds:ladee_nms&version=2.0), helium abundance tables and labels. | Use `He_ABUNDANCE`; retain valid, unambiguous clocks and supported abundance values. Calculate daily medians, then their median. Native `P/Cc` means particles per cubic centimetre; no numerical unit conversion was made by renaming the header. Preserve orbital altitude/local-solar-time and uncertainty context; do not treat it as surface atmosphere. |

For all daily summaries, use equal weight per valid day, not an average pooled across unequal record counts. Missing days are not zero. Do not combine different instruments, versions, species or modes under one measurement name.

The earlier regional model reference covers 2020-2021, dust/helium references cover 2013-2014, and the seismic reference covers 1973-1974. These do **not** become 2030 observations because the test CSV carries 2030 requested dates. Static product label acquisition dates are not a candidate-window chronology either. The active assumption policy uses fictional scoring mappings; it does not qualify these references as local hazard measurements. Source summaries, quality masks and aggregation steps are preparation choices; changing them requires documenting the new meaning, not silently retaining an incompatible header.

### Local data and EDA cross-checks

Paths below are relative to the repository root unless they start with `D:/`.
Use the original labels/README and quality flags along with the numeric files.

| Source family | Existing local source location | Relevant EDA cross-checks |
| --- | --- | --- |
| Sun/Earth/sky visibility and permanent shadow | `darrel stuff/data/moon/illumination_2016/`; documented region extents under `darrel stuff/data/moon/sdem/` | Dar020 candidate support, Dar021 preference sensitivity and Dar054 reference-point/time/footprint limits |
| Phase thermal | `darrel stuff/data/moon/diviner/`; additional model/reference files under `D:/projects/NASA Dataset/datasets/D20_PRP/` and `D28/` | Earlier Diviner phase/cohort analyses; Dar047 depth-specific historical thermal and Dar050 static polar model are different quantities, not replacements for missing phase profiles |
| Radiation | `D:/projects/NASA Dataset/datasets/D07/`, with earlier local support under `darrel stuff/data/moon/eda_pilots/` | Dar041, Dar043 and Dar049: instrument/cohort/time support and nonlocal dose limitations |
| Solar UV | `D:/projects/NASA Dataset/datasets/D09_SEE/` | Dar044 and Dar045: complete spectral-band support, quality and time coverage |
| Plasma / spacecraft potential | `D:/projects/NASA Dataset/datasets/D11_ESA/`; separate P2 context in `D11_P2/` | Dar044 and Dar046: full/reduced modes, clocks and native quality selection must not be pooled |
| Historical dust | `D:/projects/NASA Dataset/datasets/D10/` | Dar044 and Dar048: signed current, uncertainty and mass-threshold distinctions |
| Historical seismic | `D:/projects/NASA Dataset/datasets/D14_PSE/` | Dar044 and Dar053: S12 channel/mode, gap handling and raw-count/response distinctions |
| Historical exosphere | `D:/projects/NASA Dataset/datasets/D35/` | Dar044 and Dar051: species, uncertainty, orbital sampling and clock handling |

See [EDA notes](../EDA/EDA_Notes.md) and [research/source notes](../research/Research_Notes.md) for the accepted scopes. Cross-checking studies does not make different footprints, instruments, epochs or statistics interchangeable. Preserve original file/version, coordinates, masks, supported counts, actual dates and aggregation choices in preparation notes. The standalone scorer cannot verify that provenance from a numeric cell.

### Where do thresholds and multipliers come from?

They are **configuration decisions, not another downloadable measurement**. Use a justified applicable screening requirement for a hard threshold, documented utility reference bounds for a preference, and explicit project priorities for multipliers. An observed maximum is not automatically a safety limit. Validate sensitivity to multiplier choices; do not label project weights as NASA weights. The current `assumption_NASA_values` thresholds, preference directions/bounds and domain weights are explicitly project assumptions for testing, not sourced or adopted NASA safety requirements. Change them in `config.yml`; do not infer them from the fixture min/max.

## Run

From the repository root:

```powershell
python "darrel stuff/env_pipeline/env_pipeline.py" --output "darrel stuff/env_pipeline/outputs/results.csv" --overwrite
```

`inputs/sites.csv` is selected by default. The optional `--input` flag selects one replacement CSV, not additional input files. `config.yml` is configuration, not a second site-input CSV. Existing output files are protected; add `--overwrite` only when you want to replace the selected output.

## Simple output

The command-line default writes only enabled domain columns. With all ten domains enabled, it writes **14 columns**:

```text
ID, radiation, thermal, solar_illumination, dust, plasma_charging,
uv, seismic, exosphere, communications_geometry, soil_score,
hard_gate_status, Fail Reason, final_habitability_score
```

`final_habitability_score` is always the final column. Domain and habitability scores
are on 0-100 and displayed to two decimal places (internal calculations retain
full precision). `Fail Reason` lists blocking gates with actual values, required
YAML limits and units, or explains missing required evidence/configuration. It is
blank when a final score is available; omitted measurements in available-data mode
are not themselves failures. Detailed export includes the same column alongside
the existing audit reasons. A final score
remains blank when an evaluated mandatory gate fails/is unknown or configuration
is incomplete. In available-data mode, blank measurements are omitted rather than
zero-filled; see the mode/toggles below.

The final score is the weighted mean of the included,
available domain scores, not a sum or an extra hard-gate penalty. It uses unrounded
domain scores, so weighting the displayed two-decimal values can differ slightly.
Priority labels do not change weights; `multiplier` does. Turning off a domain's
hard gates does not remove its score: communications still contributes while
`enabled: true` and `include_in_score: true`, even when `hard_gates_enabled: false`.

For full audit details, explicitly request `--detailed`:

```powershell
python "darrel stuff/env_pipeline/env_pipeline.py" --output "darrel stuff/env_pipeline/outputs/results.csv" --detailed --overwrite
```

This still writes only the selected output CSV; it does not generate a duplicate.
`--compact` remains accepted as an explicit synonym for the simple default.
The Python `run()` API keeps its existing detailed default for compatibility;
pass `compact=True` to request the simple export directly.

## Pipeline flow (matching the code)

```text
config.yml + inputs/sites.csv
              |
              v
Validate configuration and input rows
              |
              v
For each site, evaluate measurements:
  - Hard gates: Passed / Failed / Unknown
  - Soft preferences: normalized utilities, 0-1
  - Context-only values: retained, not scored
              |
              v
Calculate enabled diagnostic domain scores, 0-100
              |
              v
Calculate comparison_preference_score from the mode-selected available domains
              |
              v
Check final eligibility:
  - Any mandatory failure -> no final score/rank
  - Any evaluated unknown gate or unconfigured selected score/weight -> no final score/rank
  - Enabled evaluated gates pass and mode-selected scoring is complete -> final score
              |
              v
Rank eligible sites within the same requested UTC window
              |
              v
Write one results CSV (full or --compact)
```

| Code entry point | Responsibility |
| --- | --- |
| `main()` | Select the single input, config, output path and export options. |
| `run()` | Load config/input, call the evaluator and write the results CSV. |
| `load_config()` / `validate_config()` | Validate settings and hash the YAML used. |
| `read_csv()` | Validate IDs, numeric inputs, declared physical bounds and optional UTC pairs. |
| `assess()` | Evaluate each site, calculate domain/aggregate scores, qualify final scores and assign ranks. |
| `hard_check()` / `gate_margin()` | Evaluate inclusive mandatory comparisons and signed distances from their limits. |
| `utility()` | Normalize the soft preference and apply its configured utility curve. |

Hard gates and preferences are evaluated inside the same per-site/domain loop.
**Gate-first eligibility** means a failed/unknown gate blocks the final recommendation;
it does not prevent diagnostic domain scores from being calculated.

```text
domain_score = 100 * sum(metric_weight * utility) / sum(metric_weights)
comparison_preference_score = sum(domain_weight * domain_score) / sum(domain_weights)
final_recommendation_score = comparison_preference_score only when eligible
```

The aggregate uses the configured relative weights of domains actually included
for that row. Available-data mode explicitly renormalizes around missing
measurements; strict mode withholds the aggregate instead. The detailed output
records the actual per-row `score_scope`, coverage and normalized contributions.
`final_habitability_score` and `final_recommendation_score` receive the same eligible value.
Final ranks sort scores descending; equal scores use assessment ID as the tie-break.
Undated assessments form a separate group from dated ones, and input row order is
preserved in the output. `--compact` changes only the exported columns to ID plus
domain scores, gate status and the final habitability score, not the calculations or gate decisions.

## Pipeline mode and independent domain toggles

Current settings in `config.yml`:

```yaml
pipeline_mode: available_data  # strict | available_data

domains:
  communications_geometry:
    enabled: true
    include_in_score: true
    hard_gates_enabled: false
```

| Setting | Meaning |
| --- | --- |
| `enabled: false` | Disable the entire domain: no measurement evaluation, scores, weights or gates. Its simple-output column is omitted. |
| `include_in_score: false` | Exclude the domain from the aggregate, while leaving its enabled hard gates active. Diagnostic scores may still be shown. |
| `hard_gates_enabled: false` | Turn off only this domain's hard checks. Supplied scoring inputs still contribute when included. Gate-only measurements are ignored. |
| `pipeline_mode: strict` | A missing selected measurement blocks its domain/final score; missing required gate evidence is Unknown. |
| `pipeline_mode: available_data` | Omit blank measurements and renormalize metric/domain weights per row. Missing-only domains stay blank, but do not block otherwise supported final scoring. |

**Comms is currently enabled for scoring, with its hard gate off.** If two rows
have Earth-visibility data, comms contributes to those two. If a third has no
Earth-visibility data, its comms score stays blank and the aggregate uses its
other available domains. Missing/negative link-margin values do not block any
row while comms hard gates are off. Re-enable `hard_gates_enabled` to apply them.

In available-data mode, a missing measurement for an otherwise configured active
gate is recorded as `Skipped_missing`, not as a physical pass. Supplied values
are still checked against all enabled YAML hard gates. A known failure still
blocks the final score. Unconfigured limits/weights/preferences and missing
required dates for **supplied** measurements are not excused by this mode.

If every selected gate lacks data, eligibility stays Unknown. If all hard gates
are intentionally toggled off, available-data mode permits a preference-only
score when at least one complete included domain is available. A row with no
scoring data never receives an invented zero or final rank.

Missing mode/toggle settings preserve compatibility: `strict`, `enabled: true`
and `hard_gates_enabled: true`. Input columns do not need to change when toggling.
The same settings work for every domain. Detailed output records the mode, skipped
checks, actual score scope, coverage and normalized contributions. Simple output
keeps only ID, enabled domain scores, gate status, `Fail Reason` and the final score.

**Available-data scores may use different factors across rows.** Inspect the
scope/coverage in `--detailed` before treating them as like-for-like site comparisons.
This is an explicit test/comparison policy, not evidence of operational safety.

## Scoring behavior

The ten domains are radiation, thermal, solar illumination, dust, plasma/charging, UV, seismic, exosphere, communications geometry and experimental soil.

The solar gate uses an opt-in `cap_to_window_duration: true`: effective threshold = `min(configured threshold, (stop_utc - start_utc) in hours)`. Thus a short visit must have modeled continuous sunlight for its entire requested window; a window of 156 h or longer still requires 156 h. This is an explicit project policy for comparing different mission durations, not a newly sourced universal NASA rule. Missing dates remain Unknown for a supplied duration; missing limits are not defaulted. A supplied sunlight duration beyond the window is rejected. Detailed gate audit records both configured and effective thresholds.

Apollo source selection prioritizes relevant measured references, then traceable derivations, then explicitly conditional models/test assumptions?not the highest numerical result.

**Evidence-first baseline acceptance policy:** NASA's historical site selection is a positive-case reference for each mission's intended operations. It is not a measurement of every CSV quantity, a guarantee of a score of 100, or proof that a proxy feature vector is historical ground truth. Genuine equal/close observations and declared shared backgrounds are preserved. No random jitter, arbitrary site multipliers, quiet-day cherry-picking or Apollo-ID-based gate exemption is permitted. Selected sites are not a ground-truth negative label for other sites NASA did not select.

| Evidence family | Independent source / derivation | What it does not establish |
| --- | --- | --- |
| Mission dates/site identity | NASA flight summaries and event timelines, cross-checked against the later HLS compilation | A second NASA page quoting the same flight record is corroboration, not an independent measurement. |
| FUV | LASP NRLSSI2 reconstruction, complete 115-180 nm daily bins for the individual mission dates | Model estimates, not Apollo UV measurements or protected dose. Shared model biases remain. |
| Upstream plasma context | NASA OMNI hourly spacecraft records; actual per-mission support is tabulated above | Near-Earth coverage is not local lunar plasma. Derived electron values are not independent electron observations. Apollo 15 remains a declared borrowed reference. |
| Geometry/thermal | NASA landing coordinates, source-reported local albedo and conditional flat-horizon/phase models | A common model is not six independent direct observations. Thermal/solar/model-derived quantities can share evidence dependencies. |
| Seismic | PDS station-specific native waveform products for S11/S14/S15/S16, plus the existing S12 archive statistic | Different epochs, short samples and raw counts do not supply response-qualified structural demand. Apollo 17 still has a borrowed reference. |
| Other shared reference quantities | Declared CRaTER, LDEX, LADEE and spacecraft-potential references | Repeating a reference in six rows does not produce six independent historic site measurements. |

Gate applicability is reviewed separately from data completeness. The raw seismic cutoff is disabled globally because [Dar053 SE-H01](../data/processed/analysis/subject_seismic/20261110T183033924956Z_ba610a/stage4_seismic_proposals.csv) requires qualified local demand, response and applicable structural tolerance. [PDS archive documentation](https://pds-geosciences.wustl.edu/lunar/urn-nasa-pds-apollo_pse/readme.txt) and [StationXML](https://pds-geosciences.wustl.edu/lunar/urn-nasa-pds-apollo_pse/data/xa/metadata/) describe source modes/timing/response; the archive supplies no adopted universal 15-count failure threshold. The stored gate can be re-enabled explicitly, but is not qualified merely by doing so. Other existing test thresholds are retained, not newly validated as NASA requirements.

This is a **traceable evidence/proxy baseline for software calibration**, not six complete measured nine-domain Apollo datasets. Testing the same reference/model assumptions that generated these rows is a consistency check, not independent predictive validation. The remaining shared references, nominal RF assumption and conditional model limitations are deliberately visible rather than concealed by manufactured diversity.
 All Apollo input cells are populated for a nine-domain **proxy/test baseline**. The field-level provenance above distinguishes actual dates/site reference data from borrowed references and assumptions. This is not nine-domain historical validation or proof that the sites meet the configured requirements.

The active `config.yml` policy is **`assumption_NASA_values`**: project assumptions for testing NASA-site scenarios, **not official NASA values or safety limits**. All ten domain definitions retain complete preference bounds and the project domain weights listed below; all ten are currently enabled, with comms, seismic and soil hard gates disabled. The original nine domains each use one score-bearing metric; soil uses four equally weighted, potentially related descriptors as an explicit experimental exception. Other fields are either gate-only or context-only. These fictional mappings must not be used to interpret orbital/reference quantities as local hazard, dose, surface charging or real habitability.

| Domain | Relative weight |
| --- | ---: |
| Radiation | 20 |
| Thermal | 10 |
| Solar illumination | 20 |
| Communications geometry | 15 |
| Dust | 10 |
| Plasma / charging | 5 |
| UV | 5 |
| Seismic | 3 |
| Exosphere | 2 |
| Soil (experimental) | 10 |

Weights are project priorities, not NASA-approved percentages. The aggregate divides by the sum of included weights; they need not total 100. Available-data mode renormalizes around omitted measurements. Change domain-level `multiplier` values in `config.yml`; metric multipliers control weighting within each domain.

| Domain | Test soft preference (utility bounds) | Assumed hard gate |
| --- | --- | --- |
| Radiation | Lower orbital counter median, 24-104.5 counts/SEC record (reference scale) | Counter maximum <=7500 counts/SEC record |
| Thermal | Lower phase-median temperature span, 0-300 K | Lowest phase median >=40 K; highest <=390 K (project surface-model envelope, not component safety) |
| Solar illumination | Higher median Sun visibility, 0-1 | Continuous sunlight >= min(156 h, requested window duration), with `cap_to_window_duration: true` |
| Dust | Signed detector current: outer bounds -1000 to 60000 charges/s; preferred plateau 0-10000 | Current between -1000 and 55000 charges/s |
| Plasma / charging | Spacecraft potential: outer bounds -20 to 15 V; preferred plateau -5 to 5 | Potential between -15 and 10 V |
| UV | Lower FUV irradiance, 0-0.055 W/m2 (project-policy scale) | Irradiance <=0.055 W/m2 |
| Seismic | Lower historical raw RMS, 0.347193913546-24.850591805123 counts (descriptive test scale) | Hard gate disabled globally; stored 15-count cutoff is not an adopted structural criterion |
| Exosphere | Helium abundance: outer bounds 0-20000 P/Cc; preferred plateau 1000-10000 | Abundance <=16000 P/Cc |
| Communications geometry | Higher median Earth visibility, 0-1 | Candidate-window minimum link margin >=0 dB |

Every bound, direction, plateau and gate above is an **assumption for exercising software**, not a NASA-certified environmental response. Equality passes. The sunlight gate requires the supplied UTC pair. The link gate also requires it when that gate is enabled. Final score is the weighted average of the mode-selected included domain scores after enabled gate eligibility is met; otherwise it stays blank. Domain diagnostics can still be shown when final eligibility is blocked.

- Known active-gate failure dominates Unknown. Failed or evaluated Unknown checks prevent final scores/ranks; `Skipped_missing` is not counted as a pass.
- Missing values are never zero-filled. Available-data mode explicitly omits them and renormalizes weights; strict mode does not.
- Higher/lower/target-range preferences normalize measurements; optional utility curves act after normalization.
- Domain scores are weighted metric utilities on 0-100. Final scoring requires mode-selected available domains and enabled gate eligibility.
- `comparison_preference_score` is diagnostic, not an operational approval or replacement for the final score.
- Simple output shows diagnostic domain scores, gate status, `Fail Reason` and the gate-qualified habitability score.

The script remains standalone: Python 3.10+, PyYAML, the selected YAML and one input CSV. It does not read source datasets, preparation scripts, notebooks or provenance sidecars at runtime.
