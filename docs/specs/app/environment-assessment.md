# Inspect environment assessments

Needs: browse-regions
Due: 2026-11-15

## Goal

Inspect the environmental scenario associated with a lunar region without confusing it with the region's terrain predictions.
Include regions without terrain and explain missing or blocked scores. See [shared context](area.md#shared-context).

## Done when

- The region catalogue includes the 17 Artemis-labelled scenarios. The 30 synthetic and 30 dummy cases are excluded.
- An explicit, source-linked mapping joins `eda_001` through `eda_017` to readable regions. The first seven retain their matching terrain links.
- An environment tab shows two separate assessments, Operations and Survival. Each shows its own domain scores, status, failure reason and final score (`operations_score`, `survival_score`). It does not introduce a terrain domain.
- Domain rows come from the received columns, not a fixed list. Operations has six domains, including soil and Earth visibility. Survival has four domains. See the current architecture for their names.
- A `Fail` or `Unknown` status leaves that assessment's final score blank. Missing scores remain missing. Zero is displayed only when the source supplies zero.
- Compact input displays each assessment's status and preserved failure reasons. It identifies per-check detail as unavailable instead of deriving check outcomes from domain scores.
- If a traceable detailed export is supplied, the view shows its actual check values, units, thresholds, and statuses. Otherwise it remains usable with the compact CSV.
- The ten environment-only regions explain why terrain selection is unavailable. A blank environment score does not disable existing terrain screens.
- A download button on the environment tab gives Darrel's `sample_input.csv` unchanged, labelled as the scorer's input format. The team asked for this in chat on 13 Nov.
- A browser walkthrough checks passing, missing-data, and environment-only cases against the exported source records. It checks a failing case only if the received results contain one. The production build passes.

## Out of scope

- Recalculating environmental scores, adopting safety thresholds, combining Operations and Survival into one score, or treating scenario scores as uniform regional measurements.
- Apollo comparison charts, scoring an uploaded file (see `environment-upload`), historical mission reconstruction, and a real habitability assessment.

## Constraints

- Preserve source row IDs, original failure text, units where available, and the distinction between measured references, models, and test assumptions.
- State the evidence support beside the results. Darrel's README says only four map-geometry columns for `eda_001` to `eda_007` come from real LOLA maps. Their other values are test assumptions. Every value for `eda_008` to `eda_017` is assumed.
- Label the scores as scenario results from mostly assumed inputs, not as measured site assessments. Do not put them on the first screen of the demo flow as headline numbers.
- Label scenario time and footprint as unavailable when the received compact output omits them. Do not infer them from a display name.
- Domain scores and status are different fields. A high domain score cannot override a `Fail` status.
- Thermal and plasma charging appear in both assessments, sometimes with different rules. Show them under each assessment. Do not merge them.
- The current scorer writes `Pass`, `Fail` and `Unknown`. The older file used `Passed` and `Failed`. Display one wording.
- Do not merge environment and terrain scores. Keep access to each independent assessment.
- Keep each task within three files and three functions or five test cases. Missing future columns are not a reason to fabricate data.

## Verify

- Seam: export the actual environment CSV and navigate from the region catalogue to its environment tab.
- Existing integrated export interface. It reads compact and matching detailed results from the selected bundle:

```powershell
.\.venv\Scripts\python.exe app\scripts\export_data.py --pipeline-run data/processed/moon_pipeline/<run> --output-dir app/public/data
.\.venv\Scripts\python.exe -m unittest discover -s app/scripts/tests -p "test_*.py"
npm --prefix app run build
npm --prefix app run preview
```

- `data/app_inputs/results.csv` is an obsolete input for this exporter. Use the bundle's Operations/Survival files, or isolated test fixtures.
- Cover empty scores, numeric zero, a `Fail` status, an unmapped ID, and an old-format file with at most five cases per test task.
- Exercise `Fail` and `Unknown` examples as clearly labelled test fixtures. Do not add them to the shipped scenario catalogue as real results.

## Decisions

- **Resolved, 2026-11-14:** Darrel enabled hard gates. The app now uses the gated Operations/Survival run and its detailed evidence.
- **Resolved, 2026-11-14:** Darrel confirmed the 17-region mapping in D3. Only the first seven rows join to terrain.
- **Resolved, 2026-11-15:** Darrel permits the Apollo references with best-effort input labels. Show them in a separate reference group. No comparison chart, terrain coverage, or suitability claim is added.

## My calls

- Put schema adaptation in the exporter, so every screen consumes the same normalized score and status fields.
- Keep that adapter in its own standard-library-only module. `environment-upload` runs it in Pyodide, so uploaded and precomputed results share one format.
- Read domain columns by prefix (`operations_*_score`, `survival_*_score`). Darrel changed the domain list on 13 Nov and may change it again.
- Display structured explanations beside the unmodified source failure text. Unknown reason formats remain readable as source text.
- Treat detailed checks as optional evidence. The absence of a detailed file must not hide existing compact results.

## Tasks

- [x] Adopt the source-linked 17-region mapping and evidence labels. Record its review status and reject unknown mappings without attaching them to a guessed region.
- [x] Add compact environment export for the `operations_*` and `survival_*` columns, with explicit missing-value handling. Verify row filtering, numeric zero, a blank final score, and source identity with focused tests.
- [x] Reject old-format files (`final_habitability_score`) and unrecognized score columns with a readable error. Preserve blank values.
- [x] Add optional detailed-check adaptation when its source is available, plus an explicit unavailable state when it is absent. Verify that scores never create invented gate outcomes. Checked 2026-11-14: the 27 app-script tests cover detailed evidence, missing evidence, malformed gates, and compact/detailed disagreement. The TypeScript and production build also pass.
- [x] Publish the environment catalogue and render its region score summaries with evidence labels. Verify 17 scenario entries and seven preserved terrain associations.
- [x] Add the environment tab with separate Operations and Survival sections: domain rows, status, readable failure reasons, and final score. Compare passing and blank-score scenarios with the source CSV. Historical check: only passing scenarios were compared in the earlier gates-off run. The current export has three Operations failures and their blank scores. No fresh browser check was run in this update.
- [x] Add the sample input download: copy `sample_input.csv` from `dar_dev` into `app/public/` with its source commit, and add the labelled button. Verify the downloaded file matches the source byte-for-byte. Note, 14 Nov: the source is `env_algo_task/env_pipeline/sample_input.csv` on `main`. The export records its SHA-256, not a commit.
- [x] Add environment-only and blocked-score region states. Verify ten disabled terrain selections, continued terrain access for a region with a blank score, and the complete production walkthrough. Historical preview: ten regions showed "No terrain data". The earlier gates-off run had no blank score. Current source data contains failed Operations assessments, which still need a fresh browser walkthrough.

## Results

Reconciled on 2026-11-15 against `8769b86` and the current committed `environment.json`.
All 23 published scenarios have per-check evidence. Operations and Survival hard gates are active.
The 17 Artemis scenarios have Operations 14 Pass / three Fail and Survival 17 Pass. Re-exported 2026-11-15 after the input reconciliation in [team-blockers.md](../../team-blockers.md#scorer-reconciliation-resolved-2026-11-15).
Darrel's T3 answer is recorded in [team-blockers.md](../../team-blockers.md).
Gareth's `8769b86` presents six Apollo scenarios separately with best-effort input labels, including on their detail pages. The local duplicate was removed during reconciliation.
They do not change the 17-region summary or imply measured site suitability.
`npm --prefix app run check:browser` checks the failed `eda_007` page, environment-only `eda_008`, Apollo reference, and all 23 list entries.
Both desktop and 375 px layouts pass automated accessibility and page-overflow checks.
All 29 app-script tests and the production build pass.
Final acceptance and a real screen-reader pass remain open.
