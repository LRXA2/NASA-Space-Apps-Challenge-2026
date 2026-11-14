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
- Domain rows come from the received columns, not a fixed list. In Darrel's current scorer (`dar_dev`, `eb4edbf`), Operations has thermal, solar illumination, dust, plasma charging, Earth visibility and soil. Survival has radiation, thermal, plasma charging and UV.
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
- Proposed export interface, to be added to the shared exporter:

```powershell
.\.venv\Scripts\python.exe app\scripts\export_data.py --input-dir temp --environment-file "temp/darrel pipeline results.csv" --output-dir app/public/data
.\.venv\Scripts\python.exe -m unittest discover -s app/scripts/tests -p "test_*.py"
npm --prefix app run build
npm --prefix app run preview
```

- `data/app_inputs/results.csv` in this checkout uses the old format (`final_habitability_score`, nine domains). Until Darrel sends new results, test against output from his current scorer run on his `sample_input.csv`.
- Cover empty scores, numeric zero, a `Fail` status, an unmapped ID, and an old-format file with at most five cases per test task.
- Exercise `Fail` and `Unknown` examples as clearly labelled test fixtures. Do not add them to the shipped scenario catalogue as real results.

## Decisions

- **Open:** Darrel's real results in the new format have not arrived. His current scorer disables hard gates, so all 83 sample rows pass. Ask him whether gates stay off for the demo.
- **Open:** The README supplies a region mapping, but teammate confirmation remains pending. The mapping task must record its source and review status.
- **Open:** Apollo display remains a team choice. This feature excludes the comparison chart and preserves the reference rows in the original input.

## My calls

- Put schema adaptation in the exporter, so every screen consumes the same normalized score and status fields.
- Keep that adapter in its own standard-library-only module. `environment-upload` runs it in Pyodide, so uploaded and precomputed results share one format.
- Read domain columns by prefix (`operations_*_score`, `survival_*_score`). Darrel changed the domain list on 13 Nov and may change it again.
- Display structured explanations beside the unmodified source failure text. Unknown reason formats remain readable as source text.
- Treat detailed checks as optional evidence. The absence of a detailed file must not hide existing compact results.

## Tasks

- [ ] Adopt the source-linked 17-region mapping and evidence labels. Record its review status and reject unknown mappings without attaching them to a guessed region.
- [ ] Add compact environment export for the `operations_*` and `survival_*` columns, with explicit missing-value handling. Verify row filtering, numeric zero, a blank final score, and source identity with focused tests.
- [ ] Reject old-format files (`final_habitability_score`) and unrecognized score columns with a readable error. Preserve blank values.
- [ ] Add optional detailed-check adaptation when its source is available, plus an explicit unavailable state when it is absent. Verify that scores never create invented gate outcomes.
- [ ] Publish the environment catalogue and render its region score summaries with evidence labels. Verify 17 scenario entries and seven preserved terrain associations.
- [ ] Add the environment tab with separate Operations and Survival sections: domain rows, status, readable failure reasons, and final score. Compare passing and blank-score scenarios with the source CSV.
- [ ] Add the sample input download: copy `sample_input.csv` from `dar_dev` into `app/public/` with its source commit, and add the labelled button. Verify the downloaded file matches the source byte-for-byte.
- [ ] Add environment-only and blocked-score region states. Verify ten disabled terrain selections, continued terrain access for a region with a blank score, and the complete production walkthrough.
