# NASA Space Apps 2026

Find Earth training analogs for lunar terrain and assess mission-specific environmental constraints. **Earth and Moon only; Mars is excluded.**

Broad EDA is complete across five Earth sites and seven lunar regions. Next: define a mission/training scenario and an independent relevance rubric before model development.

## Start here

- [EDA summary](EDA_PLAN.md) — key problems, decisions and next steps.
- [Notebooks](notebooks/README.md) — analysis index and running instructions.
- [Project outline](outline.md) — intended pipeline and sources.
- [Download instructions](download%20scripts/README.md) and [inventory](DOWNLOAD_CHECKLIST.md) — source acquisition.

## File paths

Paths below are relative to the repository root. See [notebooks/README.md](notebooks/README.md) for links to every numbered notebook.

```text
README.md                            Project overview
EDA_PLAN.md                          EDA findings, problems and next steps
outline.md                           Pipeline and data sources
DOWNLOAD_CHECKLIST.md                Acquisition and readiness checklist
.gitignore                           Files excluded from Git
download scripts/
  README.md                          Download commands and source details
  download_*.py                      Dataset downloaders
  tests/                             Downloader tests
notebooks/
  README.md                          Notebook index and running instructions
  requirements-processing.txt        Python dependencies
  setup/                             01: original data organization
  preprocessing/                     02–13, 19, 21, 26: processing and checks
  exploration/                       14–18, 20, 22–25, 27: EDA
  processing.py                      Shared processing operations
  osm_processing.py                  OSM extraction and geometry handling
  inspection.py                      Shared validation utilities
  *_analysis.py                      Terrain, candidate and environment helpers
  tests/                             Processing and analysis tests
  diagnostics/                       Local analysis reports, tables and figures
data/
  raw/                               Local downloaded source data
  processed/                         Local versioned processing runs
  manifests/                         Local organization and acquisition records
reports/                             Local audits and maintenance records
.scratch/                            Temporary local working files
.venv/                               Local Python environment
```

Git keeps code, tests, documentation and notebooks with cleared outputs. Data, reports, diagnostics, scratch work and local environments are ignored; cloning the repository will not include those files.

Existing findings can be read without rerunning preprocessing. Models and operational suitability scores have not been validated.
