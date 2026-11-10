# Earth-trained operational terrain CNN plan

Beginner walkthrough: [`docs/00_START_HERE.md`](docs/00_START_HERE.md)

Status: implementation started. Provisional generated labels now exist; no operational CNN has been trained.

## First implementation run — 10 November 2026

The current-run EDA and directional connectivity code is implemented in
`operational_cnn/` and was run against all five accepted
November Earth terrain runs.

Completed run:

`data/processed/terrain_operability_eda/20261110T130243908177Z_49a299`

The run produced 22,678 size-specific records across 600 m and 960 m windows,
five-channel tensor shards, grid-origin sensitivity, feature correlations,
spatial groups and provisional directional labels. Provenance finished with
`status: complete`. No CNN was trained.

Initial class balance is similar at both scales:

| Size | Operable | Marginal | Non-operable |
| --- | ---: | ---: | ---: |
| 600 m | 79.8% | 14.6% | 5.6% |
| 960 m | 80.2% | 15.0% | 4.9% |

The labels are not collapsed, but they are imbalanced and currently derive from
slope connectivity only. Representative maps must be reviewed before training.
Median 90 m and 330 m roughness summaries are also very strongly correlated
within regions, although their spatial patterns may still differ. The next gate
is therefore visual label inspection and a decision about whether roughness
belongs in the label rule, the CNN inputs, or both.

### First prototype CNN

A small 89,927-parameter multi-task CNN was subsequently trained as a pipeline
test. Death Valley was held out as the whole Earth test region; validation used
complete 5 km spatial groups from the other four regions.

Completed model run:

`data/processed/terrain_operability_model/20261110T131117138093Z_304ddb`

| Metric | Validation | Held-out Death Valley test |
| --- | ---: | ---: |
| Accuracy | 89.1% | 87.8% |
| Balanced accuracy | 84.0% | 85.5% |
| Operable recall | 91.6% | 91.4% |
| Marginal recall | 72.9% | 68.8% |
| Non-operable recall | 87.5% | 96.4% |

This result verifies tensor loading, train-only normalization, spatial grouping,
multi-task training and whole-region testing. It is not validation of real rover
operability: the labels are generated from slope connectivity and slope is an
input, so the CNN is learning an approximation of the deterministic rule. The
deterministic generator remains perfect against its own labels by definition.
Real progress now requires stronger labels or a richer route-cost target rather
than merely increasing CNN epochs.

## 1. Goal

Build a second CNN, separate from the existing terrain-similarity CNN, that estimates whether a wheeled rover can find a practical **macro-scale route** through a terrain patch.

The first model target is deliberately narrow:

> Given a terrain patch and an entry/exit direction, estimate whether a nominal wheeled rover can find a route across the patch.

This is a macro-traversability estimate. With the current 30 m Earth grid it cannot certify wheel-scale safety, detect small rocks, predict sinkage, establish habitability, or prove complete lunar operational suitability.

## 2. Why this target is appropriate

“Operational” is too broad to label directly. It can include terrain, illumination, thermal conditions, communications, power, regolith strength, radiation, access and vehicle-specific constraints. A route-crossing task has a clear question, measurable outputs and a direct relationship to lunar rover operations.

NASA describes lunar route planning as dependent on vehicle capabilities, slope, rocks, illumination, power and communications. VIPER was generally planned around slopes near 15 degrees, with steeper slopes increasing slip and slowing progress. These are useful scenario references, not universal safety thresholds:

- [NASA VIPER lunar operations](https://science.nasa.gov/mission/viper/lunar-operations/)
- [NASA Moon Base Systems](https://www.nasa.gov/moonbase-systems/)
- [NASA Apollo rover performance and Artemis traverse planning](https://ntrs.nasa.gov/citations/20250011301)

## 3. Current Earth data

The accepted November 2026 processing runs provide five Earth regions on projected 30 m grids:

- Northern Arizona
- Lanzarote
- Atacama–San Pedro
- Death Valley
- Wadi Rum

Available aligned terrain and screening layers include:

- elevation;
- patch/region-relative elevation;
- slope;
- 330 m-support local elevation standard deviation;
- Laplacian/curvature proxy;
- validity and source-coverage masks;
- bare/sparse, built, crop and water fractions;
- natural-terrain screen.

Earth-only contextual evidence includes WorldCover, TerraClimate and OSM. These can support sampling, weak supervision and review, but they must not be normal inputs to a model intended for lunar inference.

The current readiness report is [the November data-readiness report](../reports/data-readiness/20261105T155134Z/REPORT.md).

## 4. Current-patch inventory

A read-only audit of the accepted November rasters used non-overlapping 32 × 32 windows, required complete valid terrain and required at least 80% of each window to pass the existing natural-terrain screen.

| Earth region | Eligible 960 m windows | Median window P90 slope |
| --- | ---: | ---: |
| Northern Arizona | 2,490 | 3.19° |
| Lanzarote | 211 | 5.45° |
| Atacama–San Pedro | 4,952 | 7.25° |
| Death Valley | 1,592 | 8.68° |
| Wadi Rum | 1,946 | 26.61° |
| **Total** | **11,191** | — |

These counts show enough patch volume for an initial experiment and a useful easy-to-difficult terrain range. They are not independent observations: neighboring windows from one region share terrain, source and mapping characteristics.

## 5. What the existing EDA contributes

The exploration notebooks were reviewed as design evidence. Most are pinned to October processing run IDs that are absent from the rebuilt November runtime. Their numerical tables must therefore be regenerated from complete November runs before they are used as modelling inputs.

### Notebook 14: terrain feature EDA

[14_terrain_feature_eda.ipynb](../notebooks/exploration/14_terrain_feature_eda.ipynb) supports these decisions:

- use relative rather than absolute elevation for cross-body shape modelling;
- keep lunar support and quality masks explicit;
- do not infer independent-sample confidence from spatially adjacent cells;
- inspect extreme values rather than silently clipping or deleting them;
- keep environmental analysis separate from terrain analysis.

### Notebook 15: patch terrain EDA

[15_patch_terrain_eda.ipynb](../notebooks/exploration/15_patch_terrain_eda.ipynb) shows that:

- complete-window counts depend on grid origin and stride;
- patch populations change with physical patch size;
- the current local elevation SD has 330 m support;
- patch availability must be reported with explicit denominators;
- slope, relief and roughness associations do not prove that the channels are interchangeable.

This means one arbitrarily aligned 960 m lattice must not be treated as the only possible dataset.

### Notebook 16: scale and spatial-form EDA

[16_scale_and_spatial_form_eda.ipynb](../notebooks/exploration/16_scale_and_spatial_form_eda.ipynb) compared 300 m, 600 m and 960 m windows at matched centers. It found that:

- no universal patch size has been justified;
- central relief changes more with extent than median or P90 slope;
- patches with similar scalar slope/relief summaries can have different spatial arrangements;
- plane residual and absolute relief should be read together;
- spatial evaluation groups and intended rotation invariance must be chosen before normalization or tuning.

The spatial-arrangement result provides a real reason to test a CNN: a deterministic summary table may miss whether obstacles form a connected barrier or leave a traversable corridor.

### Notebooks 20, 22, 23 and 24: region, screening and source checks

[20_death_valley_contribution_eda.ipynb](../notebooks/exploration/20_death_valley_contribution_eda.ipynb), [22_cross_region_screening_eda.ipynb](../notebooks/exploration/22_cross_region_screening_eda.ipynb), [23_candidate_inspection_eda.ipynb](../notebooks/exploration/23_candidate_inspection_eda.ipynb) and [24_candidate_source_check_eda.ipynb](../notebooks/exploration/24_candidate_source_check_eda.ipynb) reinforce that:

- WorldCover screening is a population policy, not proof of access or safety;
- adding candidates mechanically increases coverage but does not prove generalization;
- source labels and imagery are not independent operational truth;
- broad Arizona terrain form was supported in selected source checks, but vegetation and access remained unresolved;
- missing roads or mapped features must not be interpreted as negative operational labels.

### Notebooks 25 and 27: environmental EDA

[25_environment_native_support_eda.ipynb](../notebooks/exploration/25_environment_native_support_eda.ipynb) and [27_five_site_environment_eda.ipynb](../notebooks/exploration/27_five_site_environment_eda.ipynb) support keeping environment out of the first terrain CNN:

- TerraClimate is regional/monthly context rather than a 30 m patch measurement;
- OSM does not verify legal access, passability or emergency readiness;
- lunar illumination and Diviner products have different spatial and temporal support;
- a universal all-products completeness filter can remove most or all usable lunar locations;
- missing environmental evidence must stay Unknown.

## 6. Operational-anchor strategy

### Black Point Lava Flow

Black Point Lava Flow is inside the Northern Arizona development region and is the strongest existing operational anchor. NASA used it for Desert Research and Technology Studies rover operations and planned traverses:

- [NASA D-RATS simulated lunar operations](https://www.nasa.gov/humans-in-space/nasa-practices-rover-operations-in-simulated-lunar-environment/)
- [D-RATS 2022 test report](https://ntrs.nasa.gov/api/citations/20230017073/downloads/D-RATS%202022%20Test%20Report%20Final.pdf?attachment=true)

The report describes collection of rover GPS, distance, speed, slope, power and vehicle-event information. If georeferenced traverse telemetry can be obtained, it should be treated as high-quality positive evidence along the actual driven corridor.

It must not be converted into “the entire plot is safe.” A completed route proves that one vehicle completed that route under those test conditions. It does not label nearby avoided terrain, and it does not provide sufficient negative examples.

### OSM as weak evidence

The accepted OSM extracts contain many transport features, including thousands of tracks in Northern Arizona and Lanzarote and hundreds in Atacama, Death Valley and Wadi Rum. Unpaved tracks can support review and weak-positive checks.

OSM rules:

- an unpaved route is weak positive evidence, not ground truth;
- paved/engineered roads should not define natural-terrain operability;
- absence of an OSM route is never a negative label;
- OSM is not a lunar CNN input;
- route geometry and surrounding patches must stay in one spatial split.

## 7. Label definition

### 7.1 Label unit

One record represents:

- one projected terrain window;
- one physical scale;
- one entry/exit direction;
- one vehicle scenario;
- one data-quality state.

Start with four crossings:

- north to south;
- east to west;
- northwest to southeast;
- northeast to southwest.

### 7.2 Vehicle scenarios

Use configurable scenarios rather than one asserted truth:

| Scenario | Initial purpose |
| --- | --- |
| Conservative | Gentle terrain and a large margin |
| Nominal | Approximately 15° nominal-slope regime |
| Permissive | Short steeper sections allowed at high cost |

Exact cost curves and any hard limits must be stored in versioned configuration. Roughness should initially be a continuous cost because the current 30 m data cannot justify a universal obstacle-clearance threshold.

### 7.3 Deterministic route labels

For each window:

1. Construct a per-cell travel-cost raster from slope, multi-scale roughness and validity.
2. Treat invalid cells as Unknown/blocked for that run, never as zero-cost terrain.
3. Use A* or Dijkstra search between entry and exit boundary sets.
4. Repeat for each direction and vehicle scenario.
5. Save the path and all intermediate measurements.

Required continuous outputs:

- path exists;
- minimum route cost;
- route length divided by straight-line distance;
- maximum and mean route slope;
- roughness along the route;
- fraction of passable cells;
- largest connected passable component;
- fraction of directions crossed;
- label confidence and evidence source.

Display classes may then be derived:

- `operable`: several practical crossings under the nominal scenario;
- `marginal`: limited or costly crossing, or scenario-sensitive result;
- `non_operable`: no crossing under the declared scenario;
- `unknown`: insufficient, invalid or unsupported evidence.

The continuous measurements are authoritative; class boundaries remain configurable.

### 7.4 Human review

Before training, review a region-balanced sample from every class and scenario. The review display should include:

- relative elevation;
- slope;
- both roughness scales;
- curvature;
- validity and natural-screen masks;
- proposed route;
- OSM route overlay when available;
- source coordinates and region.

Use at least two reviewers for the audit subset. Disagreement should lower confidence or yield `unknown`, not be forced into a majority “safe” label.

## 8. CNN feature plan

### Initial transferable channels

| Channel | Role |
| --- | --- |
| Patch-mean-centered elevation | Terrain shape without body-specific datum |
| Slope | Large-scale traversal demand |
| 90 m local elevation SD | Finer terrain variation available from the 30 m grid |
| 330 m local elevation SD | Broad ruggedness/context |
| Curvature or Laplacian | Ridges, depressions and abrupt shape changes |

The 90 m roughness layer must be generated consistently for all Earth and lunar inputs.

### Masks and quality

Validity and source-support masks should gate examples and preserve Unknown. If all training windows are complete, a constant validity channel adds no information; it should not be included merely to increase the channel count. Lunar quality/uncertainty should be reported alongside predictions and may later enter a calibrated uncertainty branch.

### Earth-only evidence not used as lunar CNN input

- WorldCover classes and fractions;
- OSM roads, tracks and facilities;
- TerraClimate variables;
- built, crop and water fractions;
- absolute Earth elevation.

These may support sampling, weak labels or auditing only.

### Later features to investigate

- local relief at matched physical support;
- topographic position index;
- slope variability;
- detrended plane-residual RMS;
- directional elevation gradients, with correct vector rotation during augmentation;
- higher-resolution rock/boulder and regolith evidence if matched Earth–Moon sources become available.

## 9. Scale decision

Do not lock the project to 960 m solely because the similarity CNN uses 32 × 32 cells.

The first operational EDA should compare at least 600 m and 960 m tasks on common centers. A 300 m patch is smaller than the support of the existing 330 m roughness channel, so it should only be tested after the new 90 m roughness layer exists.

Recommended initial modelling choice:

- primary experiment: 960 m, 32 × 32 cells;
- sensitivity experiment: 600 m on matched centers;
- later tactical experiment: higher-resolution data, not a misleading 30 m-grid claim.

## 10. Spatial splitting and leakage prevention

Random patch splitting is prohibited.

Rules:

- neighboring/overlapping windows belong to the same spatial group;
- all child windows from one operational plot belong to one split;
- normalization statistics are fitted on training groups only;
- label thresholds and model settings are not tuned on the final Earth test region;
- Moon data is never used for Earth model selection.

Primary evaluation should use five leave-one-region-out rounds. Inside the four training regions, use large spatial blocks, initially about 5 km × 5 km, for training/validation grouping.

Overlapping windows may later be used for training augmentation, but no overlap or context halo may cross into validation or test blocks.

## 11. Baselines before the CNN

The CNN must be compared with transparent baselines:

1. maximum or P90 slope threshold;
2. logistic regression or shallow tree on scalar patch descriptors;
3. deterministic A*/Dijkstra route planner;
4. small CNN using the spatial channels.

If the CNN is trained from deterministic route-planner labels, it is learning an approximation of that planner. It must not be claimed to discover independent safety truth. Its possible value is learning spatial barrier/corridor patterns and producing fast screening estimates.

## 12. Initial CNN task and architecture

Input:

```text
(batch, 5 channels, 32 rows, 32 columns)
```

Initial multi-task outputs:

```text
four route-crossing probabilities
minimum normalized route cost
prediction uncertainty/confidence
```

Start with a small residual-style CNN rather than reusing the similarity head. The similarity model and operational model have different objectives and must remain separate. A later comparison may test a frozen or shared encoder, but only after the independent baseline is understood.

If pixel-level passability labels later become supported by high-resolution observations, a U-Net-style segmentation model can be evaluated separately.

## 13. Evaluation

Earth quantitative evaluation:

- macro F1 and balanced accuracy for each crossing direction;
- mean absolute error for route cost;
- calibration error and reliability plots;
- confusion matrix per region and terrain-difficulty band;
- performance on Black Point/known-route anchors;
- performance separately for strong, weak and generated labels;
- comparison with all deterministic baselines;
- sensitivity to patch scale, grid origin and vehicle scenario.

Required failure analysis:

- false operable predictions;
- false non-operable predictions;
- failures near invalid/source boundaries;
- failures on very low-relief and very high-relief terrain;
- failures caused by vegetation/source artefacts;
- out-of-distribution feature ranges.

## 14. Lunar inference

Only after Earth evaluation passes the declared gates:

1. Freeze all model weights and Earth-fitted normalization.
2. Generate exactly matched lunar channels and physical support.
3. Infer on image-supported terrain first; preserve full-context results separately.
4. Flag patches outside the Earth training feature envelope.
5. Report model uncertainty and lunar data quality.
6. Inspect known landing/traverse areas as qualitative case studies, not a statistical test set.
7. Combine terrain output with separate lunar-only evidence: illumination, Diviner temperature, Earth visibility/communications and source uncertainty.

The output name should remain explicit, for example:

> Earth-trained macro-terrain traversability estimate.

Do not call it lunar safety, habitability or certified operational suitability.

## 15. Implementation sequence

### Phase A: current-run operational EDA

- Create a new operational EDA notebook rather than rewriting historical EDA notebooks.
- Point only to November runs with complete provenance.
- Reproduce patch inventories at 600 m and 960 m with several grid origins.
- Generate and audit 90 m roughness.
- Measure correlations and incremental information among proposed channels.
- Map Black Point and inspect available D-RATS/OSM evidence.

Gate A: accepted channel definitions, scale policy, spatial groups and evidence limitations.

### Phase B: route-label generator

- Implement versioned vehicle-scenario configuration.
- Generate cost maps and deterministic routes.
- Save paths, continuous labels, classes, confidence and provenance.
- Produce region/class/scenario distributions and maps.

Gate B: no unexplained missing values, no extreme class collapse and successful visual review.

### Phase C: label audit

- Review a stratified sample with two reviewers.
- Compare generated labels with known rover routes and OSM weak positives.
- Revise cost curves only using development evidence.
- Freeze label schema version 1.

Gate C: documented agreement and retained Unknown class.

### Phase D: baselines and CNN

- Run scalar and deterministic baselines.
- Train the separate multi-task CNN under spatial/region splits.
- Report calibration, regional performance and failure analysis.
- Do not inspect lunar predictions for model selection.

Gate D: CNN must add useful performance or speed while remaining calibrated; otherwise retain the deterministic planner.

### Phase E: lunar experimental inference

- Freeze the selected Earth model.
- Run matched lunar channels with support masks.
- Produce uncertainty-aware terrain predictions.
- Add lunar environment as a separate decision layer.
- Conduct manual mission-site case studies.

## 16. Planned artifacts

Implemented project structure:

```text
operational_cnn/
    docs/
    notebooks/
    configs/
    data/
    labels/
    model/
    training/
    review/
    tests/
data/processed/terrain_operability_labels/<run_id>/
reports/terrain-operability/<run_id>/
```

Every processed run should include complete provenance, input hashes, scenario configuration, spatial-group assignments and label-schema version.

## 17. Decisions to use unless later evidence changes them

- Task: directional macro-route traversability.
- Primary patch: 960 m; 600 m sensitivity.
- Primary nominal slope scenario: approximately 15°, explicitly configurable.
- Model inputs: five transferable terrain channels.
- WorldCover/OSM/climate: evidence and audit only, not lunar CNN inputs.
- Splitting: leave-one-region-out plus spatial blocks.
- Labels: continuous route measurements plus operable/marginal/non-operable/unknown display classes.
- Black Point: strong operational anchor, not the whole training dataset.
- Lunar stage: frozen-model out-of-distribution inference and manual case studies.

## 18. Stop condition before implementation

Do not begin CNN training merely because patches can be extracted. Begin only after the current-run operational EDA and route-label audit show that:

- channel support is consistent;
- label classes are not trivial or collapsed;
- neighboring data cannot leak between splits;
- the labels represent a declared vehicle scenario;
- uncertainty and Unknown are retained;
- the deterministic baseline is recorded.

