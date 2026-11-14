# Status

> **Remove before submission.** This is an internal progress log for the team. Delete it before the Space Apps submission on 2026-11-15.

Updated 2026-11-14. It replaces `design/docs/STATUS.md` (Ian, 13 Nov), which is out of date. How the parts fit together is in [architecture.md](architecture.md). Open questions are in [team-blockers.md](team-blockers.md).

## Done

| Area | State |
| --- | --- |
| Branch | `main` merged into `gareth/app` (`668bf7c`). Integration and app work committed (`885f127`, `3b5937e`) and pushed. The changes in the next three rows are **not committed yet** |
| Scorer hashes | **Bug fixed.** The export hashed the Windows CRLF copies of the scorer files, but git stores LF, so on a host that builds from a clean clone the browser upload would refuse 3 of the 4 scorer files. The export now writes and hashes LF bytes, and `.gitattributes` keeps `app/public/data/` text files LF in every checkout |
| Overview and pair | Polar overview map of all 7 regions on the front page (regions.json now has each region's `extent_m`). One cursor shared by the four pair grids |
| Featured tiles | Draft in [featured-tiles.md](featured-tiles.md): 5 per region and a suggested demo path, for the team to choose from (T6) |
| Python setup | `.venv` with Python 3.12, repo requirements, CPU PyTorch and onnxruntime, on Gareth's Windows machine |
| Teammate data | Hanxi's inference run and Aarron's dataset, model and embedding cache copied into `data/processed/`. Weights copied into `notebooks/modeling/terrain_similarity/weights/` |
| Integration | `run_all` fixes G1–G3 (caveat follows the scope, `physical_comparison.csv` copied, POSIX paths). Current run: `moon_pipeline/20261114T023547307090Z_39a681`, region scope |
| Tile join | All 2,910 tiles have both an Aarron and a Hanxi patch. Their Moon grids agree |
| Export v2 | `app/scripts/export_data.py` reads the pipeline run. Writes patches with `tile_id`, Moon grids, analogs, Earth candidates and grids, environment, and scorer files (31 MB) |
| App pages | Region list, region map, patch page (plus best Earth match and region environment), **Earth analogs** (table and OpenStreetMap map), **Moon–Earth pair** (5 checks, 4 grids on shared scales), **environment** list and scenario pages, **environment upload** |
| Environment upload | Darrel's unmodified scorer in Pyodide 0.28.3 in a Web Worker. Output identical to the CLI for all 83 sample rows. Upload and an invalid file checked in headless Chrome |
| ONNX | Both CNNs export and match the saved outputs (2.2e-7 and 5.4e-7, no class changes). `app/scripts/check_onnx_parity.py`. Not used by the app yet |
| Tests | Integration 18 (1 skipped smoke test), app scripts 20, notebooks 79. App type-check and build pass. Scorer parity: 83 rows identical |
| Accessibility | axe-core: no violations on all 8 routes, light and dark. Keyboard: Tab reaches every control on every page, all with a visible focus style. Not tried with a real screen reader (NVDA) |
| Docs | `docs/` architecture, team blockers and this status. `app/README.md` updated for schema v2 |

## Not done

- **Deploy:** waiting on the host (T2).
- **Terrain upload (ONNX):** waiting on the upload scope (T1).
- **Apollo rows:** exported, but hidden until T3 is answered (`SHOW_APOLLO` in `app/src/pages/EnvironmentPage.tsx`).
- **Per-tile environment:** needs the 4 LOLA maps and a `run_all` rerun (T4).
- **Per-check environment evidence:** waiting on D2 (`--detailed`).
- **Not checked yet:** slope and height distribution charts, and a pass with a real screen reader.
- **Darrel's answers (D1, D4, D5)** are in [team-blockers.md](team-blockers.md). D1 still needs one clarification: whether "include all of them" means switching the hard gates on. Changing gates or weights from the upload page is not built.
- **Visual design:** placeholder styles only. Gareth is refining the design separately.

## Next, in order

1. Review and commit the uncommitted changes on `gareth/app` (scorer hash fix, overview map, linked cursor, featured tiles draft).
2. Host decision (T2), then deploy and check the hosted walkthrough.
3. Choose featured tiles for the demo (T6) from [featured-tiles.md](featured-tiles.md).
4. Apply the visual design.
5. If T1 says yes: terrain upload with ONNX and an `.asc` elevation template.
6. Submission: demo script, project page, and delete this file.

## Stale elsewhere

- `design/docs/STATUS.md` and parts of `design/docs/specs/app/` (especially `earth-analogs.md`) describe the situation before integration. Use `docs/` instead.
- `design/handoff/developer_handoff_2026-11-13.md` lists blockers that are now resolved (see the Resolved table in [team-blockers.md](team-blockers.md)).
