# Notebooks

Read the [current findings and decisions](../outline.md#current-findings-and-evaluation-decisions) for scope and next steps. This page is an index; detailed methods and results are in the notebooks and their saved reports.

The similarity CNN **proof of concept is complete**: lunar query to Earth candidates with explained examples. Notebook 35 is the main demonstration; notebook 34 builds its orientation-invariant cache. Notebook 33's rating forms remain optional follow-up work.

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
| Slope and relative elevation | [35 Eight-orientation Earth analog demo with physical comparisons](modeling/terrain_similarity/35_slope_and_relative_elevation_demo.ipynb) |

## Run a notebook

Notebooks 07–12 include historical diagnostics. The old Arizona terrain gaps were a corrected processing defect; lunar elevation holes came from our support mask. Obsolete standalone terrain previews in 07 and 10 have been removed. Use 14 onward for current terrain comparisons; 09 and 12 retain explicit before/after evidence.

Use a Python 3.12 `.venv`; on a fresh clone, create it with `uv venv --python 3.12 .venv`. If dependencies need installing, close its running kernels first, then run from the project root in PowerShell:

```powershell
uv pip install --python .\.venv\Scripts\python.exe -r notebooks/requirements-processing.txt
```

Select `.venv\Scripts\python.exe` as the notebook kernel. Save configuration changes, then run cells from the top. Download instructions are [separate](../download%20scripts/README.md). A fresh clone does not contain the pinned `data/` inputs, reference records or trained models: restore those local artifacts, or rebuild the required inputs and update the pinned paths before running the notebooks.

Notebook 28 uses the same dependencies. Its [configuration](modeling/terrain_similarity/terrain_dataset.json) pins accepted terrain runs and a development fold; the builder can also run from the root with `.\.venv\Scripts\python.exe notebooks/terrain_dataset.py`. Outputs go to ignored `data/processed/terrain_learning_readiness/`. Atacama and Leibnitz are EDA-exposed development holdouts, not final tests. No CNN is trained in 28.

Notebook 29 adds PyTorch: install `uv pip install --python .venv/Scripts/python.exe -r notebooks/requirements-modeling.txt` after the processing dependencies. Its [configuration](modeling/terrain_similarity/similarity_experiment.json) pins the notebook-28 dataset and defaults to `cuda:0`. Run the notebook or `.\.venv\Scripts\python.exe notebooks/similarity_experiment.py`. Four fixed experiments compare sampling and lunar support policies using one encoder architecture for both bodies. Models and tables stay in ignored `data/processed/terrain_similarity_cnn/`; figures stay in `reports/terrain-similarity-cnn/`. Training loss and baseline agreement are diagnostics, not relevance validation.

For the demonstration, run [34](modeling/terrain_similarity/34_rotation_and_reflection_inference.ipynb) once to build a separate cache under ignored `data/processed/terrain_similarity_orientation/<run>/`. It averages four rotations and their reflections for both bodies, checks transformed-query consistency and retains the original weights/scaler. [35](modeling/terrain_similarity/35_slope_and_relative_elevation_demo.ipynb) is already pinned to a completed run; if you rerun 34, copy its printed path into `ORIENTATION_RUN` in 35. Run 35 to see slope and relative elevation side by side, physical differences and distribution curves. Its `DEMO.md`, CSVs and figures go to ignored `reports/terrain-similarity-oriented-demo/<run>/`. These measurements explain CNN rankings without changing them.

- **To read existing findings:** open the relevant notebook; no preprocessing rerun is needed.
- **To rerun EDA:** check the notebook's pinned input paths. Running every notebook in numeric order does not automatically select new outputs.
- **To rebuild inputs:** process, validate coverage/hashes/masks, then explicitly select the accepted runs for EDA. Do not rerun notebook 01 merely to start analysis.

## Outputs and reproducibility

Processing writes versioned runs under `data/processed/`. EDA saves reusable tables, rasters and manifests under `data/processed/analysis/<run>/`; its final cell publishes figures and reports to `reports/analysis/<run>/`. Source research, unit policies and the frozen source-check sample live under `data/reference/`. Reruns create new directories. Run through the final export cell; interrupted folders may be partial.

Exact inputs, parameters and source hashes are recorded in notebook configuration and provenance. Keep referenced data runs and reference records intact. Reports are optional exports: deleting `reports/` does not invalidate reusable data manifests or notebook inputs. The relocation receipt at `data/reference/analysis-relocation-20261102.json` preserves original paths and hashes; historical source hashes describe the code or notes used at the time. Scientific limitations and evaluation rules are summarized in [outline.md](../outline.md#current-findings-and-evaluation-decisions).

Before staging notebooks in Git, **save with useful outputs retained**, including plots, tables and results. Review the saved outputs for errors, credentials and personal filesystem paths before publishing. Embedded images are part of the notebook file and are not excluded by `.gitignore`. Code, notebook Markdown and saved outputs remain trackable; standalone data, figures, reports and their provenance records stay local in the ignored output directories.

## Check the shared code

From the project root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s notebooks/tests -v
.\.venv\Scripts\python.exe -m unittest discover -s notebooks/modeling/terrain_similarity/tests -v
```

These focused tests check processing and analysis behavior; they do not validate source accuracy or mission suitability.
