# LEAP: Lunar Exploration & Assessment Platform

[Live app](https://lrxa2.github.io/NASA-Space-Apps-Challenge-2026/) · [Source code](https://github.com/LRXA2/NASA-Space-Apps-Challenge-2026) · [Walkthrough](app/README.md#walkthrough) · [Research notebooks](notebooks/README.md)

LEAP (Lunar Exploration & Assessment Platform) compares lunar south-pole terrain with Earth sites that could support mission training.
Choose a lunar patch to see the models' rover and on-foot predictions. Compare its Earth matches using terrain measurements.
Environment scenarios score Operations and Survival separately.
This is a proof of concept for the NASA Space Apps Challenge 2026.

The repository includes the web app, terrain models, environment scorer, data download scripts, and research notebooks.
The integration pipeline joins model outputs by lunar tile and prepares the results for the app.

## What the app does

- Browse seven lunar terrain regions and 2,910 patches, each 960 m square on a 30 m grid.
- Compare 15 Earth matches per patch across five field sites. See similarity scores, five physical checks, and terrain grids together.
- Inspect environment scenarios for 17 candidate regions and six Apollo reference sites. See the input assumptions and reasons for gate results.
- Upload an environment CSV and score it in the browser.

## Try it

Open the [live app](https://lrxa2.github.io/NASA-Space-Apps-Challenge-2026/).
Follow the Region, Patch, Earth analogs, and Best match links in the header.
The examples show matches with high shape similarity but poor physical agreement.
See [the walkthrough](app/README.md#walkthrough) for a longer demonstration.

The app reads saved results. Environment uploads use Pyodide to run Python in a browser worker.
The first upload needs internet access. Your CSV stays in your browser.

## Run locally

Use Node 22.12 or newer. Run these commands from the repository root:

```bash
npm --prefix app ci
npm --prefix app run dev
```

For a production build, run `npm --prefix app run build`.
You can view the saved results without Python, model weights, or research downloads.
See the [app guide](app/README.md) for verification and export commands.

## Data and evidence

Lunar terrain uses [NASA/LRO LOLA terrain products](https://pgda.gsfc.nasa.gov/products/90).
Environment studies use [LOLA illumination and visibility maps](https://pgda.gsfc.nasa.gov/products/69), [LRO Diviner](https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_pcp/), and other mission data.
Earth comparisons use terrain datasets for Northern Arizona, Lanzarote, Atacama, Death Valley, and Wadi Rum.
The [notebook index](notebooks/README.md) links the analyses and model methods.
The [environment source register](env_algo_task/research/environmental_data.csv) lists the mission products and their uses.

Similarity is not a percentage or a suitability score.
The terrain models were trained on Earth data. Their accuracy on lunar terrain has not been measured.
Environment inputs are best-effort estimates. Gate thresholds are project test values, not NASA requirements.
Earth simulation readiness and operational suitability remain unvalidated.

## Development

For the full Python environment, install Python 3.12 and uv, then run `uv sync --locked --all-extras`.
See the [app guide](app/README.md#export-the-data) for pipeline and export commands.
Research inputs and model files stay local. The [data guide](data/README.md) lists the required files and their paths.

## AI assistance

AI was used for development, app, documentation, and repository cleanup.
