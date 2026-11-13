# NASA Space Apps 2026

Proof of concept: use a trained terrain CNN to retrieve plausible Earth training analogs for lunar terrain, with measured differences and clear limitations. **Earth and Moon only; Mars is excluded.**

Broad EDA is complete across five Earth sites and seven lunar regions. [Notebook 28](notebooks/modeling/terrain_similarity/28_training_data_readiness_and_baseline.ipynb) prepares terrain tensors; [notebook 29](notebooks/modeling/terrain_similarity/29_similarity_cnn_experiment.ipynb) trains the first similarity CNNs. Start with [notebook 35's four-model comparison](notebooks/modeling/terrain_similarity/35_four_model_comparison.ipynb), which supports choosing the full-context, region-balanced CNN for the demonstration. [Notebook 36](notebooks/modeling/terrain_similarity/36_slope_and_relative_elevation_demo.ipynb) shows its terrain matches, using the rotation/reflection cache built by [notebook 34](notebooks/modeling/terrain_similarity/34_rotation_and_reflection_inference.ipynb). These notebooks reuse saved models and artifacts. The demo shows ranked Earth locations, slope and relative elevation; outperforming the physical baseline is not required, and general retrieval accuracy remains unvalidated.

## Start here

- [Current findings and decisions](outline.md#current-findings-and-evaluation-decisions) — completed work, limitations and evaluation scope.
- [Notebooks](notebooks/README.md) — analysis index and running instructions.
- [Project outline](outline.md) — intended pipeline and sources.
- [Download instructions](download%20scripts/README.md) and [inventory](DOWNLOAD_CHECKLIST.md) — source acquisition.

## Compare two prepared sites

Use the saved CNN from Python, without opening Jupyter:

```powershell
.\.venv\Scripts\python.exe -m notebooks.modeling.terrain_similarity.pipeline --moon-site Haworth --earth-site wadi_rum
```

The inputs are **whole prepared Moon and Earth regions**. For every eligible 960 m lunar patch, the pipeline finds the closest patches within the specified Earth site. It saves a summary, ranked matches, physical differences and visual comparisons. The median best-patch cosine describes these matches; it is not a similarity percentage or proof that the whole regions are equivalent.

Use `--list-sites` to see available names, `--top-k 3` to set candidates per lunar patch, or `--no-plots` for tables only. The [configuration](notebooks/modeling/terrain_similarity/pipeline/config.json) pins the saved model run, dataset and rotation/reflection cache. Weights live in `notebooks/modeling/terrain_similarity/weights/<run>/<view>/<sampling>/model.pt`; the model run still holds preprocessing, tables and provenance. `--rebuild-cache` explicitly rebuilds that cache with the same weights and scaler; it does not train a model. Required local artifacts must be present.

Reusable results go to `data/processed/terrain_similarity_pipeline/<run>/`; reports and figures go to `reports/terrain-similarity-pipeline/<run>/`. Each execution creates a new run. See the [pipeline details](notebooks/README.md#saved-model-site-comparison) for outputs and interpretation.

## Shared Moon tile IDs

The similarity CNN and the operability CNNs name the same 960 m lunar windows differently (centre row/column per view versus top-left row/column). [moon_tiles.py](notebooks/shared/moon_tiles.py) gives every window one `tile_id`, `<region>:<centre x>:<centre y>` in metres in the common lunar polar stereographic CRS, so their outputs can be joined:

```powershell
.\.venv\Scripts\python.exe -m notebooks.shared.moon_tiles --similarity-run data/processed/terrain_learning_readiness/<run> --operability-run rover=data/processed/terrain_operability_lunar_inference/<run> --operability-run walkability=data/processed/<walkability inference run>
```

It writes `moon_tiles.csv` (one row per tile, its bounds, each source's patch ID and `in_<source>` flags), `tile_sources.csv` (tile → source patch) and `coverage_by_region.csv` to `data/processed/moon_tiles/<run>/`. Sources whose windows are not on the same 960 m lattice are refused, for example when two lunar processing runs used different grids; rebuild one source from the other's lunar run rather than matching nearest tiles.

## Per-tile Moon site table

[integration/moon_sites.py](integration/moon_sites.py) turns an operability or walkability inference run into one row per `tile_id`: rover class and probabilities, human-terrain class (walkability runs), predicted crossing directions and count, and slope/relief figures. Add the environment pipeline's compact output with `--environment-csv` to attach its Operations and Survival scores, statuses and domain scores (`env_*` columns). These join **by region**: baselines `eda_001`–`eda_007` each summarise one of the seven terrain regions, so every tile in a region gets the same scores and `env_scope` is `region`. Other environment rows have no terrain tiles; they are skipped and listed in the run record. Tiles in regions without scores stay in the table with `env_assessed` false.

```powershell
.\.venv\Scripts\python.exe -m integration.moon_sites --terrain-run data/processed/terrain_human_walkability_lunar_inference/<run> --environment-csv path/to/results.csv
```

It writes `moon_sites.csv` and `summary_by_region.csv` to `data/processed/moon_sites/<run>/`. It joins existing outputs only and adds no new score.

## File paths

Paths below are relative to the repository root. See [notebooks/README.md](notebooks/README.md) for links to every numbered notebook.

```text
README.md                            Project overview
outline.md                           Pipeline, findings, decisions and data sources
DOWNLOAD_CHECKLIST.md                Acquisition and readiness checklist
.gitignore                           Files excluded from Git
integration/
  moon_sites.py                      Per-tile terrain table with optional environment join
  tests/                             Join and tile-ID checks
download scripts/
  README.md                          Download commands and source details
  download_*.py                      Dataset downloaders
  tests/                             Downloader tests
notebooks/
  README.md                          Notebook index and running instructions
  requirements-processing.txt        Python dependencies
  requirements-modeling.txt           Pinned PyTorch dependency for CNN experiments
  setup/                             01: original data organization
  preprocessing/                     02–13, 19, 21, 26: processing and checks
    osm_processing.py                OSM extraction and geometry handling
  exploration/                       14–18, 20, 22–25, 27: EDA
    *_analysis.py                    Candidate, environment, screening and source helpers
    select_source_check_sample.py    Reproduces the frozen development sample
  modeling/
    terrain_similarity/              28–36: dataset, CNN, diagnostics, comparison and demo
      terrain_dataset.py             Reproducible tensor and baseline builder
      terrain_learning.py            Tensor, split and normalization contracts
      similarity_cnn.py              Encoder, similarity head and training objective
      similarity_experiment.py       Training, inference and retrieval comparison
      model_weights.py               Shared checkpoint paths, saving and hash checks
      weights/                       Saved weights by run, view and sampling (Git-ignored)
      pipeline/                      Importable two-site comparison package
        main.py                      Main script, comparison and run orchestration
        artifacts.py                 Verified model, terrain and cache loading
        report.py                    Side-by-side terrain maps and report
        config.json                  Pinned inference artifacts and chosen variant
      candidate_coverage.py          Physical compatibility and ranking diagnostics
      model_comparison.py            Shared-location alignment and regional comparison summaries
      terrain_perturbation.py        Controlled vertical-scale sensitivity
      terrain_dataset.json           Accepted inputs and development fold roles
      similarity_experiment.json     Fixed training and retrieval configuration
      tests/                         Dataset, CNN transformation and leakage checks
  shared/
    processing.py                    Raster processing and versioned runs
    inspection.py                    Shared validation utilities
    patch_analysis.py                Terrain patch measurements
    retrieval_analysis.py            Physical terrain comparisons
    analysis_artifacts.py            Separates reusable data from disposable reports
    moon_tiles.py                    Shared lunar tile IDs joining similarity and operability outputs
    tests/                           Shared and cross-stage processing/analysis checks
data/
  raw/                               Local downloaded source data
  processed/                         Local versioned processing runs
    analysis/                        Reusable EDA tables, rasters and manifests
  reference/                         Source research, unit policies and frozen sample
  manifests/                         Local organization and acquisition records
reports/                             Disposable figures, reports and the current demo
  analysis/                          Regenerated EDA figures and reports
.scratch/                            Temporary local working files
.venv/                               Local Python environment
```

Git keeps code, tests, documentation and notebooks with saved plots, tables and other useful outputs so readers can view results without rerunning the analysis. Retain these outputs when committing notebooks. Standalone data, reports, scratch work and local environments are ignored; cloning the repository will not include those files. Keep required `data/` inputs; `reports/` can be deleted and regenerated.

The similarity CNN proof of concept is complete. Next: environmental, access and equipment checks. General analog relevance and operational suitability remain unvalidated.
