# Environmental feature decisions

**Objective:** evaluate mission operation at a selected Moon site. For the current demonstration, use the standalone measurement-level test fixture and explicitly assumed scoring policy without requiring a mission/equipment configuration. Full operational adequacy requires separate qualification.

The filename is retained as a project guide, not a runtime input. [Sources](research/Research_Notes.md), [analysis methods](EDA/EDA_Notes.md) and [run instructions](env_pipeline/README.md) hold the supporting detail.

## 1. Decision contract

- **Accept:** use only the stated measured/modelled role with its units, support and provenance.
- **Reference-only:** useful context, not local hardware capability or an independent score.
- **Defer:** a necessary input/model has not been established.
- **Reject:** reject the unsupported inference, not the underlying data.
- Required Stage 3 inputs remain important; leaving them optional for a context demo does not make them optional for an operational claim. P1/P2/P3 are research priorities, not mandatory/soft labels.

## 2. Gate and preference separation

The default `assumption_NASA_values` policy defines nine domains with equal test weights in `config.yml`; no terrain score is included. `pipeline_mode: available_data` uses supplied measurements and explicitly renormalizes available weights; `strict` withholds incomplete final assessments. `enabled`, `include_in_score` and `hard_gates_enabled` independently control each domain. Comms currently contributes where supplied, with its hard gate off. These are project assumptions, not NASA safety limits.

Operational assessment requires a declared mission, hardware and applicable requirement inventory. Known active hard-gate failure dominates Unknown; an evaluated Failed/Unknown blocks final scoring. Blank measurements can be explicitly omitted in available-data mode, but skipping them is not an operational pass. Expected synthetic outcomes are test labels, never rule inputs.

## Science-backed preference extension

[Dar_042](EDA/Moon/Stage3_Requirements/Dar_042_lunar_science_indicators.ipynb) reuses the EDA for terrain sky openness, direct-Sun/UV opportunity and fixed-common thermal profiles. The [model contract](research/lunar_science_models.json) records source citations, assumptions and explicit comparison directions. This is a hybrid: infer lower/higher preference only for comparable quantities with a defensible direction, not arbitrary minima/maxima across times, instruments or plasma variables.

The archived prototype uses a sunlight/Earth visibility baseline and a separate **unweighted Pareto view** for geometric primary-radiation sky openness, UV opportunity and Earth visibility. Sunlight/UV share an underlying input and should not receive duplicate independent weights. Thermal preference comparison requires complete comparable cohorts. These research views do not replace the active standalone YAML test mappings.

Published REDMoon scenarios are a common what-if library, never assigned to candidate doses or multiplied by sky openness. Plasma regimes and illumination/PSR context are included, but density/voltage/safety is not inferred monotonically. All applicable radiation/UV/plasma operational requirements remain Unknown without their response and adopted limits. Research references are not NASA-endorsed scoring weights.

## 3. What to recommend

**Time-period extension:** Dar_043 defines source-separated historical year-month/quarter comparisons for radiation, solar UV and spacecraft plasma, retaining valid-day/time, cadence and geometry support. Do not turn historical level orders into safety weights or arrival-window recommendations. Match observation periods before correlations. E14-E16 document those evidence boundaries; temporal handoff preparation is separate from the active CSV-only scorer.

| Evidence | Decision | Permitted algorithm use / withheld inference |
| --- | --- | --- |
| Dar_020: candidate static/phase feature definitions | Accept bounded context | Preserve visibility/terrain support and explainable preferences in the archived research comparison. They are not validated base footprints or whole-component thermal coverage. |
| Dar_012/013/024: missingness, fixed/available cohorts, scale | Accept support; reject full-coverage inference | Preserve source/cohort/counts. No reward merely for having data. |
| Dar_023/025/030: terrain-conditioned thermal comparisons | Accept diagnostics | No universal thermal correction or correlation-derived weight. |
| Dar_032 and reused terrain notebook 13 | Accept separate strict/context support | Do not silently replace existing features; missing elevation is not a permanently shadowed region. |
| Dar_030/036: dated solar/Earth reference geometry and finite terrain horizons | Reference-only | Region-center/window sensitivity, not component generation, storage adequacy or a working communications link. |
| Dar_035/040: dated Diviner channel records | Accept qualified observations; flagged values diagnostic only | Channel brightness is not bolometric/component temperature. No mission history or equipment thermal pass without applicable coverage and response. |
| Dar_005/034/037-039: orbital radiation and shielding cases | Reference-only | Preserve instrument/state/energy/direction, gaps and shielding assumptions. No conversion of counters/flux directly to crew dose or invented safety cutoff. |
| Dar_015/031: battery cycling and BVAD nominal rates | Reference-only | Protocol-specific degradation and explicit crew-duration sensitivity; no automatic mission battery, recycling, load or reserve. |
| Dar_016: Apollo soil mechanics | Reference-only | Preserve test geometry and locality; no south-polar bearing/traction certification. |
| Dar_033: Apollo EVA and LM resources | Reference-only | Planned/actual/resource-redline comparisons in original lb/Ah. Ah is not Wh; historical margins are not current equipment margins. |
| Dar_007/008/034: seismic/impact catalogs | Reference-only | No local recurrence probability without effort, independence, event date and vulnerability evidence. |
| Dar_026/027: ShadowCam/Mini-RF | Context only | Darkness/backscatter is not ice quantity, extractability, soil strength or safety. |
| Dust, plasma, chemistry, exosphere and habitat factors | Retain applicable context; defer response | Orbital exposure is not internal contamination, wear, discharge rate or crew atmosphere. |
| Mission activities, actual hardware/stocks/loads/reserves and applicable limits | Defer operational conclusions | Optional input contract; absent fields stay Unknown. No invented defaults. |

## 4. Rule traceability

[environment_rule_register.json](research/environment_rule_register.json) records the research rule families, applicability and consequences. [The pipeline guide](env_pipeline/README.md) explains the active assumption policy, modes and toggles; the [archived prototype guide](env_pipeline/legacy_1/README.md) describes its separate evidence annex. The active script does not read the research register or this document. Failed evidence-use checks reject an unsupported inference, not necessarily the physical site.

New downloads must pass source/schema/quality/support review before becoming evidence. More files alone never justify a new score factor, physical threshold or operational pass.
