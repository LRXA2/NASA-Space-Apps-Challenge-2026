# Steps 4-5: existing-data lunar environmental prototype

**Steps 4-5 completed - 9 November 2026 (Singapore).**

**Scope:** Moon only, no CNN integration. Use existing data first. Mission/equipment inputs are optional and do not block the normal comparison. This prototype does not establish operational suitability without applicable evidence; missing operational conclusions remain Unknown.

## Open and run

1. Open [latest results](../Pipeline_Proto/outputs/LATEST_RESULTS.md), then the linked **conditions -> rules -> candidate explanations**.
2. Run [Dar_028](../Pipeline_Proto/Dar_028_environment_pipeline.ipynb) with Run All, or from the repository root:

```powershell
.\.venv\Scripts\python.exe "darrel stuff\Pipeline_Proto\environment_engine.py"
```

Normal use needs no mission profile, equipment file, new download or synthetic fixture. The default synthetic notebook switch remains False.

## Step 4 - define scoped, traceable rules

Source: [environment_rule_register.json](environment_rule_register.json). The engine compiles **22 static scoped entries plus the active policy's five comparison entries** into each real run's `evidence_context/rule_register.csv`. It records IDs, original research IDs, authority, source, applicability, required inputs, consequence, evaluator and limit state. Active comparison values, operators, bounds and weights come from the actual chosen policy, including overrides; they are not silently replaced by defaults.

| Classification | Implemented meaning |
| --- | --- |
| Evidence-use guards | Check units/support, dated thermal quality, phase-versus-response, orbital-versus-dose, reference-point-versus-component, historical applicability and indirect event/resource/soil inference. |
| Conditional requirement families | Thermal, power, communications, radiation, life support, ground/mobility, events/plume/ejecta, dust, charging, resource dependence and contingency return. Mandatory only when applicable to an explicitly assessed operation. No numerical physical limit is adopted here. |
| Historical reference | Apollo observations, prediction deviations and original source redlines; source configuration/page/SHA and lb/Ah are retained. Not modern defaults or present-site operating margins. |
| Planetary baseline | Vacuum, unbreathable exterior and lunar body-level conditions, not site scores or proof that equipment can cope. |
| Exploratory filters/preferences | Existing solar/Earth visibility filters >=0.5, slope q90 <=8 degrees, and equal visibility preference weights. These are existing declared comparison settings, **not NASA operational requirements**. |

Original P1/P2/P3 tags in `environmental_data.csv` remain unchanged. Research priority does not determine a hard/soft classification, weight or permission to ignore a critical hazard.

### What actually executes

Existing candidate-value/unit/support validation and gate-before-score functions remain unchanged. The new evidence-use evaluation produces eight checks from accepted EDA. For example:

- **Dated thermal use: Failed** for this sample: zero strict-quality observations. This rejects using the sample as a qualified mission thermal history, **not the physical site**. Even a positive count alone would remain Unknown for a complete mission history.
- **Orbital-to-local-dose inference: Failed**: counters/flux and study scenarios are not candidate transported crew/electronics dose. No radiation cutoff or site score is invented.
- **Reference-point-to-component history: Failed**: finite 2020 ROI-center target geometry is not a validated component power/contact history.
- **Historical arithmetic: Passed**, while adopting those limits for a new configuration is Failed. Reproducing remaining-minus-redline does not prove current equipment adequacy.
- Catalog-to-local-event-probability and proxy-to-resource/ground-strength promotions are rejected. A high context score cannot turn them into operational passes.

Every evidence-use row is explicitly labelled `evidence_use_NOT_site_safety`; every operational conclusion from those bundled sources remains Unknown. Optional actual-profile checks continue through the existing separate operational models, not through these data-use results.

## Step 5 - working handoff and outputs

The existing engine now consumes the [pinned manifest](../Pipeline_Proto/evidence_rules_manifest.json), verifies source output hashes and adds the [evidence_rules.py](../Pipeline_Proto/evidence_rules.py) explanation layer. The scoped requirement register and Research Notes/CSV/outline are also recorded in provenance. It does not read the raw multi-gigabyte archives again or request more data.

| Evidence | How it is used | What it must not imply |
| --- | --- | --- |
| Dar_033 Apollo resources and contextual rules | Historical prediction/reserve findings with page-level original metadata. | Modern stocks, crew, operating redlines or equipment qualification. |
| Dar_035 dated polar temperature | Explicit zero strict cohort and retained geometry-flag diagnostics. | Qualified mission temperature history, bolometric/equipment response or a safe temperature range. |
| Dar_036 terrain-aware center geometry | Separate seven-reference-point coordinates, scenario summaries and resolution sensitivity. | Measurements for the 21 component footprints, a complete horizon, uninterrupted darkness, power generation or working links. |
| Dar_039 annual radiation, retaining Dar_037/038 lineage | 494 CRaTER dates, 495 GOES-16 dates, explicit date/quality gaps and measured support fraction. | Two complete years, local dose, certified solar events or worst-case protection adequacy. |
| Dar_034 shielding/seismic/impact context | Scenario sensitivity and catalog/detection limitations. | Independent event totals, precise local recurrence, shielding adequacy or essential resource/soil capacity. |

### Actual default comparison

The real-data input remains **21 existing purposively selected components**, not validated base footprints or CNN patch identities. It produces **14 ranked context comparisons**, **seven explained exclusions** and the **top five**. Scores and order are unchanged by the new references. Existing root candidate-product CSVs keep their populated/no-placeholder contract.

The separate nested evidence annex adds:

- `rule_register.csv`: scoped rules and actual policy parameters.
- `evidence_use_checks.csv`: permitted/rejected inference and reasons, not physical site verdicts.
- `evidence_findings.csv`: measured history, thermal/radiation support and reference findings with units/scope.
- `source_catalog.csv`: 17 consumed source tables with run identities, original SHA-256, observed/modelled basis, spatial/time/quantity scope and declared use.
- `explained_context_checks.csv`: actual values/operators/limits/statuses and signed distances from exploratory thresholds. **These are not equipment operating margins.**
- `candidate_inference_limits.csv`: **252 rows**, 12 hazard boundaries for each of 21 components. Context availability does not become a candidate measurement or risk score.
- `sources/`: source tables retaining original columns, scopes, dates, units and N/A values; reference geometry has no candidate ID added.
- `EVIDENCE_DECISIONS.md`: all 21 candidate cards show existing supported measurements, actual filters, score/exclusion reasons and remaining inference limits. A regional reference may be mentioned as available, but its numerical values are not assigned to a component.

The annex intentionally retains Unknown and source N/A values. Filling them to make a clean table would destroy evidence meaning; clean candidate products and reference/uncertainty records are separate outputs.

## Verification and scope boundary

[Verification record](../Pipeline_Proto/outputs/verification/step45/verification.json) is the completion evidence: baseline-versus-new candidate-product checks, unchanged protected tests/policy/operational models, targeted tests, the executed notebook, real CLI modes, source/output hashes and requirement-by-requirement audit. **Passed:** 63 pipeline tests (46 protected tests unchanged plus 17 new), eight executed Dar_028 code cells with zero saved errors, and all nine previous candidate-product CSVs byte-identical to the pre-change real-data baseline. The default run, explicit readiness, evidence-only, audit, policy override, old configuration without the new extension and synthetic mode all executed successfully. Default execution never loads the mission template; explicit readiness remains 21 Unknown with no operational top-k, while the separate synthetic software test retains 2 pass / 6 fail / 2 Unknown.

All 17 new consumed source tables and their copies were checked, along with **49 final-run input hashes and 36 output hashes**. Every former dependency is still consumed; original data/helper/CNN inputs remain unchanged. The comparison policy and operational-model code were not modified. All 21 candidate explanation cards and 252 source-inference boundaries are present; none creates a local dose, new score factor or operational pass.

Final verified default run: `darrel stuff\Pipeline_Proto\outputs\environment_comparison\20261108T224336177881Z_5c960d`. The [completion audit](../Pipeline_Proto/outputs/verification/step45/completion_audit.json) maps each goal requirement to current files, execution and checks.

The full operational path remains opt-in: `--stage3`, `--evidence-only`, `--mission-profile`. Existing synthetic verification is also explicit (`--sample`) and does not load the real-data annex. Known mandatory failure still dominates Unknown; actual operational ranking still requires mandatory checks to pass. Existing custom configurations without `evidence_rules_manifest` keep their previous behavior.

This completes the scoped **lunar conditions -> explained rules -> candidate results** prototype, not a complete mission-safety assessment. Wider workflow Step 6 (engineering/physical validation, complete historical reconstruction and broader sensitivity/independent validation) remains deferred. Targeted implementation checks needed to verify Step 5 are included now. No source data, priority tags, CNN, default equipment configuration or physical safety cutoff was changed.
