# Notebooks

This folder contains terrain processing, exploratory data analysis, and similarity-model experiments.
This guide indexes the notebooks and explains how to run them. Detailed methods and results are in the notebooks and saved reports.
See the [findings and evaluation decisions](../outline.md#current-findings-and-evaluation-decisions) for the research scope.

The similarity convolutional neural network, or CNN, matches lunar queries to Earth terrain candidates.
Notebook 35 compares four trained variants and explains the demo model choice.
Notebook 36 demonstrates the selected full-context, region-balanced CNN. Notebook 34 builds its rotation and reflection cache.
Notebook 33 contains rating forms for mission-relevance review.

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

Notebooks 07 to 12 include historical diagnostics. The Arizona terrain gaps came from a corrected processing defect.
The lunar elevation holes came from the support mask. Use notebook 14 onward for current terrain comparisons.
Notebooks 09 and 12 retain evidence from before and after the corrections.

Use a Python 3.12 `.venv`. Create it with `uv venv --python 3.12 .venv` on a fresh clone.
Close running notebook kernels before installing dependencies. Run from the repository root in PowerShell:

```powershell
uv pip install --python .\.venv\Scripts\python.exe -r notebooks/requirements-processing.txt
```

Select `.venv\Scripts\python.exe` as the notebook kernel. Save configuration changes, then run cells from the top.
Restart open kernels after module paths change. Kernels can retain imports from old paths.
See the [download instructions](../download%20scripts/README.md) for source data.
A fresh clone does not contain the pinned `data/` inputs, reference records, or trained models.
Restore those files or rebuild the inputs and update the pinned paths before running the notebooks.

Notebook 28 uses the same dependencies. Its [configuration](modeling/terrain_similarity/terrain_dataset.json) pins accepted terrain runs and a development fold.
Run the builder from the repository root with `.\.venv\Scripts\python.exe -m notebooks.modeling.terrain_similarity.terrain_dataset`.
Outputs go to ignored `data/processed/terrain_learning_readiness/`. Notebook 28 prepares data without training a CNN.
Atacama and Leibnitz are development holdouts already examined during exploratory analysis. They are not independent final tests.

Notebook 29 adds PyTorch. Run `uv pip install --python .venv/Scripts/python.exe -r notebooks/requirements-modeling.txt` after installing the processing dependencies.
Its [configuration](modeling/terrain_similarity/similarity_experiment.json) pins the notebook-28 dataset and defaults to `cuda:0`.
Run the notebook or `.\.venv\Scripts\python.exe -m notebooks.modeling.terrain_similarity.similarity_experiment`.
Four fixed experiments compare sampling and lunar support policies using one encoder architecture for both bodies.
Weights go to ignored `notebooks/modeling/terrain_similarity/weights/<run>/<view>/<sampling>/model.pt`.
Preprocessing, tables, and provenance stay in `data/processed/terrain_similarity_cnn/<run>/`. Figures stay in `reports/terrain-similarity-cnn/`.
Training loss and baseline agreement are diagnostics, not relevance validation.

Notebook [35](modeling/terrain_similarity/35_four_model_comparison.ipynb) compares the four saved notebook-29 variants on shared query locations and identical candidate pools.
It includes the mathematical reference, physical-match metrics, training curves, threshold sensitivity, regional results, and terrain examples.
The demo uses the full-context, region-balanced CNN. It ties for the best top-five physical-match rate on the main development comparison.
It has lower slope and relief errors than the other tied model. Another CNN has lower relief error overall.
These development results support the model choice. They do not independently validate analog accuracy.

Running all cells in notebook 35 uses the pinned local files without retraining.
It compares the original four-rotation embeddings for every variant.
Tables go to `data/processed/analysis/four-model-comparison-<run>/`, with reports and figures under `reports/analysis/`.
Restricting the comparison to common locations excludes the full-context view's extra coverage.

Run [34](modeling/terrain_similarity/34_rotation_and_reflection_inference.ipynb) to rebuild the demo's orientation cache.
It averages four rotations and their reflections for both bodies and retains the selected model's weights and scaler.
Notebook [36](modeling/terrain_similarity/36_slope_and_relative_elevation_demo.ipynb) pins a completed cache.
After rerunning 34, copy its printed path into `ORIENTATION_RUN` in 36.
Run 36 to inspect slope and relative-elevation comparisons, physical differences, and distributions.
Its `DEMO.md`, CSVs, and figures go to ignored `reports/terrain-similarity-oriented-demo/<run>/`.
These measurements explain CNN rankings without changing them.
Notebook 35's metrics use four rotations. They do not measure the demo's eight-orientation policy.

- Open a notebook to read its saved findings. No preprocessing rerun is needed.
- Check pinned input paths before rerunning exploratory analysis. Running notebooks in numeric order does not automatically select new outputs.
- To rebuild inputs, process the data and validate coverage, hashes, and masks. Select the accepted runs for analysis.
- Notebook 01 organizes raw data. It is not required to read existing analyses.

## Outputs and reproducibility

Processing writes versioned runs under `data/processed/`.
Exploratory analysis saves reusable tables, rasters, and manifests under `data/processed/analysis/<run>/`.
The final cell publishes figures and reports to `reports/analysis/<run>/`.
Source research, unit policies, and the frozen source-check sample live under `data/reference/`.
Reruns create new directories. Run through the final export cell, because interrupted runs may leave partial folders.

Notebook configuration and provenance record exact inputs, parameters, and source hashes.
Keep referenced data runs and reference records intact. Deleting optional `reports/` exports does not invalidate data manifests or notebook inputs.
The relocation receipt at `data/reference/analysis-relocation-20261102.json` preserves original paths and hashes.
Historical source hashes describe the code or notes used at the time.
See [outline.md](../outline.md#current-findings-and-evaluation-decisions) for scientific limitations and evaluation rules.

Save notebooks with useful outputs, including plots, tables, and results, before staging them in Git.
Review saved outputs for errors, credentials, and personal filesystem paths before publishing.
Embedded images are part of the notebook file. The `.gitignore` file does not exclude them.
Git can track code, notebook Markdown, and saved outputs.
Standalone data, figures, reports, and their provenance records stay local in ignored output directories.

## Saved-model site comparison

The [Python pipeline](modeling/terrain_similarity/pipeline/main.py) compares a prepared lunar region with one prepared Earth region.
Its files live in the `terrain_similarity/pipeline/` package.
It reuses the full-context, region-balanced CNN selected in notebook 35 and notebook 34's eight-orientation cache.
Notebooks 34 to 36 contain saved experiment results. The pipeline command needs no notebook runtime.

Training, notebooks, and pipeline readers share [model_weights.py](modeling/terrain_similarity/model_weights.py).
The configured `model_run` identifies the training metadata. Its run ID determines the weights folder.
New training runs write weight locations and hashes to `weights.json` beside their preprocessing files.
The loader checks relocated checkpoints against their original manifest hashes. Historical manifests and orientation caches remain unchanged.
Keep both the weights folder and the referenced data runs when transferring the pipeline.

Site mode compares one Moon site and one Earth site per call.
For in-memory integration, `compare_sites(terrain, moon_site, earth_site)` returns match tables and a summary.
The score is `summary["median_best_patch_cosine"]`.

Tile mode matches selected lunar tiles against every Earth site in one run.
Pass a CSV with a `tile_id` column, such as `moon_tiles.csv` or a shortlist from it.
See [shared Moon tile IDs](shared/moon_tiles.py).

```powershell
.\.venv\Scripts\python.exe -m notebooks.modeling.terrain_similarity.pipeline --tiles path/to/shortlist.csv --top-k 3
```

It keeps the top `--top-k` Earth patches per site, or all patches when a site has fewer.
It adds `overall_rank` across sites by cosine similarity.
It writes `earth_matches.csv`, `physical_comparison.csv`, and `summary.json` to `data/processed/terrain_similarity_tile_matches/<run>/`.
Add `--earth-site` to restrict the search to one site. Rankings use cosine similarity in both modes.
Physical checks explain the rankings without changing them.
In memory, use `match_tiles(terrain, tile_ids)`. The function `lunar_tile_ids(terrain.patches)` maps prepared patch IDs to tile IDs.

Import the callable interface from `notebooks.modeling.terrain_similarity.pipeline`:
`ArtifactConfig`, `TerrainModel`, `compare_sites`, `match_tiles`, `lunar_tile_ids`, `run_inference`, and `run_tile_matching`.
The implementation is in `main.py`. The `__main__.py` file enables the package commands below.

```powershell
.\.venv\Scripts\python.exe -m notebooks.modeling.terrain_similarity.pipeline --list-sites
.\.venv\Scripts\python.exe -m notebooks.modeling.terrain_similarity.pipeline --moon-site Haworth --earth-site wadi_rum
```

The pipeline accepts full region IDs and readable names. Matching ignores spaces, underscores, hyphens, and capitalization.
It matches each eligible lunar patch against the selected Earth site's prepared patches, with all development folds included.
The `--top-k` default is 3. Use `--no-plots` to skip figures.
The selected regions must already exist in the accepted dataset. The command does not process arbitrary coordinates or raw elevation files.

Each run writes:

- `summary.json`: patch counts, median/mean best-patch cosine, median physical differences, the count of lunar patches with a candidate passing all five exploratory checks, and how often distinct Earth patches are used.
- `retrieval.csv` and `physical_comparison.csv`: all ranked pairs, Earth coordinates, cosine scores and measurements in their original units.
- `selected_patches.csv`: the prepared patches belonging to both selected sites.
- `report_examples.csv`: the highest, middle and lowest first-match score examples selected for the report.
- `provenance.json`: completion or failure status, exact settings, input/source hashes and code revision.

Tables and provenance live under `data/processed/terrain_similarity_pipeline/<run>/`.
Optional `REPORT.md`, pair maps, and slope and height distributions live under `reports/terrain-similarity-pipeline/<run>/`.
Deleting reports does not invalidate reusable data. Summaries cover all prepared lunar patches.
Visual examples show the highest, middle, and lowest first-match scores. They are not a random evaluation sample.

The comparison asks whether the Earth site contains terrain resembling the lunar site.
The median best-patch cosine is not a percentage of site similarity.
Larger Earth candidate pools offer more opportunities for a close match.
Repeated use of one Earth patch does not imply extensive matching terrain. Physical thresholds explain results without changing their rankings.
General accuracy and environmental, access, or equipment suitability remain unvalidated.

The [configuration](modeling/terrain_similarity/pipeline/config.json) pins local training, dataset, and orientation runs.
The loader rejects changed hashes or mismatched models, datasets, scalers, patch IDs, support views, and inference policies.
Use `--config path/to/config.json` for another accepted set of files.
Use `--rebuild-cache` to regenerate embeddings with the saved weights and scaler. It checks rotation and reflection consistency.
It writes `embeddings.npz`, `preprocessing.json`, `patches.csv`, and `orientation_checks.csv` into the new data run.
To reuse the cache, set `orientation_run` in a configuration copy to the printed data-run path.
A failed cache validation does not trigger automatic rebuilding.

## Python helpers and tests

Python helpers live in `preprocessing/`, `exploration/`, and `modeling/terrain_similarity/`.
Common raster, terrain-measurement, validation, and report utilities live in `shared/`.
Imports use the `notebooks` package from the repository root. Each notebook locates that root automatically.

From the project root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s notebooks -t . -v
```

Shared and cross-stage tests live in `shared/tests/`. Dataset and CNN tests live in `modeling/terrain_similarity/tests/`.
These tests check processing and analysis behavior. They do not validate source accuracy or mission suitability.
