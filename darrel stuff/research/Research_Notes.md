# Moon Research Notes

**Purpose:** identify the evidence available for our Moon environmental assessment, what it can support and what remains unresolved. Measured findings belong in [EDA Notes](../EDA/EDA_Notes.md); algorithm choices belong in [Feature decisions](../purposal.md).

[Source register](environmental_data.csv) | [Outline coverage](outline_environment_crosswalk.csv) | [Downloads](../download_script/Download_Dataset_Instructions.md) | [Pipeline](../Pipeline_Proto/README.md)

## Files in this folder

| File | Purpose |
| --- | --- |
| [environmental_data.csv](environmental_data.csv) | Source register: datasets, fields, priorities and limitations. |
| [outline_environment_crosswalk.csv](outline_environment_crosswalk.csv) | Moon-relevant outline factors and evidence gaps. |
| [environment_rule_register.json](environment_rule_register.json) | Step 4 requirements, evidence guards and permitted uses. |
| [lunar_science_models.json](lunar_science_models.json) | Science sources, proxy definitions and preference-view settings. |

This is already a dedicated research folder; its file paths are kept stable. The local spreadsheet backup remains covered by [../.gitignore](../.gitignore).

## Source coverage

- **Register:** 53 entries: 38 external D-sources, 14 project M-inputs and C01 planetary baseline. It records official links, fields, joins, feasible analysis dimensions and review dates. Blank fields mean unreviewed, not absent data.
- **Core collection:** Diviner polar phase, LOLA/SDEM terrain and visibility products; Earth analog/climate collections are reference-only. Use D01-D06 lunar applicability first. New small pilots do not replace established core data.
- **Bounded Dar_029 snapshot:** 32 public D-source selections present; D21-D24 access-gated; D17/D25 unselected; 14 M-inputs absent; C01 available. Zero selected missing/size-mismatched files is not a whole-archive checksum claim.

Availability comes from frozen manifests and receipts, not a live tracker. Register statuses are historical, not a current download audit. D21-D24 remain pending authorised archive access; no bypass or substitute science files are assumed.

## Environmental research areas

The table groups related evidence without changing the CSV's original priorities or source membership.

| Category | P tag | Register references | Research use | Important limit |
| --- | --- | --- | --- | --- |
| Temperature & Thermal | P1 | P1: D01, D04, D20, D21, D28, D38, M01 | Surface/phase/local-time and depth contrasts; thermal response and operating margins. | Brightness temperature, subsurface profiles and component temperature are not interchangeable. |
| Radiation | P1, P2 | P1: D07, D08, D31, M06; P2: D09, D29 | Quiet/event contrasts, shielding and applicable exposure margins. | Orbital counts and published shielding cases are not local crew dose. |
| Illumination & Shadows | P1, P2 | P1: D02, D27, M07; P2: D32 | Terrain/shadow and UV context; dated generation, darkness and storage needs. | Static maps and dark-region images are not chronological power or UV-dose histories. |
| Terrain & Surface Properties | P1, P3 | P1: D05, D06, D15, D26, D33, M05; P3: D24, D30, D36, D37 | Native-support/uncertainty checks, terrain joins and tested mobility/foundation response. | Slope, radar and morphology do not certify soil capacity; avoid duplicate terrain penalties. |
| Seismic Activity | P1 | P1: D13, D14, D23 | Event classes, location uncertainty, waveform spectra and duration. | Historical/local records do not establish south-polar recurrence or structural qualification. |
| Resources & Sample Chemistry | P1, P3 | P1: D16, M09; P3: D34 | Spectral/material context and measured release/containment response. | Remote chemistry or one impact experiment does not certify resources or cabin toxicity. |
| Communications & Geometry | P1 | P1: D03, D19, M08 | Visibility, dated geometry, contact/outage and link margins. | Mean visibility and sphere-horizon samples are not terrain-aware working links. |
| Habitat & Human Health | P1, P2 | P1: M02, M10; P2: D17, D18, M11, M12 | Protected atmosphere, supplies/quality, performance, noise and vibration. | External maps and analogs cannot replace internal telemetry or approved requirements. |
| Mission Safety & Reliability | P1 | P1: M04, M13, M14 | Equipment/limit inventory, recovery scenarios and landing/plume/layout response. | Requires mission-specific configuration, applicability and validated models/tests. |
| Planetary Baseline | P1 | P1: C01 | Vacuum, unbreathable exterior and reduced gravity as design conditions. | A baseline is not time-varying EDA or proof that a system is adequate. |
| Dust | P2 | P2: D10, M03 | Exposure/occurrence versus wear, filtration and cooling changes. | Orbital dust is not cabin loading or tested hardware degradation. |
| Plasma & Magnetic Environment | P2, P3 | P2: D11, D22, D25; P3: D12 | Time, geometry, regimes and field contrasts; charging-model needs. | Plasma observations are not discharge rates or ionizing crew dose. |
| Exosphere & Vacuum | P3 | P3: D35 | Sparse exosphere and contamination/operations context. | Not breathable air, atmospheric wind or internal habitat pressure. |

### How to read the priorities

| P tag | Research focus | Register entries |
| --- | --- | --- |
| <a id="tier-1--most-direct-impact-on-mission-feasibility-and-essential-protection"></a> **P1** | Survival/protection research | 34 |
| <a id="tier-2--substantial-but-more-dependent-on-the-activity-or-specific-evidence-gap"></a> **P2** | Long-term health/reliability | 12 |
| <a id="tier-3--indirect-context-alternatives-or-specialised-extensions"></a> **P3** | Supporting context | 7 |

For mixed-priority categories, the register references retain each source's own P tag.

These are **research priorities, not hard/soft gates, algorithm weights or a new impact ranking**. Core-collection selections use a separate scheme. Mission activities determine applicability: a P2/P3 hazard is not automatically safe to ignore, and missing mission/equipment evidence does not become less important because other files are easier to download.

## NASA mission and equipment evidence

### Reviewed material

The extraction batch screened **11 supplied PDFs / 2,903 pages**: 2,295 pages had at least 80 extracted characters; 608 did not. This is text screening, not full manual review. Image-only material includes the 221-page integrated LRV handbook and 176-page press kit. Missing priority PDFs are not assumed available.

**File identity corrections:** `AP7_Prelaunch Mission Operation Report.pdf` is Apollo **17**, not Apollo 7. The file labelled full LRV handbook transcripts contains only a 30-page segment.

The curated extraction retains source/page images, context, holds and provenance in `../data/processed/analysis/mission_equipment_extraction/20261108T205148887009Z_evidence/`:

| Extract | Scope |
| --- | --- |
| Context records | 26 mission/equipment records. |
| EVA percentage remaining | 66 records: 11 Apollo 14-17 EVA tables x two crew x three resources; 65 paired predictions. One missing power prediction stays missing. |
| Primary Apollo 17 suit records | 18 visually checked records: three EVAs x two crew x oxygen/feedwater/battery. |
| LM totals | Eight oxygen/water totals; vehicle and suit resources remain separate. |

### Source evidence and limits

Page numbers below are PDF pages, with printed references in parentheses where available.

| Source / pages | Evidence and applicability |
| --- | --- |
| Apollo 17 prelaunch pp.16-17 (10-11) | Activity/return context, not a universal modern plan. |
| LM10 handbook pp.329/369/380 (2.5-1, 2.6-1, 2.6-16) | Configuration-specific EPS/ECS dependencies. |
| Apollo 16 report p.97 | Rover parking, covers and radiator dust maintenance. |
| Apollo 17 postflight pp.139-141 | Fender repair and temperature indication: operational response evidence. |
| Apollo 17 flight rules p.33 (2-8, item 2-27) | Seven-hour plan, 30-minute post-EVA EMU reserve and conditional five-minute communications provisions. Preserve the LCRU/antenna exception; not a universal cutoff. |
| Same, p.50 (3-15, item 3-64) | Rover 125 F for EVAs 1/2 and 140 F for EVA 3, with management/traverse responses. Temperature alone did not mandate abandoning the rover. |
| Apollo 17 postflight p.144 (9-6, Table 9-II) | Primary suit data; pp.137-138 and 144-145 support LM balances. |

**Interpretation rules:** retain lb/Ah; Ah is not Wh. Preserve the printed predicted descent-water total of 48.1 lb and its discrepancy with the displayed tank sum of 48.2 lb. Initial-minus-consumed balances do not validate a new mission. Reconstructions and primary reports are related evidence, not independent experiments. Further OCR/dense-table extraction is deferred.

## Supporting references and model routes

| Source | Useful for | Boundary |
| --- | --- | --- |
| S01 BVAD Rev2 (2022) | Curated official nominal-rate extract. | Full PDF returned HTTP 403 at recorded acquisition; rates are not actual mission loads. |
| S02 NASA-STD-3001 V2 F; S03 V1 C | Acquired requirements-reference PDFs. | Applicable requirements/limits need explicit adoption. |
| R01 NASA PCoE battery aging | Laboratory cycling/impedance histories. | Protocol-specific, not lunar-vacuum or selected-hardware qualification. |
| R02 Apollo 15 soil mechanics | PDS4 six-test numeric history. | Local, geometry-dependent reference, not polar capacity. |
| DEM + DE421/MOON_ME | Dar_036 finite-terrain scenarios. | Observer configuration, terrain uncertainty, solar disk and energy/link models still needed. |
| Geant4 / OLTARIS | Possible design-specific transport modelling. | Results must be generated/validated; OLTARIS requires approved access. Not ready-made local crew dose. |

## Questions to explore in EDA

Frame each analysis as: **How does [variable] vary with [dimension], within [region/time window], accounting for [coverage and uncertainty]?** Not every dataset supports every dimension.

| Dimension | Check or question |
| --- | --- |
| Time and duration | Dated changes, event duration, sampling and gaps. |
| Location | Coordinates or georeferenced footprints for site comparisons. |
| Elevation and terrain shape | Ridge/depression, slope and aspect; join to a DEM where needed. |
| Local solar time and illumination geometry | Solar position, shadow and rotation-related effects. |
| Depth / measurement altitude | Subsurface depth and spacecraft altitude, each distinct from terrain elevation. |
| Surface properties | Compatible material, geology or rock-abundance maps. |
| Events and environmental regimes | Defined intervals/classes; control instrument changes. |
| Spatial scale | Preserve effective footprint, resolution and aggregation scale. |
| Relationships between variables | Match locations, time support, resolution and reference frames before joining. |
| Variability and extremes | Spread, observed extremes and rates of change; means cannot reconstruct short events. |
| Coverage and uncertainty | Observation counts, flags, errors and missingness before comparisons. |

Calendar date, local solar time, solar phase and event-relative time are different. Cumulative phase-bin averages are not dated time series; static terrain/geology does not supply monthly change.

## Bottom line

- The outline crosswalk covers **27 Moon-relevant factors**, including unresolved evidence boundaries.
- Existing sources support environmental comparisons and historical/reference lessons, not automatic operational approval.
- Mission/equipment inputs remain optional for the demo. Actual suitability still needs applicable configuration, requirements, limits and response evidence; missing mandatory evidence stays **Unknown**.
