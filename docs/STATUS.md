# Status

> **Remove before submission.** This is an internal progress log for the team. Delete it before the Space Apps submission on 2026-11-15.

Updated 2026-11-14. It replaces `design/docs/STATUS.md` (Ian, 13 Nov), which is out of date. How the parts fit together is in [architecture.md](architecture.md). Open questions are in [team-blockers.md](team-blockers.md).

## Done

| Area | State |
| --- | --- |
| Branch | `main` merged into `gareth/app` (`668bf7c`) and pushed. The branch is 0 commits behind `main` |
| Python setup | `.venv` with Python 3.12, repo requirements, CPU PyTorch and onnxruntime, on Gareth's Windows machine. All 106 tests pass (17 integration, 10 app export, 79 notebooks) |
| Teammate data | Hanxi's inference run and Aarron's dataset, model and embedding cache copied into `data/processed/`. Model weights copied into `notebooks/modeling/terrain_similarity/weights/` |
| Integration | `python -m integration.run_all --environment-scope region` runs in about 90 seconds. Output: `data/processed/moon_pipeline/20261114T014850261930Z_7de0f3/` |
| Tile join | All 2,910 lunar tiles have both an Aarron patch and a Hanxi patch. Their Moon grids agree to within 0.0002 m |
| Earth matches | Every tile matched against all 5 Earth sites, top 3 each (43,650 rows) |
| Environment | Darrel's new Operations/Survival format is produced by `run_all`. Joined by region, because the LOLA maps aren't downloaded |
| ONNX | Both CNNs exported and checked against the saved Python outputs: largest differences 2.2e-7 (similarity) and 5.4e-7 (walkability), no class changes. The check script is in a scratch folder, not the repo yet |
| App, schema v1 | Ian's app (on `gareth/app`) shows all 7 regions and 2,910 patches: region list, Leaflet patch map, patch page with rover and on-foot predictions, crossing directions, slope and elevation grids. It still reads Hanxi's run only |
| Docs | `docs/` created: architecture, team blockers, this status |

## In progress

Nothing. Waiting for the go-ahead on the plan below.

## Next, in order

1. **Export v2.** Read `moon_pipeline/<run>/`: add `tile_id` to patches, plus analogs, Earth candidates and Earth grids, and environment. Add tests.
2. **Earth analogs.** Analog page with a ranked table and an Earth map. Link every patch page to its analogs.
3. **Deploy.** Needs the host decision (T2). Redeploy after each later step.
4. **Environment tab.** Operations and Survival sections, plus the sample input download.
5. **Pair comparison.** Moon and Earth grids on one scale, and the 5 physical checks.
6. **Stretch: environment upload** (Pyodide).
7. **Stretch: CNN upload** (ONNX plus an elevation grid template). Depends on T1.
8. **Submission.** Demo script, project page, and delete this file.

## Waiting on decisions

See [team-blockers.md](team-blockers.md). The ones that block the plan:

- **T2, host:** blocks step 3.
- **T1, upload scope:** blocks step 7.
- **T3, Apollo rows:** affects step 4.
- **T4, environment per region or per tile:** affects step 4.
- **D1, hard gates:** affects step 4.

## Stale elsewhere

- `design/docs/STATUS.md` and parts of `design/docs/specs/app/` (especially `earth-analogs.md`) describe the situation before integration. Use `docs/` instead.
- `design/handoff/developer_handoff_2026-11-13.md` lists blockers that are now resolved (see the Resolved table in [team-blockers.md](team-blockers.md)).
