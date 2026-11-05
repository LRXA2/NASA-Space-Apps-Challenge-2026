# Notebooks

Read the [current findings and decisions](../outline.md#current-findings-and-evaluation-decisions) for scope and next steps. This page is an index; detailed methods and results are in the notebooks and their saved reports.

The similarity CNN **proof of concept is complete**: lunar query to Earth candidates with explained examples. Notebook 35 compares the four trained variants and explains the demo choice. Notebook 36 demonstrates the chosen full-context, region-balanced CNN; notebook 34 builds its orientation-invariant cache. Notebook 33's rating forms remain optional follow-up work.

## Find an analysis

| Topic | Notebooks |
| --- | --- |
| Raw-data organization | [01](setup/01_organize_lunar_raw_data.ipynb) |
| Initial processing | [02 Terrain](preprocessing/02_earth_terrain_landcover.ipynb), [03 Climate](preprocessing/03_earth_climate.ipynb), [04 OSM](preprocessing/04_osm_support_zones.ipynb), [05 Lunar environment](preprocessing/05_lunar_terrain_environment.ipynb), [06 Diviner](preprocessing/06_diviner_temperature.ipynb) |
| Quality checks and corrections | [07 Validation](preprocessing/07_validate_processed_outputs.ipynb), [08 Missing data](preprocessing/08_investigate_missing_data.ipynb), [09 Earth coverage](preprocessing/09_verify_earth_coverage_fix.ipynb), [10 Terrain readiness](preprocessing/10_inspect_terrain_and_patch_readiness.ipynb), [11 Environmental readiness](preprocessing/11_inspect_environment_and_actions.ipynb), [12 Shadow gaps](preprocessing/12_investigate_lunar_shadow_gaps.ipynb), [13 Lunar views](preprocessing/13_build_lunar_terrain_views.ipynb) |
| Terrain exploration | [14 Features](exploration/14_terrain_feature_eda.ipynb), [15 Patches](exploration/15_patch_terrain_eda.ipynb), [16 Scale and form](exploration/16_scale_and_spatial_form_eda.ipynb), [17 Candidates](exploration/17_earth_moon_candidate_eda.ipynb), [18 Regional diversity](exploration/18_region_diversity_eda.ipynb) |
| Development-region expansion | [19 Death Valley processing](preprocessing/19_development_region_terrain.ipynb), [20 Contribution](exploration/20_death_valley_contribution_eda.ipynb), [21 Wadi Rum processing](preprocessing/21_wadi_rum_terrain.ipynb) |
| Candidate evidence | [22 Screening](exploration/22_cross_region_screening_eda.ipynb), [23 Inspection](exploration/23_candidate_inspection_eda.ipynb), [24 Source checks](exploration/24_candidate_source_check_eda.ipynb) |
| Environmental evidence | [25 Native support](exploration/25_environment_native_support_eda.ipynb), [26 Earth expansion](preprocessing/26_earth_environment_expansion.ipynb), [27 Five-site comparison](exploration/27_five_site_environment_eda.ipynb) |
| Model preparation | [28 Training-data readiness and baseline](modeling/terrain_similarity/28_training_data_readiness_and_baseline.ipynb) |
| Similarity learning | [29 Bidirectional similarity CNN](modeling/terrain_similarity/29_similarity_cnn_experiment.ipynb) |
| Similarity diagnostics | [30 Physical mismatch and disagreement examples](modeling/terrain_similarity/30_similarity_error_analysis.ipynb) |
| Controlled sensitivity | [31 Vertical scale and retrieval response](modeling/terrain_similarity/31_vertical_scale_sensitivity.ipynb) |
| Candidate coverage | [32 Physical compatibility and ranking](modeling/terrain_similarity/32_candidate_coverage_and_ranking.ipynb) |
| Mission relevance | [33 Earth analog review for rover route-planning practice](modeling/terrain_similarity/33_mission_analog_review.ipynb) |
| Rotation and reflection handling | [34 Rebuild the saved-model cache and check orientation consistency](modeling/terrain_similarity/34_rotation_and_reflection_inference.ipynb) |
| Four-model comparison and demo choice | [35 Same-location comparison of all four trained variants](modeling/terrain_similarity/35_four_model_comparison.ipynb) |
| Slope and relative elevation | [36 Eight-orientation demo using the chosen CNN](modeling/terrain_similarity/36_slope_and_relative_elevation_demo.ipynb) |

## Run a notebook

Notebooks 07–12 include historical diagnostics. The old Arizona terrain gaps were a corrected processing defect; lunar elevation holes came from our support mask. Obsolete standalone terrain previews in 07 and 10 have been removed. Use 14 onward for current terrain comparisons; 09 and 12 retain explicit before/after evidence.

Use a Python 3.12 `.venv`; on a fresh clone, create it with `uv venv --python 3.12 .venv`. If dependencies need installing, close its running kernels first, then run from the project root in PowerShell:

```powershell
uv pip install --python .\.venv\Scripts\python.exe -r notebooks/requirements-processing.txt
```

Select `.venv\Scripts\python.exe` as the notebook kernel. Save configuration changes, then run cells from the top. After updating to the topic-based Python layout, restart any open kernels before rerunning; they may still hold modules imported from the old paths. Download instructions are [separate](../download%20scripts/README.md). A fresh clone does not contain the pinned `data/` inputs, reference records or trained models: restore those local artifacts, or rebuild the required inputs and update the pinned paths before running the notebooks.

Notebook 28 uses the same dependencies. Its [configuration](modeling/terrain_similarity/terrain_dataset.json) pins accepted terrain runs and a development fold; the builder can also run from the root with `.\.venv\Scripts\python.exe -m notebooks.modeling.terrain_similarity.terrain_dataset`. Outputs go to ignored `data/processed/terrain_learning_readiness/`. Atacama and Leibnitz are EDA-exposed development holdouts, not final tests. No CNN is trained in 28.

Notebook 29 adds PyTorch: install `uv pip install --python .venv/Scripts/python.exe -r notebooks/requirements-modeling.txt` after the processing dependencies. Its [configuration](modeling/terrain_similarity/similarity_experiment.json) pins the notebook-28 dataset and defaults to `cuda:0`. Run the notebook or `.\.venv\Scripts\python.exe -m notebooks.modeling.terrain_similarity.similarity_experiment`. Four fixed experiments compare sampling and lunar support policies using one encoder architecture for both bodies. Weights go to ignored `notebooks/modeling/terrain_similarity/weights/<run>/<view>/<sampling>/model.pt`; preprocessing, tables and provenance stay in `data/processed/terrain_similarity_cnn/<run>/`. Figures stay in `reports/terrain-similarity-cnn/`. Training loss and baseline agreement are diagnostics, not relevance validation.

Notebook [35](modeling/terrain_similarity/35_four_model_comparison.ipynb) compares all four saved notebook-29 variants on shared query locations and identical candidate pools. It includes the mathematical reference, physical-match metrics, training curves, threshold sensitivity, regional results and terrain examples. The full-context, region-balanced CNN is chosen for the demo: it ties for the best top-five physical-match rate and has lower slope and relief errors than the other tied model on the main development comparison. Another CNN has lower relief error overall. This is a practical choice from development results, not independently validated analog accuracy.

Run All in 35 uses the pinned local artifacts without retraining. It compares the original four-rotation embeddings for every variant. Tables go to `data/processed/analysis/four-model-comparison-<run>/`, with reports and figures under `reports/analysis/`. Restricting the comparison to common locations excludes the full-context view's extra coverage.

For the demonstration, run [34](modeling/terrain_similarity/34_rotation_and_reflection_inference.ipynb) if its orientation cache needs rebuilding. It averages four rotations and their reflections for both bodies and retains the chosen model's weights/scaler. [36](modeling/terrain_similarity/36_slope_and_relative_elevation_demo.ipynb) is already pinned to a completed cache; if you rerun 34, copy its printed path into `ORIENTATION_RUN` in 36. Run 36 to see the chosen CNN's slope and relative-elevation comparisons, physical differences and distributions. Its `DEMO.md`, CSVs and figures go to ignored `reports/terrain-similarity-oriented-demo/<run>/`. These measurements explain CNN rankings without changing them. Notebook 35's metrics use four rotations; they do not measure this demo's eight-orientation policy.

- **To read existing findings:** open the relevant notebook; no preprocessing rerun is needed.
- **To rerun EDA:** check the notebook's pinned input paths. Running every notebook in numeric order does not automatically select new outputs.
- **To rebuild inputs:** process, validate coverage/hashes/masks, then explicitly select the accepted runs for EDA. Do not rerun notebook 01 merely to start analysis.

## Outputs and reproducibility

Processing writes versioned runs under `data/processed/`. EDA saves reusable tables, rasters and manifests under `data/processed/analysis/<run>/`; its final cell publishes figures and reports to `reports/analysis/<run>/`. Source research, unit policies and the frozen source-check sample live under `data/reference/`. Reruns create new directories. Run through the final export cell; interrupted folders may be partial.

Exact inputs, parameters and source hashes are recorded in notebook configuration and provenance. Keep referenced data runs and reference records intact. Reports are optional exports: deleting `reports/` does not invalidate reusable data manifests or notebook inputs. The relocation receipt at `data/reference/analysis-relocation-20261102.json` preserves original paths and hashes; historical source hashes describe the code or notes used at the time. Scientific limitations and evaluation rules are summarized in [outline.md](../outline.md#current-findings-and-evaluation-decisions).

Before staging notebooks in Git, **save with useful outputs retained**, including plots, tables and results. Review the saved outputs for errors, credentials and personal filesystem paths before publishing. Embedded images are part of the notebook file and are not excluded by `.gitignore`. Code, notebook Markdown and saved outputs remain trackable; standalone data, figures, reports and their provenance records stay local in the ignored output directories.

## Saved-model site comparison

The [Python pipeline](modeling/terrain_similarity/pipeline/main.py) compares a whole prepared lunar region with one prepared Earth region. Its files live together in the `terrain_similarity/pipeline/` package. It reuses the full-context, region-balanced CNN selected in notebook 35 and notebook 34's eight-orientation cache. Notebooks 34–36 remain saved records of the experiments; the command needs no notebook runtime.

Training and all notebook/pipeline readers share [model_weights.py](modeling/terrain_similarity/model_weights.py). The configured `model_run` identifies the training metadata; its run ID determines the weights folder. New training runs register a `weights.json` location/hash descriptor beside their preprocessing. Relocated checkpoints are checked against their original manifest hashes, so historical manifests and orientation caches remain unchanged. Keep both the weights folder and the referenced data runs when transferring the pipeline.

The script compares **one Moon site and one Earth site per call**. Your application owns the loop over Earth sites and selects the highest-scoring result. For in-memory integration, `compare_sites(terrain, moon_site, earth_site)` returns match tables and a summary; the score is `summary["median_best_patch_cosine"]`.

Import the callable interface from `notebooks.modeling.terrain_similarity.pipeline`: `ArtifactConfig`, `TerrainModel`, `compare_sites` and `run_inference`. `main.py` is the implementation entry point; `__main__.py` enables the shorter package command below.

```powershell
.\.venv\Scripts\python.exe -m notebooks.modeling.terrain_similarity.pipeline --list-sites
.\.venv\Scripts\python.exe -m notebooks.modeling.terrain_similarity.pipeline --moon-site Haworth --earth-site wadi_rum
```

Full region IDs and readable names are accepted. Matching ignores spaces, underscores, hyphens and capitalization. Every eligible lunar patch is matched against only the selected Earth's prepared patches, with all development folds included. `--top-k` defaults to 3; `--no-plots` skips the figures. The selected regions must already exist in the accepted dataset; this command does not process arbitrary coordinates or raw elevation files.

Each run writes:

- `summary.json`: patch counts, median/mean best-patch cosine, median physical differences, the count of lunar patches with a candidate passing all five exploratory checks, and how often distinct Earth patches are used.
- `retrieval.csv` and `physical_comparison.csv`: all ranked pairs, Earth coordinates, cosine scores and measurements in their original units.
- `selected_patches.csv`: the prepared patches belonging to both selected sites.
- `report_examples.csv`: the highest, middle and lowest first-match score examples selected for the report.
- `provenance.json`: completion or failure status, exact settings, input/source hashes and code revision.

Tables and provenance live under `data/processed/terrain_similarity_pipeline/<run>/`. Optional `REPORT.md`, pair maps and slope/height distributions live separately under `reports/terrain-similarity-pipeline/<run>/`. Report deletion does not invalidate the reusable data. Summaries cover all prepared lunar patches; visual examples illustrate score extremes and the middle, rather than forming a random evaluation sample.

**Interpretation:** this is a directed comparison: does the Earth site contain terrain resembling the lunar site? The median best-patch cosine is not a percentage of site similarity, and larger Earth candidate pools offer more opportunities for a close match. Repeated use of one Earth patch does not imply extensive matching terrain. Physical thresholds explain the results without reranking them. General accuracy and environmental, access or equipment suitability remain unvalidated.

The [configuration](modeling/terrain_similarity/pipeline/config.json) pins local training, dataset and orientation runs. The loader rejects changed hashes or mismatched model, dataset, scaler, patch IDs, support view and inference policy. Use `--config path/to/config.json` for another accepted artifact set. Use `--rebuild-cache` to explicitly regenerate embeddings with the saved weights/scaler; it checks rotation/reflection consistency and writes `embeddings.npz`, `preprocessing.json`, `patches.csv` and `orientation_checks.csv` into the new data run. To reuse that cache, set `orientation_run` in a configuration copy to the printed data-run path. A failed cache validation never triggers silent rebuilding.

## Python helpers and tests

Python helpers live with their topic: `preprocessing/`, `exploration/` and `modeling/terrain_similarity/`. Common raster, terrain-measurement, validation and report utilities live in `shared/`. Imports use the `notebooks` package from the repository root; each notebook locates that root automatically.

From the project root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s notebooks -t . -v
```

Shared and cross-stage tests live in `shared/tests/`; dataset and CNN tests live in `modeling/terrain_similarity/tests/`. These focused tests check processing and analysis behavior; they do not validate source accuracy or mission suitability.
