# Purpose

Darrel's environmental research supports selecting a **Moon base location**. Earth data provide supporting analog/training comparisons, not substitutes for lunar conditions.

# Objective

The [project overview](../outline.md#1-project-overview) states that locations are evaluated using environmental conditions, terrain difficulty and available survival/exploration equipment. It also states that similar Earth environments will be identified for astronaut and robotic-system simulations and preparation.

The active scope is **Earth and Moon**. Historical Mars references are excluded.

# Task

Our responsibility is [Stage 3 — Environmental and Equipment Suitability Engine](../outline.md#stage-3--environmental-and-equipment-suitability-engine): supply environmental evidence for documented mandatory checks and explicitly defined preferences. [Stage 4](../outline.md#stage-4--planetary-operational-suitability-assessment) combines assessments for screening and ranking.

Missing applicable evidence remains **Unknown**, not a pass. Power, thermal, communications and protection margins require applicable mission/equipment inputs. Environmental charts alone do not establish operational suitability.

## EDA target and expected outcome

Compare temperature, illumination and Earth visibility **together with terrain**; examine co-location, connected diagnostic zones and location-specific profiles; retain coverage, uncertainty and source evidence. Exact CNN-patch matching is useful but optional. The [algorithm proposal below](#algorithm-proposal) explains planned integration, separate from measured findings.

# Steps

1. Research factors and rank their relevance.
2. Verify sources, fields, coverage and access.
3. Perform focused EDA and record supported findings.
4. Configure applicable hard/soft requirements before engine integration or operational ranking.

# Current Stage

Dar_001–022 have executed on their documented scopes. The work covers core Earth/Moon evidence, all research P1 dispositions, reference experiments, regional/candidate diagnostics and counterfactual hard/soft comparisons. **65 targeted EDA tests pass.** This is not a completed mission engine or final base-location recommendation.

- [Research report](research/Research_Notes.md): impact ranking and evidence gaps across the research CSV, regardless of local availability.
- [EDA notes](EDA/EDA_Notes.md): notebook index, 32-question register, dataset study scope and TODOs.
- [EDA results](EDA/EDA_Results.md): measured findings, accepted runs and verification.
- [Algorithm proposal](#algorithm-proposal): the detailed output-to-algorithm plan in this document.

# Other Datasets

The [core dataset register](Critical_Project_Dataset.md) describes the original core/supporting selections; the [research CSV](research/environmental_data.csv) covers the broader research scope. Their priorities/statuses have different roles and must not be silently equated. Authenticated sources remain KIV. Extend P2/P3 only for a stated question or evidence gap.

# Folder Structure

| Folder | Purpose |
| --- | --- |
| **download_script/** | Acquisition, verification, retry and resume tools; see the [download instructions](download_script/Download_Dataset_Instructions.md). |
| **research/** | Environmental factors, impact ranking, source references and gaps. |
| **data/** | Downloads, receipts and reproducible processing/analysis outputs. |
| **EDA/** | Earth/Moon analysis notebooks, work plan and results. |

All data stays under **`darrel stuff/data/`**, excluded by [`.gitignore`](.gitignore). The downloader creates the directory when needed; retain source labels and receipts for traceability.


## Notebook organisation

Create `EDA/<planet>/<category>/` only when the category has **more than two notebooks**. Smaller categories stay directly under their planet. Notebook names are preserved; shared Python helpers stay in `EDA/` and tests in `EDA/tests/` so existing imports remain valid.

```text
EDA/
├── Earth/
│   ├── Climate/                 # 4 notebooks
│   └── Dar_015_battery_reference_experiments.ipynb
└── Moon/
    ├── Thermal/                 # 4 notebooks
    ├── Terrain_And_Soil/        # 4 notebooks
    ├── Environmental_Context/   # 6 notebooks
    ├── Site_Assessment/         # 6 notebooks
    ├── Dar_005_research_radiation.ipynb
    ├── Dar_007_research_seismic.ipynb
    ├── Dar_008_research_imagery_change.ipynb
    └── Dar_009_research_lcross_spectra.ipynb
```

Data, receipts and generated runs remain in `darrel stuff/data/`. Existing run manifests retain their original source-path history; the reorganisation map is recorded under `data/verification/workspace_reorganisation/`.

---

# Algorithm proposal

**Status:** regional/joint EDA, connected-zone and illustrative candidate profiles, and hard/soft-rule influence diagnostics executed; operational policy adoption and engine integration remain proposed work.

**Date:** 7 November 2026.

**Basis:** the existing terrain CNN prototype, [Stage 3](../outline.md#stage-3--environmental-and-equipment-suitability-engine), and our [executed EDA findings](EDA/EDA_Results.md).

## 1. Overall objective and our contribution

The goal and Stage 3 task are stated above. The proposed contribution is an explainable rule-based environmental layer beside the existing terrain evidence, not another CNN. It will report applicable hard-rule outcomes and, only when eligible, explicitly configured soft preferences. EDA correlations and diagnostic cuts do not become limits or weights by default.

## 2. What the sample CNN pipeline currently implements

| Step | Existing implementation | Meaning |
| --- | --- | --- |
| Configuration | [terrain_dataset.json](../notebooks/modeling/terrain_similarity/terrain_dataset.json), [similarity_experiment.json](../notebooks/modeling/terrain_similarity/similarity_experiment.json) | Explicit regions, source runs, development splits and experiment settings. |
| Dataset preparation | [Notebook 28](../notebooks/modeling/terrain_similarity/28_training_data_readiness_and_baseline.ipynb), `terrain_dataset.py` | 960 m terrain patches, 30 m grid spacing, 32×32 tensors, identity/footprint records and physical descriptors. |
| Deterministic selection/scoring | `terrain_dataset.py`, [terrain_learning.py](../notebooks/modeling/terrain_similarity/terrain_learning.py) | Existing completeness/policy-mask eligibility and physical-descriptor band comparisons provide the implementation pattern for explicit criteria. These are not already a complete mission-specific base-location rule set. |
| Model | [Notebook 29](../notebooks/modeling/terrain_similarity/29_similarity_cnn_experiment.ipynb), [similarity_cnn.py](../notebooks/modeling/terrain_similarity/similarity_cnn.py) | Three channels: **relative elevation, slope and local elevation SD**. A terrain encoder and similarity head produce normalized retrieval vectors. |
| Retrieval | `similarity_experiment.py`, notebooks 34–36 | Cosine similarity retrieves Earth/Moon terrain counterparts. The demo uses consistent rotation/reflection inference for queries and the candidate bank. |
| Evaluation/demo | Notebooks 30–36 | Physical comparisons, sensitivity checks and example retrieval cards. These are development results, not validated base-suitability predictions. |

**Important distinction:** the CNN measures **terrain resemblance**, not whether a lunar base can operate there. Its cosine similarity must not be relabelled as a base-suitability score. A learned terrain-assessment head is not implemented in the current similarity model.

Preserve the existing CNN channels, weights, training scaler, orientation policy and physical baseline. Environmental integration does **not** require retraining or adding environmental image channels to that saved model.

## 3. Does our EDA already combine terrain and environment?

Yes: Dar_002 pairs temperature with native illumination/terrain/quality context; Dar_006 checks bounded terrain support; Dar_012/013 analyse joint support and sensitivity; Dar_017–022 extend this to profiles, connectivity and rule/preference diagnostics. See [the notebook index](EDA/EDA_Notes.md#darrel-notebook-naming-and-current-p1-implementation) for scope and [the results](EDA/EDA_Results.md) for evidence.

These are not the CNN's full relative-elevation/local-SD tensors. Technical containing-pixel joins do not prove physical co-registration or full-footprint coverage. The proposed layer preserves both distinctions.

## 4. Include relevant evidence even without an exact CNN-patch match

**Exact patch matching is useful but optional. It is not a prerequisite for including relevant data.** Keep three evidence roles distinct:

| Evidence role | Examples | How the algorithm may use it |
| --- | --- | --- |
| **Site-associated** | Environmental observations/model fields with verified overlap and applicable spatial/time support. | Inform that site's criteria, retaining coverage, resolution and temporal limitations. Where original CNN footprints are available, associate using their verified bounds/CRS and identity. |
| **Regional or broader context** | Regional thermal/illumination summaries, orbital radiation measurements, historical seismic information. | Inform the relevant regional/domain context and uncertainties. Do not silently copy a regional average into every patch as a measured local condition, or assume an orbital measurement equals surface dose. |
| **Reference experiment / model support** | Dar_015 battery experiments, Dar_016 Apollo soil tests, published radiation scenarios. | Test/calibrate applicable methods and inform rule design. They are not spatial measurements of every candidate or qualification of our selected equipment. |

Retain useful additional datasets in an evidence register even when they cannot produce a site score yet. Record **why they are relevant, where they apply and what is still missing**. More evidence can improve coverage and interpretation; duplicate or correlated records must not generate extra rewards merely because there are more rows.

## 5. Proposed algorithm structure — matching the prototype's workflow

```text
Configuration + pinned source/EDA runs + optional mission/equipment profile
                                  |
                 Site / region / candidate evidence records
                     /                            \
       Existing terrain evidence           Environmental evidence
       and optional CNN features        site / regional / reference roles
                     \                            /
                      Rule-based criterion evaluation
                                  |
                  Applicable mandatory requirements
                Failed / Unknown / all required Passed
                                  |
              Eligible candidates only: soft-preference scoring
                                  |
         Base-location comparison + reasons + gaps + source evidence

Separate retained capability: CNN terrain-resemblance / Earth analog search
```

The environmental branch can operate on our existing regions/analysis units **without waiting for CNN-patch integration**. A real base layout/footprint is a separate configuration choice; neither a 960 m CNN patch nor a 1.2 km EDA block automatically defines it.

| Prototype pattern | Environmental extension proposed here |
| --- | --- |
| Explicit JSON configuration | Versioned selected evidence, assessment units, requirement applicability, thresholds, preference definitions and weights. Unknown configuration stays explicitly unconfigured. |
| Versioned dataset builder | Build environmental feature/evidence tables from accepted EDA/source runs. Preserve native support and missingness; do not force coarse climate or phase-average temperature onto the terrain's 30 m grid. |
| CNN training / feature computation | **Deterministic feature and rule computation**, not another CNN. Physics/response models are added only when their required inputs exist. |
| Embeddings and retrieval outputs | Per-site criterion results, mandatory status and, where permitted, preference scores. Keep CNN similarity and physical terrain discrepancies as separately named outputs. |
| Controlled comparisons and demo | Coverage/sensitivity checks, worked Passed/Failed/Unknown cases, and a location report explaining each decision. |

**Implementation reuse:** use `LocalRun`, source hashes/receipts and accepted run selection from [environment_workflow.py](EDA/environment_workflow.py); compose the aggregation helpers in [decision_eda.py](EDA/decision_eda.py), regional/joint comparison functions in [site_comparison.py](EDA/site_comparison.py) and reference-experiment readers in [reference_eda.py](EDA/reference_eda.py). Proposed new code should be small procedural functions for evidence association, criterion evaluation and report generation, with an explicit JSON configuration. No such new engine is implemented by this proposal.

The new [environmental_selection_eda.py](EDA/environmental_selection_eda.py) now supplies those **diagnostic** spatial/profile/Pareto/preference/gate primitives. It follows notebooks 31–32's fixed-control and availability-before-ranking pattern. Its counterfactual scores/thresholds are deliberately separate from operational requirement status; completing this helper is not deployment of the proposed mission engine.

## 6. EDA evidence → environmental criteria and methods

This is the modelling/criterion-design reference; source-level findings remain in the results report. Required policy, units, applicability, response validation and support must be explicit. No method below supplies missing project inputs by default.

| Evidence | Proposed method / required controls | Operational boundary |
| --- | --- | --- |
| Thermal phase/context | Empirical phase-conditioned quantile/count lookup with available/fixed cohorts; retain absent phases. For components, validate a lumped-parameter or measured response model including internal heat and radiative/conductive exchange before comparison with documented limits. | Surface brightness is not component temperature, chronological exposure or a mission extreme. |
| Solar visibility and geometry | DEM azimuth-horizon modelling plus dated SPICE Sun/disc geometry; specify observer height, frame/curvature, surrounding terrain coverage, nodata and timestep sensitivity. Then integrate generation, load, charge/discharge efficiency, storage state/bounds and reserves in consistent W/Wh/time units. | Regional crops may omit distant blockers. Mean visibility/reference-sphere runs cannot establish darkness duration; track unmet demand rather than clipping a deficit away. |
| Earth visibility | Terrain-aware station/relay line-of-sight history followed by an architecture-specific link budget: antennas, frequency, power, losses, receiver/noise and required rate; distinguish access, service scheduling and link margin. | Earth-disc visibility is not a guaranteed station/relay contact or RF service. |
| Radiation | Scenario-indexed lookup retaining dose quantity, material, areal density/depth and solar case; do not enforce monotonic depth smoothing. Applicable fields/geometry require validated transport; impact vulnerability is separate. | SEC is not LET/surface crew dose, strict GOES pilot support is empty, and published shielding scenarios are not approved mission limits. |
| Terrain/source support | Retain native support, source/cohort counts, zero-spot fraction, error/resolution and spatial-grain sensitivity with each value. Review correlated preferences as groups. | Quality fields are not independent physical rewards; do not double-count slope or automatically drop independently required hard checks. No invented confidence probability/cutoff. |
| Battery reference | Adjacent-sample Ah/Wh integration and cell/protocol/ambient/age-qualified lookup; split evaluation by unique cell history rather than repeated cycles/archive aliases. | R01 is not the selected mission battery; missing/zero capacity, tail/cutoff definitions and complex impedance remain explicit. |
| Soil reference | Geometry/contact-area/unit-aware historical response cases with depth/collapse flags; validate an applicable wheel/foundation model separately. | Cone/plate response and one Apollo site do not establish polar soil, allowable bearing pressure or certified passability. |
| Other thermal/seismic/imagery/spectral/Earth evidence | Register the observed/model/reference role, source quality and supported question before criterion use. | Do not force every dataset into a score or transfer non-polar/Earth evidence as a local lunar measurement. |

**Optional prediction, not implemented:** only if a prediction question is needed, compare the empirical baseline with a cyclic-local-time GAM or evaluated nonlinear regression. Separate spatial units and held-out phase products, holding out regions if transfer is claimed. Random-row splits across repeated centers do not establish independent validation; such a model would predict phase-average surface brightness, not equipment response or chronological extremes.

## 7. Rules and additional scoring

Each proposed criterion needs: `criterion_id`, purpose, applicable body/site/task, required evidence, units, comparison/response method, hard-versus-soft classification, threshold or preference definition, configuration version and source provenance.

### Mandatory requirements

- Evaluate only when applicability and required evidence are established.
- Complete applicable evidence meeting the documented requirement → **Passed**.
- Complete applicable evidence violating it → **Failed**.
- Missing profile, unknown applicability, insufficient evidence or unsupported transfer from reference experiments → **Unknown**, with a reason.
- At the assessment level, a proven mandatory failure prevents a pass; unresolved mandatory requirements prevent an overall pass. An empty/unconfigured rule list must not produce a pass through an `all([])` shortcut.

Example: a solar-power endurance requirement needs an actual power architecture and dated illumination. An average-sunlight field alone neither passes nor fails it. Permanent shadow is not universally “bad” without considering the activity, layout and power design.

### Soft preferences — the additional scoring layer

For candidates whose applicable mandatory requirements are all satisfied, combine **explicitly configured, normalized preference values**:

```text
preference_score = sum(configured_weight[j] * preference_function[j](supported_features))
```

This can include physical terrain preferences and environmental preferences. **No numerical weights, temperature bands or equipment limits are invented here.** Do not turn EDA correlations into weights, treat missing scores as zero, or silently renormalize away an unsupported required criterion. Correlated inputs representing one preference should be grouped/reviewed to avoid duplicate rewards.

Keep separate outputs: `terrain_similarity`, `terrain_physical_metrics`, `environment_criterion_results`, `mandatory_status`, `preference_score` and `evidence_gaps`. The current cosine-retrieval score is not added directly to a lunar base-suitability total.

If no candidate has established mandatory passes, show **environmental comparisons and the unchanged diagnostic terrain retrieval**, but no operationally eligible ranking. When adding candidate filtering to retrieval, consider the configured candidate pool before applying top-k; filtering only the existing top five could hide an eligible candidate below them.

## 8. Data association and reporting contract

Each environmental record should retain its assessment unit, location/region, body, variable, value, unit, spatial/temporal support, evidence role, source/run identity and quality/coverage flags. Reference experiments also retain their cell/run, protocol or geometry identity.

Where CNN artifacts exist, associate rankings' `query_id` / `candidate_id` with the original `patch_id` manifest and its `left/bottom/right/top/crs_wkt`. Keep `location_id`, source-run and footprint size when reusing evidence across terrain-support views. Do not infer footprint geometry by parsing an ID or join different-sized/versioned units solely on `location_id`.

Without an exact match, retain a separate site/regional/reference record and state its applicability. Do not disguise it as a patch measurement. The report should show: location, available terrain/environment evidence, criterion outcomes and reasons, any eligible preference score, missing evidence and the source details supporting the assessment.

## 9. Implementation order and acceptance checks

1. **Completed — regional comparison and joint diagnostics:** Dar_017/018 compare seven regions, quantify sampled-center co-location and export metrics with cohort/support context. No operational rule or score is implied by this completion.
2. **Completed diagnostics — Dar_019 connectivity:** explicit analysis-cell zones, nominal projected extent and grid/origin/adjacency/cut sensitivity. Physical co-registration, engineering footprint validity and a required base size remain unresolved, not invented.
3. **Completed illustrative profiles — Dar_020:** 21 component-cell examples with static distributions, phase-qualified temperature, provenance and support. Two lack associated thermal centers; component selection is purposive. Exact CNN-patch matching remains optional and regional averages never replace missing local measurements.
4. **Completed influence comparisons; integration planned — Dar_021/022:** tested preference/Pareto sensitivity and hard-gate-before-ranking diagnostics. Next connect supported records while preserving terrain outputs, with explicit applicability, hard/soft classification, thresholds and preference policy. No limits/weights come automatically from EDA correlations or these counterfactual scenarios.
5. **Planned — justified checks/scoring:** implement applicable rules and physical response methods as their inputs become available; enable preference ranking only after mandatory requirements are satisfied.
6. **Planned — demonstrate and audit:** preserve raw terrain retrieval, add an explained base-location assessment view and inspect coverage, duplicate/redundant evidence and sensitivity to configuration. Do not expand reference-dataset EDA merely to accumulate more rows.

Acceptance checks: no changed CNN inputs/normalization or baseline scores; no duplicate identities in joins; units and native support retained; missing data never becomes a pass; regional/reference evidence never masquerades as local measurement; no double-counted criterion; no preference score for unresolved mandatory assessments; reproducible run/configuration hashes. Protected reserves remain unopened, and explored development regions are not promoted to independent final-test evidence.

**Current dependency:** the original saved CNN checkpoints, training-data run and orientation cache referenced by its demo are absent from this checkout. Recover verified artifacts or explicitly rebuild upstream work before claiming a fresh CNN-integrated run. This blocks exact demo replay, **not environmental EDA, evidence registration or development of the separate rule-based layer**. Authenticated datasets remain KIV.

## 10. How the EDA outputs will be used in the algorithm

**Purpose:** keep the proposed algorithm-consumption details here, separate from the EDA notebooks' executed analysis and findings. The following maps the actual Dar_019–022 exports to their intended place in the location-selection workflow: **assessment-unit evidence → environmental profile → applicable mandatory screening → eligible soft scoring → explained ranking**.

The EDA helpers and numeric comparisons exist; the operational mission/equipment policy and integration into the original selection engine remain proposed. No diagnostic cut, weight or score below is adopted as mission policy. Source notebooks and the [question register](EDA/EDA_Notes.md#eda-question-register) remain the evidence references.

### Dar_019 — Spatial assessment units and footprint evidence

**Place in the workflow:** build spatial assessment-unit evidence **before** the environmental hard/soft checks. This study answers “where might a coherent assessment footprint exist?”, not “has this base passed?”.

| Export / fields actually produced | What the algorithm will do with them | Hard/soft use and remaining condition |
| --- | --- | --- |
| `grids/<region>.csv.gz`: `row`, `col`, `candidate_id`, context; `labels/<region>.npy`; `grid_metadata.json` | Reconstruct each irregular diagnostic component using its member cells, CRS/spacing/origin and source run. Associate terrain/environment evidence with that exact assessment unit. | Candidate generation/association first. Do **not** replace the component by its bounding rectangle or silently call it an original CNN patch. |
| `diagnostic_candidate_manifest.csv`: `candidate_id`, `region`, `cells`, `nominal_projected_area_m2`, bounds | Store the sampled spatial extent beside the candidate and link it to its source mask. The current manifest contains three size-ordered examples per region, not the full possible search pool. | A proposed footprint check needs an explicitly configured layout/size and validated geometry. These nominal diagnostic areas alone cannot produce an operational Passed. |
| `illustrative_component_catalog.csv`: `touches_analysis_boundary`, `lattice_interior_diameter_proxy_m` | Add truncation/discretization warnings to the candidate evidence report; request applicable geometry if a true width/layout check is required. | Evidence/applicability handling, **not** automatic physical penalties or proof of usable width. |
| `illustrative_grid_connectivity_comparison.csv`: spacing, shift, connectivity, largest extent | Check whether a conclusion depends on grid origin, spacing or diagonal adjacency. Retain the alternatives with the evidence. | Do not select whichever grid happens to make a hard requirement pass. Any allowed geometry/robustness policy must be configured and justified. |
| Native-source support and unknown masks | Preserve source resolution/coverage and prevent missing cells from being filled as favourable terrain. | Missing applicable required evidence leads to Unknown unless another applicable mandatory failure is already established. |

**Concrete use:** Haworth's largest illustrative component is 75 cells under four-neighbour adjacency, versus 155 under eight-neighbour adjacency. The algorithm will show that dependence with the extent evidence, rather than declaring a base fits from one area value. With no selected base layout, the operational footprint requirement stays Unknown. A preference for larger connected extent is possible **only if explicitly selected**; it is not an adopted score here.

**Reusable code now:** `lattice`, `sample_layers`, `components`, `select_component_candidates`. **Still proposed:** a validated physical-footprint/layout evaluator and association with the chosen terrain assessment units. The current solar/Earth/slope cuts must not be promoted into hard rules merely because they generated these examples.

### Dar_020 — Per-location environmental evidence records

**Place in the workflow:** turn each explicit location/footprint into an **environmental evidence record** consumed by the requirement evaluator and, later, configured preferences. Use local support, not a copied regional median.

| Export / fields actually produced | What the algorithm will do with them | Hard/soft use and remaining condition |
| --- | --- | --- |
| `candidate_manifest.csv`: `candidate_id`, region and component geometry/selection | Identify the assessed unit and its source run. Join profiles by `candidate_id` **within the same versioned run**, preserving footprint and evidence role. | Never join different-sized/versioned units solely because an ID looks similar; exact CNN-patch association is optional, not assumed. |
| `candidate_static_profiles.csv`: variable, unit, `minimum`, `q10`, `median`, `q90`, `maximum`, `cells`, `finite_cells` | Supply the exact statistic named by a configured criterion; for example, the slope-q90 proxy is distinct from maximum slope. Keep illumination/sky/shadow alongside terrain context. | A documented criterion must specify units, statistic, applicability and comparison. Finite samples/medians do not prove every point meets a whole-footprint limit. |
| `candidate_common_product_thermal.csv` and `candidate_thermal_summary.csv`: phase, cohort, temperature quantiles, support | Build a phase-qualified thermal context record. Retain the same products/cohort when comparing locations; expose absent phases. | Input to a later applicable response/thermal-requirement method, **not** equipment temperature, dated extremes or a universal “colder is better” preference. |
| `candidate_thermal_association_support.csv`: observed products and distinct associated centers; `associated_center_phase_spans.csv` | Report how much of the thermal comparison is actually observed and whether variation uses repeated centers. | Missing/sparse support cannot become zero exposure or a hard thermal pass. A 60 m cell lookup associates a thermal **center**, not its complete 240 m footprint. |
| `candidate_thermal_cohort_comparison.csv` and terrain-quality profiles | Carry selection sensitivity, zero-spot support, elevation error and effective resolution as evidence metadata. | Use them to explain applicability/uncertainty, not as arbitrary independent rewards or automatic physical failures. |

**Concrete use:** two of the 21 examples have no associated thermal centers. Their records will retain available terrain/illumination evidence but mark the thermal evidence gap. The evaluator cannot pass a thermal requirement from a regional average; applicable component response and limits are also required. For Malapert component `00082`, retain the −11.35 K fixed-minus-available summary difference as a cohort warning, **not** a correction to equipment temperature.

**Reusable code now:** `candidate_static_profiles`, `associate_points`, `candidate_thermal_profiles`, `center_phase_spans`. **Still proposed:** the operational evidence schema/applicability adapter and applicable component/mission response checks. Output records must keep value, unit, statistic, source run, spatial/phase support and missingness together.

### Dar_021 — Configured soft-preference scoring

**Place in the workflow:** design and audit the **soft-preference definition**, then apply an approved definition only to candidates whose applicable mandatory requirements all pass. This notebook's exported rankings remain diagnostic; do not import them as operational rankings.

| Export / fields actually produced | What the algorithm will do with them | Hard/soft use and remaining condition |
| --- | --- | --- |
| `comparison_units.csv`: `unit_id`, `pool`, region, `solar_fraction`, `earth_fraction`, `slope_deg` | Form the numeric proxy input table while keeping the block and component pools separate. Here solar/Earth are medians and the column `slope_deg` represents **q90**, not mean/maximum slope. | Keep source run and assessment grain with the ID. These are criterion candidates, not adopted preferences or whole-footprint guarantees. |
| `pareto_dominance.csv`: status and number of dominating units | Show which locations trade off the three chosen proxies before weight selection. | Explanation/review aid, **not** a hard eligibility filter: a dominated location may differ in thermal, radiation, layout or other unmodelled requirements. |
| `diagnostic_preference_scenarios.csv.gz`: normalization, weights, score/rank | Compare explicit preference definitions on a fixed pool; document the selected objective, benefit functions, weights and version if a policy is later approved. | Future soft score: weighted configured benefits of supported features. Current weights/transforms are examples, not defaults. No score for an unresolved mandatory assessment. |
| `normalization_comparison.csv` and `diagnostic_rank_stability.csv` | Audit whether the chosen ranking is sensitive to scale/weight assumptions and report alternative orders. | Name and freeze the reference pool for percentile-based benefits within a comparison; pool changes require an explicit new comparison/version. Scenario frequency is not confidence or a probability of being best. |
| Metric correlations and regional top-five representation | Check whether preferences repeat terrain slope rewards or favour a pool's sampling composition. | Avoid duplicate contributions. Do not convert correlations into weights or silently combine differently grained rankings. |

**Concrete use:** with the diagnostic weights (0.25, 0.25, 0.50), the component pool's top five under physical-domain and percentile scaling have no overlap. Therefore, the eventual algorithm must save **the benefit function and normalization alongside the weights**; “weighted score” alone does not define a reproducible policy.

```text
Proposed operational use, NOT an existing engine call:
  eligible = units with every applicable mandatory requirement established Passed
  benefits = apply the approved, versioned preference functions to supported evidence
  soft_score = sum(approved_weight[j] * benefits[j])
  missing required preference evidence -> no comparable score; report the reason
  retain per-criterion contributions, units, policy version and source evidence
```

**Reusable code now:** `benefit_values`, `pareto_dominance`, `preference_scenarios` demonstrate/test the comparison mechanics. **Still proposed:** approved operational preferences and their evaluator. Preserve original terrain similarity separately; neither that score nor slope should be added again without an explicit role.

### Dar_022 — Mandatory screening before ranking

**Place in the workflow:** define the **mandatory-screening and reporting order** between evidence assembly and soft ranking. The same configured pool must be screened before top-k selection.

| Export / fields actually produced | What the algorithm will do with them | Hard/soft use and remaining condition |
| --- | --- | --- |
| `marginal_and_joint_rule_availability.csv`: individual and joint counts | Verify that mandatory conjunctions are evaluated jointly rather than compensated by a favourable total score. | Translate only approved, applicable criteria into mandatory checks. These proxy thresholds and summary statistics are not adopted mission rules. |
| `diagnostic_hard_gate_scenarios.csv`: DiagnosticMet/NotMet/Unknown counts by cuts, pool and cohort | Test threshold/no-match handling and compare evidence-cohort alternatives before policy adoption. | Preserve known violations and unresolved evidence separately; lack of data alone is not physical failure. Do not relabel DiagnosticMet as operational Passed. |
| `gate_before_top5_examples.csv`: qualifying unit IDs and diagnostic scores | Validate the gate-before-ranking order on the full configured pool, not only a shortlist returned by an earlier soft/CNN ranking. | Hard requirements cannot be bypassed by soft preferences. Preserve a genuine no-match outcome instead of loosening thresholds automatically. |
| `actual_operational_requirement_readiness.csv`: region, requirement, status and reason | Populate unresolved requirement explanations for power, component thermal, communications, radiation and footprint checks. | All 35 records currently remain Unknown; these data do not supply selected hardware, dated histories, validated response or chosen layout requirements. |
| `rule_handoff_contract.json` and `eda_to_algorithm_lineage.csv` | Define the intended adapter boundary and record which prior comparisons justify each processing decision. | Procedural diagnostics are implemented/tested; operational applicability/policy evaluation and connection to the original selection engine are still proposed. |

**Concrete use:** at the illustrative block cuts (solar median ≥0.25, Earth median ≥0.50, slope q90 ≤5°), eight blocks meet the proxy conjunction. None appear in the ungated top five; screening first returns five. The implementation decision is therefore **screen the full pool, then rank**, not “retrieve five, discard failures and stop”. This finding does not validate the cuts.

```text
Proposed operational control flow, NOT a completed mission engine:
  assemble versioned terrain + environmental evidence for each assessment unit
  require an explicit applicable mandatory-rule configuration
  compare each applicable rule using its required evidence, units and response method
  if any mandatory rule is proven Failed: do not admit that unit to eligible ranking
  else if configuration/applicability/evidence is unresolved: report Unknown; no eligible score
  else if every applicable mandatory requirement is established Passed:
      evaluate the configured soft preferences on supported evidence
  apply deterministic ranking/top-k only after eligibility; retain reasons and no-match cases
```

An empty/unconfigured rule list must **not** pass through an `all([])` shortcut. Report Failed and Unknown reasons even when a candidate is excluded. In an approved compound rule, a supported violation can establish failure while other clauses remain unknown; never invent missing values to complete the comparison.

**Reusable code now:** `diagnostic_gate`, `gate_scenarios`, `requirement_readiness`. **Still proposed:** an operational rule configuration/applicability adapter and integration into the original terrain/location workflow. Keep diagnostic scenario results and operational outcomes in different fields.

## Recommendation

**Use the existing terrain work as one evidence branch and add our EDA-informed, rule-based environmental assessment as another.** Include relevant non-matching data with its proper role. Their combination supports the base-location objective through transparent requirements and justified preferences—not by assuming that more rows, higher terrain similarity or more equipment automatically means a better or safe base site.
