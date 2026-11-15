# Team blockers

Updated 2026-11-15. Questions are grouped by who can answer them. The hackathon ends 2026-11-15. When something is answered, write the answer and the date next to it. Don't delete it.

## Whole team

| # | Question | Why it matters | Answer |
| --- | --- | --- | --- |
| T1 | **Upload scope.** Environment only, or environment plus both CNNs? | Environment only: users edit Darrel's input CSV and see Operations and Survival scores. Adding the CNNs lets users upload an elevation grid and get rover and on-foot classes plus their closest Earth matches. That is the "new site through all pipelines" Aarron asked for. It costs roughly one extra day | "Keep environment-only uploads for this submission. Both CNNs can still be demonstrated through their existing catalogue results. Prioritize completing and verifying the submission; elevation uploads can follow later." (relayed to Gareth on 2026-11-15) |
| T2 | **Host.** Which host and account? | A host is needed for a public demo URL. | Deferred by Ian on 2026-11-14. Then on 2026-11-15: "Repo is now public so I will leave it to the app designer" (relayed to Gareth). Gareth chose GitHub Pages, deployed by `.github/workflows/pages.yml` from `main`. Live at <https://lrxa2.github.io/NASA-Space-Apps-Challenge-2026/> since 2026-11-15 |
| T3 | **Show the Apollo rows?** See [the six rows below](#apollo-reference-rows) | They score 95–97 (Operations) against 30–59 for the south-pole regions, which gives judges a reference point. But their inputs are partly modelled, and they are equatorial sites with no terrain data | "We can still present it from an ops/survivability standpoint, but we need to make it clear that the input values are based on best-effort estimates. We can still highlight 'potential' sites, and the NASA team can consider sending an unmanned rover to map the terrain and gather more accurate data. From there, they will have a clearer picture of the conditions." (Darrel, relayed by Ian on 2026-11-15; implemented by Gareth in `8769b86`) |
| T4 | **Environment per region or per tile?** | Per tile needs 4 LOLA maps (about 116 MB). Only 4 inputs then vary by tile. The rest stay region-wide assumptions | "Use per-region environment scores for this submission. Clearly label that every tile within a region shares the same environment scenario. Per-tile scoring can follow later, since most inputs would still remain region-wide assumptions." (relayed to Gareth on 2026-11-15). Already labelled on the patch and environment pages |
| T5 | Sign-off on the static architecture (no backend, exports committed) | Low risk, but nobody has confirmed it | "I thought we included an option for them to input a new set to test if needed? If not its fine ill leave it to yr" (relayed to Gareth on 2026-11-15). Gareth: yes, the static site includes the environment CSV upload, scored in the browser. Static architecture kept |
| T6 | Featured tiles for the demo: 3–5 per region, including one misleading high-cosine match | Makes the demo deterministic | "Use three featured tiles per region from the existing draft: a strong physical match, a high-cosine match with poor physical agreement, and a match outside Atacama." (relayed to Gareth on 2026-11-15). See [featured-tiles.md](featured-tiles.md) |
| T7 | Who reruns `integration.run_all` and the export when a model changes? | Currently Gareth | Proposed by Gareth, 2026-11-15, awaiting the team: Gareth reruns it by hand, only when a model, the scorer or its template changes, on a machine holding the `data/` inputs. Frozen for the submission. CI flags a stale scorer copy. Steps in [architecture](architecture.md#regenerating-the-export-t7) |
| T8 | Exploration theme or mission-control theme? | Sets the visual direction without changing the data pipelines | Resolved 2026-11-14: Aarron preferred exploration because the project supports reconnaissance. Gareth confirmed at 20:12 that he would implement the exploration theme. The theme is merged in `gareth/app`; final visual review remains pending. |

### Apollo reference rows

Historical scores below come from `moon_pipeline/20261114T014850261930Z_7de0f3`, before gates were enabled. They are not the current export's status record. The `_assumed` suffix identifies mixed mission records, models, and test assumptions. The current gated export contains all six references, both assessments pass, and the app presents them separately with best-effort input labels, following Darrel's T3 answer.

| ID | Operations | Survival |
| --- | --- | --- |
| `apollo_11_mare_tranquillitatis_assumed` | 97.31 | 82.39 |
| `apollo_12_oceanus_procellarum_assumed` | 94.87 | 76.06 |
| `apollo_14_fra_mauro_assumed` | 96.57 | 79.36 |
| `apollo_15_hadley_apennine_assumed` | 95.53 | 78.93 |
| `apollo_16_descartes_highlands_assumed` | 95.10 | 77.99 |
| `apollo_17_taurus_littrow_assumed` | 95.36 | 80.04 |
| For comparison: the 17 south-pole regions (`eda_001`–`eda_017`) | 29.67–59.23 | 42.02–70.14 |

## Darrel (environment scorer)

| # | Question | Answer |
| --- | --- | --- |
| D1 | Do hard gates stay off for the demo? With them off, all 83 rows previously passed without blank scores. | ``Darrel, 2026-11-14 11:17: "We can include all of them. Hard gates can be disabled in the config.yml which gives the team flexibility to choose what are considerations, as each mission is different." The gates are a per-mission choice made in `config.yml`. **Still to confirm with Darrel:** does "all of them" mean all the gates switched on, or all the rows shown? The demo uses `config.yml` as it is now (gates off)``<br><br>`[Darrel_14Nov_1130] Enable hard gates and thresholds to show Pass, Fail and Unknown, with reasons for Fail or Unknown.`<br><br>`[Darrel_14Nov_1500] I have updated config.yml to support this, please re-run on your end to ensure that it still works. Values are project-test thresholds, not NASA limits.` <br><br>Gareth, 2026-11-14: the "still to confirm" above is settled by Darrel's 11:30 and 15:00 answers: gates are on. Rerun `moon_pipeline/20261114T075446073217Z_af2e44` with his config works. Artemis: Operations 14 Pass and 3 Fail (eda_007, eda_012, eda_014, all Earth visibility below 0.30), Survival 17 Pass. Test rows include Unknown with reasons. Browser and CLI scores are identical for all 83 rows |
| D2 | Does `--detailed` (`*_details` JSON) include each check's value, threshold and Pass/Fail/Unknown status? | `[Darrel_14Nov_1500] Yes, for enabled gates. Parse *_details, then its hard_gate_details JSON string for the value, threshold/bounds, status and reason. Display Passed/Failed as Pass/Fail. Scoring-only inputs do not have gate verdicts.` |
| D3 | Confirm the region mapping `eda_001`-`eda_017` in the integration. | `[Darrel_14Nov_1500] Confirmed against the README. Only eda_001-eda_007 have terrain joins; eda_008-eda_017 are environment-only.` See [region mapping](../env_algo_task/env_pipeline/README.md#one-input-csv). |
| D4 | Is it OK to run `env_pipeline.py` and `config.yml` unchanged in Pyodide, using `sample_input.csv` as the template? | ``Darrel, 2026-11-14 11:17: yes. (1) Users update the input file. (2) `config.yml` holds the hard-gate toggles and the column weights. (3) Show the ID, Operations score and Survival score, with a "see more info" for the domain scores. Point 3 is what the upload page already does. Letting users change the gates or weights in the browser is not built`` <br><br> `[Darrel_14Nov_1130] Please refer to the updated config.yml as i updated some logic (Qn D1). We can have 2 views: 'General' which only has Ops score and Survival score, and 'Details' which list down all the scoring matrix . Please do take note that the input values are best effort.` |
| D5 | Which input columns could an outside user realistically fill in? | ``Darrel, 2026-11-14, **preliminary, to be confirmed:** hard to say without knowing what data NASA has; his values come from various online datasets. For now, the upload page follows his datasets (the template columns as they are)`` <br><br> `[Darrel_14Nov_1500] Users manually enter id, start_utc and stop_utc. Other values can come from NASA data where available. Otherwise, set pipeline_mode: available_data in config.yml to allow blanks, or set enabled: false to exclude an unavailable domain. hard_gates_enabled: false only disables gate checks.` See [input guide](../env_algo_task/env_pipeline/README.md#where-and-how-to-obtain-the-input-values). |

## Aarron (similarity CNN)

| # | Question | Answer |
| --- | --- | --- |
| A1 | For a CNN upload, what should a user supply? Both models read elevation-derived grids, not images. Proposal: a 42 × 42 elevation grid at 30 m (`.asc`) | Aarron, 2026-11-14: "Yes, use a 42 × 42 elevation grid at 30 m spacing in .asc format, with elevations in metres and no missing values. The app should derive the required inputs separately for each CNN." |
| A2 | Is it OK to ship the model as ONNX plus the Earth embedding bank in the site? The browser output matches Python to 2.2e-7 | Aarron, 2026-11-14: "Yes, it's OK to ship my similarity model as ONNX, together with its saved scaler and matching Earth embedding bank, in the site." The scaler (`scaler_full_context.json`) is applied outside the ONNX model, so it ships as its own file |
| A3 | Is top 3 per Earth site (15 matches per tile) enough, or should `top_k_per_site` change? | Aarron, 2026-11-14: "Yes, keep top 3 per Earth site—15 matches per tile across the five sites." |
| A4 | Atacama is the best match for about 88% of tiles, and it has the most Earth patches. Is that expected, and how should we explain it? | Aarron, 2026-11-14: "Yes, Atacama's dominance is plausible. It has 3,078 of the 5,693 Earth patches, giving it more opportunities to contain a close match. When I sampled 32 candidates per site over 100 repetitions, its median winning share dropped from 89.2% to 38.1%. This shows that reference-bank size substantially affects the result, although it does not fully explain Atacama's frequent selection. It means Atacama most often supplies the highest terrain-similarity match in our current collection. Not that it is the best operational analogue." |

## Hanxi (walkability CNN)

| # | Question | Answer |
| --- | --- | --- |
| H1 | Is model run `20261112T103924450917Z_bd0fc2` the one to ship? It is not in `data/README.md` because `run_all` doesn't need it, but the upload would | Hanxi, 2026-11-14: "Yes. Run 20261112T103924450917Z_bd0fc2 is the selected combined rover + terrain-walkability model currently referenced by lunar inference. Ship its frozen model weights and training-derived scaler together." |
| H2 | Is it OK to ship the model as ONNX? The browser output matches `predictions.csv` to 5.4e-7 with no class changes | Hanxi, 2026-11-14: "Yep its fine" |
| H3 | For an uploaded grid, should the direction threshold and the direct slope-rule check run as in `run_lunar_human_walkability.py`? | Hanxi, 2026-11-14: "The direct slope rule separately is a separate sanity check, using the original physical slope values and not normalized values. You can display CNN prediction, direct-rule result and whether they agree. The rule should not overwrite the CNN prediction." The patch page already shows all three and never overwrites the CNN class |

## Ian (app)

| # | Question | Answer |
| --- | --- | --- |
| I2 | Parts of `docs/specs/app/earth-analogs.md` described independent query IDs and notebook-only coverage. Reconcile them with the shared `tile_id`? | Resolved 2026-11-15: specs now describe integrated exports, shared tile IDs, numeric grids, and current commands. Historical tasks and decisions remain identified. |

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
| G1: `run_all` caveat always claimed per-tile values | `caveat()` now follows `environment_scope` | 2026-11-14 |
| G2: `physical_comparison.csv` missing from `moon_pipeline/<run>/` | `run_all` now copies it | 2026-11-14 |
| G3: `stage_runs` paths used backslashes | Written as POSIX paths | 2026-11-14 |

## Remaining scorer reconciliation

The recorded gated rerun produced Operations 60 Pass / 21 Fail / 2 Unknown and Survival 70 / 11 / 2.
Darrel reported Survival 68 / 11 / 4. Ask which four IDs are Unknown and compare exact input/config versions.
This does not change the committed Artemis subset: Operations 14 / 3 / 0 and Survival 17 / 0 / 0.
