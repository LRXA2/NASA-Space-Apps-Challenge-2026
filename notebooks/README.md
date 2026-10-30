# Notebooks

Read the [EDA summary](../EDA_PLAN.md) for current findings and next steps. This page is an index; detailed methods and results are in the notebooks and their saved reports.

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

## Run a notebook

Notebooks 07–12 include historical diagnostics. The old Arizona terrain gaps were a corrected processing defect; lunar elevation holes came from our support mask. Obsolete standalone terrain previews in 07 and 10 have been removed. Use 14 onward for current terrain comparisons; 09 and 12 retain explicit before/after evidence.

Use the existing Python 3.12 `.venv`. If dependencies need installing, close its running kernels first, then run from the project root in PowerShell:

```powershell
uv pip install --python .\.venv\Scripts\python.exe -r notebooks/requirements-processing.txt
```

Select `.venv\Scripts\python.exe` as the notebook kernel. Save configuration changes, then run cells from the top. Download instructions are [separate](../download%20scripts/README.md).

- **To read existing findings:** open the relevant notebook; no preprocessing rerun is needed.
- **To rerun EDA:** check the notebook's pinned input paths. Running every notebook in numeric order does not automatically select new outputs.
- **To rebuild inputs:** process, validate coverage/hashes/masks, then explicitly select the accepted runs for EDA. Do not rerun notebook 01 merely to start analysis.

## Outputs and reproducibility

Processing writes versioned runs under `data/processed/`; analysis writes to `notebooks/diagnostics/` or `reports/`. Reruns create new directories. Use completed manifests and verify consumed input hashes; interrupted folders may be partial.

Exact inputs, parameters and source hashes are recorded in notebook configuration and provenance. Historical reports retain their original paths and may reference retired working documents. Preserve raw data and existing run records. Scientific limitations and evaluation rules are summarized in [EDA_PLAN.md](../EDA_PLAN.md).

Before staging notebooks in Git, use your editor's **Clear All Outputs** command and save. Embedded images are part of the notebook file and are not excluded by `.gitignore`. Code and notebook Markdown remain trackable; data, figures, reports and their provenance records stay local in the ignored output directories.

## Check the shared code

From the project root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s notebooks/tests -v
```

These focused tests check processing and analysis behavior; they do not validate source accuracy or mission suitability.
