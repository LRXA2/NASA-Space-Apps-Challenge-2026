# Lunar Environmental Research
Environmental research and dataset references supporting lunar base site assessment and exploratory data analysis (EDA).

## Research Focus
Priority: **human safety and health**, followed by base operations and vehicle/robot operations.

The research connects environmental factors with their impacts, risks, possible mitigations and datasets for spatial or time-based analysis.

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
