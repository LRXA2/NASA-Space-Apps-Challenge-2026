# Moon Environmental EDA

**Purpose:** understand lunar conditions and compare candidate sites using observations, modelled indicators and reference studies. This is environmental evidence, not proof that a mission can operate safely.

## Scope and coverage

- Moon-focused analysis across seven study regions and 21 exploratory candidate components. Earth experiments are supporting references only.
- Quality flags, missing dates, spatial support and observation cohorts are checked before comparison. Missing evidence stays **Unknown**, not zero risk.

## Radiation

- **Steps taken:** checked CRaTER instrument states, GOES quality flags, dates and separate detector/energy/platform/version groups; reviewed shielding scenarios and derived a terrain sky-openness indicator.
- **Findings:** CRaTER covers **1,091 dates / 94.1 million records** with five missing dates. GOES-16/19 cover **524/791 dates**, but only **10.48%/10.82%** of channel/time bins meet the strict filter. Primary data uses 660,000 sampled records from 33 sparse monthly files, not a complete event census.
- **Inference:** sky openness supports relative geometric comparisons. Orbital counts and the 96 published reference scenarios are **not candidate crew doses**; more shielding is not universally safer.

## UV

- **Steps taken:** retained the candidate sunlight/UV-opportunity proxy; parsed downloaded SOLSTICE FUV/MUV daily spectra, accepting only complete 1-nm bands with quality=0 and finite nonnegative irradiance/uncertainty.
- **Findings:** the **2003-05-14 to 2020-02-25** solar-reference record contains **5,700 FUV / 5,760 MUV valid daily band integrals**. This is time-varying solar irradiance, not terrain-adjusted intensity or biological dose at our 21 candidates. Northern LAMP samples still do not cover those south-polar sites.
- **Inference:** lower opportunity can be a stated preference, but sunlight and UV share the same input and must not be counted twice as independent weights.

## Plasma and charging

- **Steps taken:** retained three published charging regimes; read **36 ARTEMIS THB CDF files / 319,946 records**, masking publisher fill/out-of-range values and preserving spacecraft SSE-x/radius strata and measured cadence.
- **Findings:** observations span **2023-10-01 to 2026-09-29**. File-level median timestamp spacings range from **137.571 to 550.738 seconds**, unlike the nominal 96/384-second metadata description. Record counts therefore do not establish elapsed valid-time coverage. **Lower plasma density or more darkness is not automatically safer.**
- **Limit:** these are spacecraft plasma/field observations, not candidate surface-potential measurements. Geometry strata are not certified plasma regimes; local voltage and discharge risk remain Unknown.

## Temperature and heat

- **Steps taken:** compared Diviner temperature by location, local time and solar phase; checked fixed observation cohorts, terrain relationships and dated-product quality.
- **Findings:** **812 dated query products** across three regions yield **zero strict-quality rows**. Existing phase products provide five complete candidate thermal profiles, but only one passes the current context filters.
- **Inference:** cohort choice changes temperature summaries; no universal terrain correction was established. Phase averages are not instantaneous extremes or equipment temperatures. One supported candidate alone cannot establish a thermal preference winner.

## Sunlight, shadow and communications

- **Steps taken:** compared solar/Earth visibility and modelled terrain horizons for seven regional reference points in two 30-day windows; varied observer height, horizon radius and sampling.
- **Findings:** geometry changes with those assumptions. Zero sampled solar blocking does not guarantee continuous sunlight; average Earth visibility does not establish a working radio link.
- **Limit:** power endurance and communications margins still require applicable time histories and response models.

## Monthly and quarterly comparisons — Dar_043

- **Steps taken:** [executed Dar_043](Moon/Stage3_Requirements/Dar_043_temporal_environment.ipynb) using existing CRaTER/GOES daily summaries and downloaded UV/plasma files. Built **101 separate series, 2,352 year-month rows and 856 calendar-quarter rows**, with 18 level/coverage/daily-peak plots. Quarters are recomputed from days, not averaged monthly medians; years, channels, versions, UV modes and plasma geometry strata are not pooled.
- **Results:** in 2025, CRaTER monthly medians of daily GOOD-counter medians range **24–27 counts/SEC record**; all-position ARTEMIS monthly medians of daily ion-density medians range **2.27–4.115 ions/cm³**. In 2019, FUV monthly medians of daily band integrals range **0.0219186–0.0222434 W/m²**. These examples have different coverage and do not establish a repeating seasonal pattern or safest month. Tables retain each period's valid days, samples and, for GOES only, qualified seconds.
- **Limits:** historical UV does **not overlap** recent plasma/radiation. No simultaneous correlation or future forecast is inferred. Calendar quarters are **not lunar seasons**; missing/flagged periods stay missing, and daily maxima remain available because monthly medians can conceal short peaks. Existing illumination windows and flagged dated thermal records were not stretched into annual histories.
- **Handoff:** Step 4 adds E14–E16 temporal evidence guards; Step 5 exports seven checked tables and a historical time-context report without new candidate scores or operational passes. [Accepted run and verification](../data/verification/latest_temporal_environment.txt).

Run again from the repository root: `.venv/Scripts/python.exe "darrel stuff/EDA/Moon/Stage3_Requirements/stage3_temporal_eda.py"` (or run the notebook). `--sample` is bounded validation, not the full analysis. The CDF reader dependency is pinned as `cdflib==1.3.6` in `../requirements.txt`.

## Terrain and data quality

- **Steps taken:** checked DEM/crop alignment, source uncertainty, spatial scale, coverage and temperature associations.
- **Findings:** 28 source/crop checks at 1,792 positions agreed within the stated tolerance. Missing elevation is not permanent shadow; associations change with scale. Thermal-center association does not establish whole-footprint coverage.

## Seismic activity and impacts

- **Steps taken:** reviewed related Apollo seismic catalogs and selected new-crater detections, including event independence and observation coverage.
- **Findings:** the 58/59 catalog entries are related, not 117 independent events. The 222 selected crater detections do not establish local mission-window impact probabilities.

## Dust, resources and imagery

- **Steps taken:** reviewed dust/chemistry evidence coverage and environmental image/radar context.
- **Findings:** ShadowCam covers 3/21 examples and Mini-RF 19/21. Darkness, radar backscatter and spectral indicators do not prove recoverable ice, soil strength or safety. Candidate-specific dust contamination and equipment degradation remain unqualified.

## Equipment and past missions

- **Steps taken:** compared Apollo resource predictions with actual usage; analysed laboratory batteries, Apollo soil tests and nominal crew-load sensitivities.
- **Findings:** **16/18 Apollo 17 resource consumptions exceeded predictions**. Rounded oxygen headroom reaches zero, reinforcing the need for contingency analysis. Battery protocols and six historical soil tests are references, not qualification of our lunar equipment. Crew-rate sensitivities are not actual stocks or life-support adequacy.

## Final results and findings

- The EDA supports **relative environmental comparisons**, not an absolute safest-site claim.
- Monthly/quarterly radiation, UV and spacecraft plasma contrasts are now measured with explicit coverage; they are historical context, not local exposure or a calendar-based safe-arrival recommendation.
- Current illustrative filters retain **14 candidates and exclude seven**. The science view finds **two non-dominated trade-off options** using radiation geometry, UV opportunity and Earth visibility; the original visibility score remains a baseline.
- Thermal comparison is withheld because only one filter-passing candidate has a complete comparable profile. Plasma is not forced into a lowest-is-safest ranking.
- Mission/equipment inputs remain optional for the demo. Operational suitability stays Unknown without applicable requirements, response evidence and limits; preference benefits cannot compensate for mandatory safety failures.

## Evidence and notebook conventions

[Source register](../research/Research_Notes.md) | [Science/model assumptions](../research/lunar_science_models.json) | [Current results](../Pipeline_Proto/outputs/LATEST_RESULTS.md)

Detailed tables, figures and provenance remain in `../data/processed/analysis/` and the notebooks, especially Dar_033-043. Original notes/results/instructions are archived through `../data/verification/latest_eda_notes_cleanup.txt`.

**Notebook conventions:** name new notebooks `Dar_0xx_descriptive_name.ipynb`, using the next unused number across Earth and Moon. Keep reference/ported names unchanged. Use `EDA/<planet>/<category>/` only when a category has more than two notebooks; otherwise keep notebooks directly under the planet. Store generated data, figures, manifests and execution/debug artifacts under `darrel stuff/data/`, not beside source notebooks.

### Python helper locations

| Folder (relative to `EDA/`) | Purpose |
| --- | --- |
| [shared/](shared/) | Reusable readers, provenance, terrain/site utilities, reference experiments and decision helpers. |
| [Moon/Stage3_Requirements/](Moon/Stage3_Requirements/) | Stage 3 analysis scripts and their seven JSON configs. |

Existing import names are preserved. Only helper/config locations and necessary search paths/file references changed; no new package structure was introduced. Notebook locations, data paths and analysis methods are unchanged. Restart open notebook kernels before using the updated paths.
