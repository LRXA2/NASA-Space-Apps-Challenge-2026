# NASA Space Apps 2026

Proof of concept: use a trained terrain CNN to retrieve plausible Earth training analogs for lunar terrain, with measured differences and clear limitations. **Earth and Moon only; Mars is excluded.**

Broad EDA is complete across five Earth sites and seven lunar regions. [Notebook 28](notebooks/modeling/terrain_similarity/28_training_data_readiness_and_baseline.ipynb) prepares terrain tensors; [notebook 29](notebooks/modeling/terrain_similarity/29_similarity_cnn_experiment.ipynb) trains the first similarity CNNs. Start with [notebook 35's terrain comparison](notebooks/modeling/terrain_similarity/35_slope_and_relative_elevation_demo.ipynb), using the rotation/reflection cache built by [notebook 34](notebooks/modeling/terrain_similarity/34_rotation_and_reflection_inference.ipynb). Both reuse saved weights on CPU. The demo shows ranked Earth locations, slope and relative elevation; outperforming the physical baseline is not required, and general retrieval accuracy remains unvalidated.

## Start here

- [Current findings and decisions](outline.md#current-findings-and-evaluation-decisions) — completed work, limitations and evaluation scope.
- [Notebooks](notebooks/README.md) — analysis index and running instructions.
- [Project outline](outline.md) — intended pipeline and sources.
- [Download instructions](download%20scripts/README.md) and [inventory](DOWNLOAD_CHECKLIST.md) — source acquisition.

## File paths

Paths below are relative to the repository root. See [notebooks/README.md](notebooks/README.md) for links to every numbered notebook.

```text
README.md                            Project overview
outline.md                           Pipeline, findings, decisions and data sources
DOWNLOAD_CHECKLIST.md                Acquisition and readiness checklist
.gitignore                           Files excluded from Git
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
    terrain_similarity/              28–35: dataset, CNN, diagnostics and demo
      terrain_dataset.py             Reproducible tensor and baseline builder
      terrain_learning.py            Tensor, split and normalization contracts
      similarity_cnn.py              Encoder, similarity head and training objective
      similarity_experiment.py       Training, inference and retrieval comparison
      candidate_coverage.py          Physical compatibility and ranking diagnostics
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
