# Team blockers

Open questions as of 2026-11-14, grouped by who can answer them. The hackathon ends 2026-11-15. When something is answered, write the answer and the date next to it. Don't delete it.

## Whole team

| # | Question | Why it matters | Answer |
| --- | --- | --- | --- |
| T1 | **Upload scope.** Environment only, or environment plus both CNNs? | Environment only: users edit Darrel's input CSV and see Operations and Survival scores. Adding the CNNs lets users upload an elevation grid and get rover and on-foot classes plus their closest Earth matches. That is the "new site through all pipelines" Aarron asked for. It costs roughly one extra day | |
| T2 | **Host.** GitHub Pages or Vercel? Who owns the account? | The repo is reported private. GitHub Pages then needs an admin (or a public repo). The Vercel CLI needs only an account | |
| T3 | **Show the Apollo rows?** See [the six rows below](#apollo-reference-rows) | They score 95–97 (Operations) against 30–59 for the south-pole regions, which gives judges a reference point. But their inputs are partly modelled, and they are equatorial sites with no terrain data | |
| T4 | **Environment per region or per tile?** | Per tile needs 4 LOLA maps (about 116 MB). Only 4 inputs then vary by tile. The rest stay region-wide assumptions | |
| T5 | Sign-off on the static architecture (no backend, exports committed) | Low risk, but nobody has confirmed it | |
| T6 | Featured tiles for the demo: 3–5 per region, including one misleading high-cosine match | Makes the demo deterministic | |
| T7 | Who reruns `integration.run_all` and the export when a model changes? | Currently Gareth | |

### Apollo reference rows

From `environment.csv` in `moon_pipeline/20261114T014850261930Z_7de0f3`, scored by Darrel's current scorer with hard gates off. The `_assumed` suffix is Darrel's: each row combines mission records, models and test assumptions, and spacecraft potential is blank (his README, "Apollo reference inputs").

| ID | Operations | Survival |
| --- | --- | --- |
| `apollo_11_mare_tranquillitatis_assumed` | 97.31 | 82.39 |
| `apollo_12_oceanus_procellarum_assumed` | 94.87 | 76.06 |
| `apollo_14_fra_mauro_assumed` | 96.57 | 79.36 |
| `apollo_15_hadley_apennine_assumed` | 95.53 | 78.93 |
| `apollo_16_descartes_highlands_assumed` | 95.10 | 77.99 |
| `apollo_17_taurus_littrow_assumed` | 95.36 | 80.04 |
| For comparison: the 17 south-pole regions (`eda_001`–`eda_017`) | 29.67–59.23 | 42.02–70.14 |

Options: leave them out; show them as a small reference strip on the environment screen; or list them as regions. They have no terrain or Earth analogs, so listing them as regions is the weakest option.

## Darrel (environment scorer)

| # | Question | Answer |
| --- | --- | --- |
| D1 | Do hard gates stay off for the demo? With them off, all 83 rows pass and no score is ever blank | |
| D2 | Does `--detailed` (`*_details` JSON) include each check's value, threshold and Pass/Fail/Unknown status? The environment tab wants per-check evidence | |
| D3 | Confirm the region mapping `eda_001`–`eda_017` (now hard-coded in `integration/moon_sites.py`) | |
| D4 | Is it OK to run `env_pipeline.py` and `config.yml` unchanged in the browser (Pyodide) for the upload, and to point users at `sample_input.csv` as the template? | |
| D5 | Which input columns could an outside user realistically fill in? This decides how the upload page is worded | |

## Aarron (similarity CNN)

| # | Question | Answer |
| --- | --- | --- |
| A1 | For a CNN upload, what should a user supply? Both models read elevation-derived grids, not images. Proposal: a 42 × 42 elevation grid at 30 m (`.asc`) | |
| A2 | Is it OK to ship the model as ONNX plus the Earth embedding bank in the site? The browser output matches Python to 2.2e-7 | |
| A3 | Is top 3 per Earth site (15 matches per tile) enough, or should `top_k_per_site` change? | |
| A4 | Atacama is the best match for about 88% of tiles, and it has the most Earth patches. Is that expected, and how should we explain it? | |

## Hanxi (walkability CNN)

| # | Question | Answer |
| --- | --- | --- |
| H1 | Is model run `20261112T103924450917Z_bd0fc2` the one to ship? It is not in `data/README.md` because `run_all` doesn't need it, but the upload would | |
| H2 | Is it OK to ship the model as ONNX? The browser output matches `predictions.csv` to 5.4e-7 with no class changes | |
| H3 | For an uploaded grid, should the direction threshold and the direct slope-rule check run as in `run_lunar_human_walkability.py`? | |

## Ian (app)

| # | Question | Answer |
| --- | --- | --- |
| I2 | Parts of `design/docs/specs/app/earth-analogs.md` are obsolete: keying on Aarron's query IDs, starting from notebook 36, and the footprint task. The shared `tile_id` covers all 2,910 tiles. Update the spec or mark it superseded by [architecture.md](architecture.md)? | |

## Integration code (`integration/`)

| # | Item | Answer |
| --- | --- | --- |
| G1 | `CAVEAT` in `run_all.py` always claims per-tile LOLA values, even in region scope. Make it depend on `environment_scope` | |
| G2 | `physical_comparison.csv` isn't copied into `moon_pipeline/<run>/`. Copy it, so the export reads one folder | |
| G3 | `summary.json` → `stage_runs` paths use Windows backslashes. Write POSIX paths | |

## Resolved

| Item | How | Date |
| --- | --- | --- |
| Aarron's three data folders | Arrived (`temp/CNN terrain similarity stuff/`), copied into `data/processed/` | 2026-11-14 |
| Patch IDs didn't match between Aarron and Hanxi | Shared `tile_id`. 2,910 of 2,910 tiles join. Aarron's IDs use the centre cell, Hanxi's the top-left cell | 2026-11-14 |
| Search every tile against all Earth sites | `run_all` matches every tile against all 5 sites | 2026-11-14 |
| Earth matches as 32 × 32 grids | Available from Aarron's dataset tensors on the same scale as the Moon grids | 2026-11-14 |
| Darrel's new Operations/Survival format | On `main`, produced by `run_all` | 2026-11-14 |
| Windows setup | `.venv` built. All tests pass, and `run_all` runs on Windows | 2026-11-14 |
| `main` merged into `gareth/app` | Merge `668bf7c`, pushed | 2026-11-14 |
