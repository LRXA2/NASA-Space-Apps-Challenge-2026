# Moon environmental pipeline

**Single active configuration: `config.yml` (`south_pole_environment_comparison`).** One input CSV produces separate Operations and Survival-conditions scores. The YAML controls reference ranges, flow weights and independent assessment toggles.

## One input CSV

Open and edit **[inputs/sites.csv](inputs/sites.csv)**. This is the single main pipeline input: 83 rows (**17 Artemis-region-labelled, 6 fully populated Apollo-labelled baseline scenarios, 30 synthetic and 30 dummy**) containing `id`, optional UTC window columns and the original measurement columns, including `median_visible_sky_fraction` and `median_earth_visibility_fraction`.

Most measurement cells are populated in the original 77 fixtures, including four intentional dummy blanks. The six Apollo-labelled baseline rows are fully populated, using the measured references, conditional models and explicit test assumptions documented below. The 77 non-Apollo fixtures use fictional eight-day requested windows spread across 2000-2026; synthetic neighbours share their EDA baseline windows; Apollo rows instead use historical landing-to-ascent UTC windows. Non-Apollo windows are test scenario dates, not the observation dates of their borrowed or randomized measurements; changing those dates does not reconstruct historical site conditions. The original seven EDA-labelled baselines and all synthetic scenarios use equally sized 1.2 km patches and the same map statistics. The ten additional EDA-labelled scenarios have assumed values, including geometry, without a measured footprint. These are controlled software fixtures, not verified NASA site assessments; static maps are not filtered to that future window. NASA labels identify a declared region, not a NASA-selected exact patch or approval of the assumed conditions.

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
| `window_continuous_sunlight_hours` | **Conditional flat-horizon estimate:** [NASA HLS-PAP-039, section 3.6](https://ntrs.nasa.gov/api/citations/20230014980/downloads/HLS-PAP-039%20HLS%20White%20Paper%20Non-Design.pdf) gives morning landings, ascent before noon and positive geometric solar elevations across the crew stays. With the explicitly assumed unobstructed local horizon, estimate the daylit run *inside the supplied window* as `(stop_utc - start_utc)/3600`. This is censored at both mission boundaries and is not the site's maximum attainable sunlight run, not a measured power-supply duration and not proof against local terrain/hardware occlusion. Values range from approximately 21.6 to 75.0 h. The active comparison retains this as context and has no universal sunlight-duration gate; no dates or measurements are extended to improve an assessment. |
| Three phase-median thermal columns | **Mission-window thermal MODEL cohort, not observed Diviner phases:** use 17 equally spaced instants including landing and ascent. Each instant represents the spatial median of the same uniform flat reference patch. With JPL Sun elevation `e_k` and local albedo `A` from [NASA HLS-PAP-039 Rev A, table 3.6-1](https://ntrs.nasa.gov/api/citations/20230014980/downloads/HLS-PAP-039%20HLS%20White%20Paper%20Non-Design.pdf), calculate `T_k = [104^4 + (390^4 - 104^4) * (1-A) * max(0,sin(e_k))]^(1/4)` K (convert degrees to radians). Supply minimum/maximum/difference across these 17 modeled spatial medians. **Model assumptions:** the existing 390 K dark-equatorial upper anchor, 104 K floor and approximate optical-albedo-as-solar-reflectance treatment are retained. NASA generic temperature endpoints do not validate this response law. No conduction, thermal inertia, emissivity calibration, self-heating, real footprint or propagated uncertainty is included. Apollo uses a mission-window cohort; this is not a measured temperature history or a component operating limit. |
| Radiation counters, spacecraft potential, LDEX current and NMS orbital helium | **Shared measured reference proxies**, not reconstructed Apollo conditions. No defensible mission/site-specific replacement was established for these instrument-specific quantities. Their repeated values are intentional reference assumptions and must not be counted as six independent historical observations. |
| FUV irradiance | Use each mission's **NRLSSI2 historical reconstruction** from [LASP LISIRD](https://lasp.colorado.edu/lisird/data/nrl2_files/). Integrate all 65 complete 1-nm bins centred 115.5-179.5 nm, then take the median of the supported UTC daily band integrals whose dates overlap landing through ascent. Results are modeled daily 1-AU references, not Apollo instrument measurements or subdaily/local surface dose. Whole UTC days include portions outside the precise crew window. They are not cross-calibrated here against the modern SEE fixture cohort. |
| Spacecraft ion/electron density | Where available, use [NASA OMNI](https://omniweb.gsfc.nasa.gov/html/ow_data.html) **near-Earth upstream proxies** during fully contained mission hours, not lunar surface or P1 ESA observations. Mask proton fill `999.9`, reject nonpositive/nonfinite density and missing spacecraft ID. With valid alpha/proton ratio `r`, estimate ion density `n_p*(1+r)` and electron density `n_p*(1+2*r)`; without alpha support, approximate both as proton density (H-only quasi-neutral model). Medians use supported hours only; coverage is incomplete, especially Apollo 11. These are conditional density proxies, not an ESD/surface-charging model. |
| `window_minimum_link_margin_db` | **Explicit TEST ASSUMPTION:** nominal `0 dB`, because no qualified historical minimum RF-margin series has been reconstructed. This is not derived from received power in dBm or Earth visibility. The comms gate remains disabled by the existing config; do not treat the placeholder as engineering evidence if enabling it. |

Earth-clearance geometry uses [JPL Horizons](https://ssd-api.jpl.nasa.gov/doc/horizons.html) airless apparent target-centre elevation and angular diameter at the actual landing coordinates and historical UTC windows. Full-disc clearance is `elevation_deg - angular_diameter_arcsec / 7200`. It supports only the stated unobstructed-horizon mission-window model, not local terrain clearance, actual DSN contact or an RF margin.

These are **fully populated baseline scenarios, not a fully measured Apollo dataset**. Numeric completeness does not establish historical accuracy. The approximate map geometry, modern reference epochs and modeled mission-window thermal cohort are not like-for-like measured support. They supply the retained environmental proxies for the two comparison scores. The 390 K value is a surface-model anchor, not an active temperature gate. Historical NASA site selection is a positive calibration reference for intended operations, not a proof that these proxy rows are measured historical truth. This project envelope is not a component qualification limit or NASA-certified safety threshold, and there is no ID-based Apollo exemption.


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

These small native-count samples are not directly comparable calibrated hazard levels. Instrument response, heating, archive clock support, telemetry gaps and ADC-endpoint samples can affect the statistic. StationXML assigns the same nominal peaked-mode sensitivity to the selected location-00/MHZ channels (3,579,160,000 counts per metre); this is NOT evidence that their nominal gains differ. Equal nominal response does not make these short raw-count samples a qualified structural demand or provide an adopted 15-count site-failure limit. In particular, S11's middle sample has substantial gaps. Preserve these limitations rather than treating a high count RMS as proof of an unsuitable site. The active comparison has no 15-count hard gate or seismic score. Seismic inputs remain context only for **every row**. No source value is reduced and no Apollo ID is exempted. Apollo 12 retains its broader, different historical cohort, so this is not a controlled cross-station experiment. The config's legacy S12 evidence-family label is a software grouping identifier, not sufficient row-level station provenance; use the actual station/source references here.

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

The [approximately 29.5-day phase cycle](https://science.nasa.gov/moon/moon-phases/) supports the regional 354 h half-cycle only as an idealized reference; it must not be described as a measured longest shadow run. Mission dates retain the temporal support of the scenario and are required if a window-dependent gate is explicitly configured; they are intentionally retained.

Local primary-report sources under `D:/projects/NASA Dataset/keep/` (physical PDF page numbers, not printed section-page numbers):

- `A16_MissionReport.pdf`, pp. 28-31: central-station thermal-plate temperatures, abnormal seismic-instrument heating, received signal power and failed heat-flow deployment. Hardware temperatures are not phase-median ground temperatures; received power in dBm is not available-minus-required link margin in dB. Activity/impact seismic descriptions do not establish the configured daily RMS statistic.
- `Apollo_17_Postflight_Mission_Report_19730015117.pdf`, pp. 37-38, 40-44 and 76: station thermal management, heat-flow deployment, mass-spectrometer activation/background, ejecta detection, gravimetry, radiation-detector context and soil observations. A probe reading near insertion, internal component heating, particle-track counts or local surface mass spectroscopy cannot replace phase medians, CRaTER SEC counters, LDEX current or NMS orbital helium.
- `a17_final-flight-mission-rules_19720068065.pdf`, pp. 33 and 51: historical EVA/communications contingencies depend on crew activity, configuration and recovery options. They do not provide a footprint visibility fraction or numeric minimum RF margin.

These references have the quantity and instrument limitations described above. OCR can be imperfect; ambiguous figure or text values must not be treated as precise measurements.

There is no separate domain-score input CSV. Domain scores are calculated by the pipeline; do not enter scores in place of physical measurements.

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
python "darrel stuff/env_pipeline/env_pipeline.py" --output "darrel stuff/env_pipeline/outputs/results.csv" --overwrite
```

`inputs/sites.csv` remains the single default input. `--input` selects one replacement CSV. No input values, headers, IDs or dates are changed by scoring. Every row runs through both Operations and Survival. Each flow has one weight map in `assessments.<flow>.weights`; there is no crewed/uncrewed selector or `--profile` option. Both scores remain experimental comparisons, not qualified crew/equipment survival assessments.

`--detailed` adds each assessment's measurement utilities, omitted inputs, domain contributions, gate details and configuration hash in JSON cells. `--compact` is the default. Output files are protected unless `--overwrite` is supplied. The script needs Python 3.10+ and PyYAML; it does not import the EDA or legacy files at runtime.

## Simple output

One row per input site, in one CSV:

```text
ID,
operations_solar_illumination_score, operations_dust_score,
operations_communications_geometry_score, operations_soil_score,
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
| Solar illumination | 40% | - |
| Communications geometry | 35% | - |
| Dust reference | 15% | - |
| Soil reference | 10% | - |
| Radiation proxy | - | 40% |
| Thermal variation | - | 35% |
| Plasma-charging proxy | - | 15% |
| UV proxy | - | 10% |
| **Total** | **100%** | **100%** |

Seismic and exosphere remain context only and contribute to neither total. A dash means unallocated, not a zero-valued measurement. Both flows process every input row; no input or hidden setting labels it crewed or uncrewed.

Operations weights emphasize solar-power opportunities and direct-Earth visibility, with smaller experimental dust/soil-reference contributions. Survival weights emphasize radiation and thermal conditions, with charging and UV contributions. These are **project priorities**, not NASA-issued percentages or demonstrated equipment/crew survival limits. Each flow totals 100, but only relative multipliers matter. Available-data mode renormalizes the weights when contributions are missing or disabled.

Edit the two independent maps in the single `config.yml`:

```yaml
assessments:
  operations:
    weights:
      solar_illumination: 40
      communications_geometry: 35
      dust: 15
      soil: 10
  survival:
    weights:
      radiation: 40
      thermal: 35
      plasma_charging: 15
      uv: 10
```

Retain each flow's `domain_overrides` and `metric_overrides` when editing. Omitting a domain from a flow's weight map removes its score and gates there. Shared metric definitions live under `domains`. Overlap is supported but not enabled by default; allocate a domain to both maps and use `assessments.<flow>.metric_overrides` for genuinely different rules. Do not duplicate a proxy merely to increase its influence.

## Reference ranges and input roles

Numbers below are **scoring scales or data-validity bounds**, not certified mission operating/survival limits. Reference scales use actual source EDA, never the sample CSV distribution. Source paths, series, counts and SHA256 pins for the orbital references are recorded as comments in `config.yml`; the numbers are frozen at runtime.

| Input field(s) | Operations use | Survival use | Numeric basis / interpretation |
| --- | --- | --- | --- |
| `median_sun_visibility_fraction` | Higher preference | Not included | 0-1 maps to 0-100; the direction favours solar-power opportunity, not actual generated energy. |
| `median_earth_visibility_fraction` | Higher preference | Not included | 0-1 maps to 0-100; geometry is not an RF link or relay assessment. |
| `historical_median_dust_detector_current_charges_per_second` | Continuous reference resemblance | Not included | 100 only at the observed median, 38,230 elementary charges/s. Declines linearly to zero at p05=14,332.5 and p95=100,711.25; values beyond these anchors remain zero. Dar_048 LDEX_CURRENT, 166 daily medians. These anchors describe reference distance, not harmful-current limits. Signed current is not local deposition, abrasion or maintenance demand; preferring resemblance to the median is an experimental project assumption. |
| `soil_mean_grain_size_um` | Reference-band resemblance | Not included | 100 at 53.01-91.5975 um; zero at 14.4225 and 130.185. |
| `soil_maturity_is_feo` | Reference-band resemblance | Not included | 100 at 42.6225-72.47 Is/FeO; zero at 12.775 and 102.3175. |
| `soil_agglutinates_percent` | Reference-band resemblance | Not included | 100 at 35.351-40.058%; zero at 30.644 and 44.765%. Preserve source modal basis. |
| `soil_feo_wt_percent` | Reference-band resemblance | Not included | 100 at 6.4375-15.71 wt%; zero at -2.835 and 24.9825. Negative scoring anchors are extrapolated coordinates, not valid chemical measurements; input must be 0-100 wt%. |
| `orbital_radiation_counter_median` | Not included | Lower proxy preference | 24-104.5 counts/SEC maps to 100-0. Dar_049 selected-state CRaTER daily medians, n=1,091, p05/p95. Not crew dose or electronics radiation tolerance. |
| `phase_median_temperature_range_kelvin` | Not included | Lower variation preference | 0-300 K span maps to 100-0. Retained project comparison scale, not a fitted hardware limit. NASA/Diviner's roughly 400 K equatorial day versus below 100 K night illustrates the contrast; it does not define a south-polar safe interval. |
| `median_spacecraft_electric_potential_volts` | Not included | Zero-centred proxy preference | 100 at 0 V; declines linearly to zero at +/-32.918969440460 V. Scale is Dar_046 p95(abs(daily median)), selected ESA_v01_thb_peif_sc_pot series, n=1,140. Choosing zero as preferred is a project assumption, not an arcing threshold or surface-voltage inference. |
| `median_solar_far_uv_irradiance_w_m2` | Not included | Lower proxy preference | 0.021529459636-0.026638514010 W/m2 maps to 100-0. Dar_045 SEE_v012_FUV_115_180 daily band integrals, n=1,206, p05/p95. Not surface dose or a material/crew exposure limit. |
| `lowest_phase_median_temperature_kelvin`, `highest_phase_median_temperature_kelvin` | Context | Context | Nonnegative K. No universal 40/390 K gate: surface temperature is not component temperature. |
| `orbital_radiation_counter_maximum` | Context | Context | Nonnegative native counts. No universal 7,500-count gate. |
| `median_spacecraft_ion_density_per_cm3`, `median_spacecraft_electron_density_per_cm3` | Context | Context | Nonnegative native density; no universal preferred/safe density interval. |
| `median_visible_sky_fraction`, `permanently_shadowed_cell_fraction`, `regional_reference_sun_visibility_fraction` | Context | Context | Fractions 0-1. Sky openness is not radiation dose; shadow fraction is not energy autonomy. |
| `regional_reference_longest_shadow_sample_span_hours`, `window_continuous_sunlight_hours` | Context | Context | Nonnegative hours. Regional sampled shadow and mission-window sunlight are different quantities; neither is a battery requirement. No universal 156-hour sunlight gate. |
| `window_minimum_link_margin_db` | Context unless an applicable gate is configured | Context | Signed dB. Zero is the zero-margin boundary by definition, not a universal required engineering reserve. No default gate. |
| `historical_median_vertical_seismic_rms_counts` | Context only | Context only | Nonnegative native counts, not response-qualified candidate-site structural demand. |
| `historical_median_orbital_helium_density_per_cm3` | Context only | Context only | Nonnegative native density; no demonstrated habitability or survival threshold. |

Dust has no flat 100-point interval. A zero dust score means outside the selected central reference interval, not a failed physical safety requirement; negative background-subtracted values must not be reinterpreted as negative dust burden. Shared Apollo inputs equal to the reference median still legitimately receive the same 100-point resemblance score. No input, weight, gate or other domain rule is changed by this definition.

All four soil metrics have multiplier 1; a complete soil score is their arithmetic mean. Their preferred bands are p05/p95 of rounded Apollo mission means from Dar_057. Scores fall to zero one band-width outside, with physical percentage validation retained. This is reference resemblance, not mechanical stability. Apollo mission means are historical-reference controls; missing Apollo 11/12/15 agglutinates retain the declared cross-mission estimate. Randomized EDA/synthetic/dummy inputs remain scenarios, not observations. Differences in mission window, method, epoch and support prevent interpreting these totals as like-for-like deployment certification.

## Evidence supporting the configuration

- [NASA LOLA polar illumination products](https://pgda.gsfc.nasa.gov/products/69) supply long-period Sun/Earth geometry, and warn that shorter periods and radio-link geometry require further analysis. They do not prescribe visibility pass percentages.
- [NASA Lunar Surface Data Book, section 6.3 and Appendix E](https://ntrs.nasa.gov/api/citations/20230007818/downloads/ACD-50044%20Lunar%20Surface%20Data%20Book%20Rev%20A.pdf) discusses approximately 150 hours of darkness for particular south-polar cases. That is a scenario demand, not a universal capability requirement or permission to equate regional sampled shadows to battery autonomy.
- [NASA's published VIPER operations description](https://science.nasa.gov/mission/viper/lunar-operations/) describes a 50-hour continuous-darkness limit for that rover concept. It must not be transplanted to every base or Apollo scenario.
- [NASA NESC lunar environment study, section 7.4](https://ntrs.nasa.gov/api/citations/20220017053/downloads/20220017053.pdf) describes surface conditions from roughly 18 K to above 400 K and thermal-control challenges. These environmental conditions are not system operating/survival limits. [Diviner thermal observations](https://www.diviner.ucla.edu/science) provide equatorial reference context for the retained span scale.
- [NASA/PDS LDEX documentation](https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/LADEE/ldex.html) identifies an orbital impact-ionization/current measurement, not a direct surface-wear criterion.
- [NASA cis-lunar charging study](https://ntrs.nasa.gov/api/citations/20200001582/downloads/20200001582.pdf) distinguishes spacecraft and lunar-surface potentials. This prevents interpreting the current input as surface discharge risk.
- [NASA crew-health standards](https://www.nasa.gov/ochmo/human-spaceflight-and-aviation-standards/) and [radiation guidance](https://srag.jsc.nasa.gov/SpaceRadiation/FAQ/FAQ.cfm) address applicable crew requirements and dose quantities. Raw instrument counters are not interchangeable with those quantities; these scores do not model crew protection or life support.

Where a compatible threshold cannot be established, it is explicitly absent. No source here supplies this project's weight percentages. These references support the measurement meanings, reference environments and limitations, not every assumed scoring direction.

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
      communications_geometry:
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
