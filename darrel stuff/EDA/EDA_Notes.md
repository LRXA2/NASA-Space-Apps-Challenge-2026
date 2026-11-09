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

- **Steps taken:** reused candidate sunlight visibility as a direct-solar exposure-opportunity proxy and checked UV product coverage.
- **Findings:** all 21 candidates have a modelled opportunity indicator, not UV intensity or biological dose. Downloaded northern LAMP samples do not cover our south-polar sites.
- **Inference:** lower opportunity can be a stated preference, but sunlight and UV share the same input and must not be counted twice as independent weights.

## Plasma and charging

- **Steps taken:** reviewed charging mechanisms and input coverage; combined sunlight, shadow and permanent-shadow context with three published charging regimes.
- **Findings:** sunlit, near-terminator and dark/plasma-poor conditions have different concerns. **Lower plasma density or more darkness is not automatically safer.**
- **Limit:** this is reference/proxy analysis, not a candidate surface-potential measurement. Local voltage and discharge risk remain Unknown.

## Temperature and heat

- **Steps taken:** compared Diviner temperature by location, local time and solar phase; checked fixed observation cohorts, terrain relationships and dated-product quality.
- **Findings:** **812 dated query products** across three regions yield **zero strict-quality rows**. Existing phase products provide five complete candidate thermal profiles, but only one passes the current context filters.
- **Inference:** cohort choice changes temperature summaries; no universal terrain correction was established. Phase averages are not instantaneous extremes or equipment temperatures. One supported candidate alone cannot establish a thermal preference winner.

## Sunlight, shadow and communications

- **Steps taken:** compared solar/Earth visibility and modelled terrain horizons for seven regional reference points in two 30-day windows; varied observer height, horizon radius and sampling.
- **Findings:** geometry changes with those assumptions. Zero sampled solar blocking does not guarantee continuous sunlight; average Earth visibility does not establish a working radio link.
- **Limit:** power endurance and communications margins still require applicable time histories and response models.

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
- Current illustrative filters retain **14 candidates and exclude seven**. The science view finds **two non-dominated trade-off options** using radiation geometry, UV opportunity and Earth visibility; the original visibility score remains a baseline.
- Thermal comparison is withheld because only one filter-passing candidate has a complete comparable profile. Plasma is not forced into a lowest-is-safest ranking.
- Mission/equipment inputs remain optional for the demo. Operational suitability stays Unknown without applicable requirements, response evidence and limits; preference benefits cannot compensate for mandatory safety failures.

## Evidence and notebook conventions

[Source register](../research/Research_Notes.md) | [Science/model assumptions](../research/lunar_science_models.json) | [Current results](../Pipeline_Proto/outputs/LATEST_RESULTS.md)

Detailed tables, figures and provenance remain in `../data/processed/analysis/` and the notebooks, especially Dar_033-042. Original notes/results/instructions are archived through `../data/verification/latest_eda_notes_cleanup.txt`. One legacy native-support notebook has an unresolved missing-unit-policy error and is not credited as executed.

**Notebook conventions:** name new notebooks `Dar_0xx_descriptive_name.ipynb`, using the next unused number across Earth and Moon. Keep reference/ported names unchanged. Use `EDA/<planet>/<category>/` only when a category has more than two notebooks; otherwise keep notebooks directly under the planet. Store generated data, figures, manifests and execution/debug artifacts under `darrel stuff/data/`, not beside source notebooks.
