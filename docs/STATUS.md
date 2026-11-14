# Status

> **Remove before submission.** This is an internal progress log for the team. Delete it before the Space Apps submission on 2026-11-15.

Updated 2026-11-14 (late evening). It replaces Ian's 13 Nov status file, which was out of date and has been removed. How the parts fit together is in [architecture.md](architecture.md). Open questions and every teammate answer are in [team-blockers.md](team-blockers.md).

## Where things stand

- **Branch:** `gareth/exploration-theme`, made from `gareth/app` at `f8820ed`. The theme work below is **not committed yet**; nothing has been pushed or merged.
- **Pipeline run in the app:** `moon_pipeline/20261114T081013177916Z_da70aa`, region scope, Darrel's gated config. Its terrain and Earth matches are identical to earlier runs; only the environment results changed.
- **Teammate answers:** Darrel D1–D5, Aarron A1–A4 and Hanxi H1–H3 are all answered and recorded word for word. The whole-team questions T1–T7 are still open.

## Done

| Area | State |
| --- | --- |
| Environment gates | Darrel's config has hard gates on (D1). Artemis: Operations 14 Pass and 3 Fail (eda_007 Connecting Ridge Extension, eda_012, eda_014: Earth visibility below 0.30), Survival 17 Pass. Fail shows the scorer's reason. Whether gates are on is read from the config (`hard_gates` in `environment.json`); an assessment with no active gate would show "Pass · gates off" |
| Per-check gate evidence (D2, D4) | `run_all` also writes `environment_detailed.csv`. The export uses it after checking it matches the compact file. The scenario page lists each gate under its assessment: value, rule (≥, ≤ or between, and when a duration threshold is capped to a short time window), Pass/Fail/Unknown, the reason for Unknown, and Darrel's "not a NASA limit" rationale. Uploads run in detailed mode and show the same table. The region list is the "General" view (two scores), the scenario page the "Details" view |
| Strict mode (D5) | A blank required input gives Unknown with a reason (for example "Missing required measurement or time window"), not an error. Checked in the scorer and in a browser upload |
| Bug report fixes | Pair page relief and IDs: not a data bug (query ID names the centre cell; relief is p95 − p5 vs the patch page's max − min; both match the drawn grid on all 2,910 tiles). Now labelled and explained. Heading gaps fixed. Pair URLs accept the numeric candidate. Region table paged at 50 rows |
| Scorer hashes | The export writes and hashes LF bytes and `.gitattributes` keeps `app/public/data/` text files LF, so a host building from a clean clone serves files that match their hashes |
| Overview and pair | Polar overview map of the 7 regions on the front page. One cursor shared by the four pair grids. Slope and elevation distribution charts on the pair page (Ian's commit `b0b4641`) |
| Featured tiles | Draft in [featured-tiles.md](featured-tiles.md), still valid for the current run (Earth matches unchanged) |
| Integration | `run_all` writes `environment.csv` (compact) and `environment_detailed.csv`. Fixes G1–G3 |
| Tile join | All 2,910 tiles have both an Aarron and a Hanxi patch. Their Moon grids agree |
| App pages | Regions (with polar map), region map and paged table, patch, Earth analogs, Moon–Earth pair, environment list and scenario, environment upload |
| Environment upload | Darrel's unmodified scorer in Pyodide 0.28.3 in a Web Worker, detailed mode. Output identical to the CLI for all 83 sample rows (`config_sha256` differs only by line endings, so the parity check masks it) |
| ONNX | Both CNNs export and match the saved outputs (2.2e-7 and 5.4e-7, no class changes). Both scalers are applied outside the ONNX models, so they ship as separate files (A2, H1). Not used by the app yet |
| Tests | Integration 19 (1 skipped), app scripts 29, notebooks 79. Type-check and build pass. Scorer parity: 83 rows identical |
| Exploration theme, phases 1–4 | Built to [ui-theme-implementation.md](ui-theme-implementation.md). Dark only (the light theme and `useColorScheme` are gone). Tokens from DESIGN.md; fonts self-hosted with `@fontsource` (Space Grotesk, Inter, IBM Plex Mono: three new dependencies). Starry page background. New shell: brand, section pills, the four-step demo path (`app/src/demo.ts`) and a footer with the run IDs. Panels, pill buttons and badges, segmented map toggle, themed tables and Limits panel ("Limits of this page"). Class fills (solid, 135° and 45° stripes). Magma slope and navy-to-white height ramps on the existing fitted, shared domain. OSM tiles darkened with a CSS filter. Polar map redrawn as nodes over dashed true-extent squares, with selected and Operations-Fail styles. New home page: hero with stats, sky panel, polar map, seven region cards, "Looks alike, measures different" and limits |
| Owner decisions (14 Nov) | Self-host fonts; CSS filter on the OSM tiles; keep the nav label "Try your own data"; keep the fitted, shared slope domain (only the colours changed) |
| Export | `regions.json` entries now carry `rover_class_counts`, `patch_size_m` and `spacing_m` (2 new tests). Re-exported: only `regions.json` changed. `app/public/data/sky.json` (473 stars to magnitude 5 in the panel's frame, plus Canopus and Sirius) was trimmed from `design/exploration-theme/sky/sky.json`; it is not made by the export |
| Accessibility | axe-core: no violations on all 8 routes at 1440 px and 375 px, and on the upload results with every row expanded. No horizontal scroll at either width. Tab reaches the header, demo path, map nodes, toggles, grids and pager with a visible ring; the arrow keys move the shared cursor on all four pair grids. Contrast checked by calculation: every text colour is at least 4.7:1 on the lightest panel fill. Not tried with a real screen reader (NVDA) |

## Not done

- **Deploy:** waiting on the host (T2).
- **Terrain upload (ONNX):** every model question is answered (A1 format: 42 × 42 `.asc` at 30 m, metres, no gaps; A2 and H1/H2: ship both models as ONNX with their scalers and Aarron's embedding bank; H3: show the direct slope rule beside the CNN, never overwriting it). Still waiting on the team's scope decision (T1).
- **Apollo rows:** exported, hidden until T3 (`SHOW_APOLLO` in `app/src/pages/EnvironmentPage.tsx`). With gates on, all six Apollo rows pass both assessments.
- **Per-tile environment:** needs the 4 LOLA maps and a `run_all` rerun (T4).
- **Darrel's status counts don't fully match ours.** He reported Operations 60/21/2 (matches) and Survival 68 Pass, 11 Fail, 4 Unknown. With the committed config and input we get Survival 70/11/2 (Unknown: dummy_003, dummy_007). Ask him which 4 IDs are Unknown; his run may have used an uncommitted input or config.
- **Exploration theme, phase 5** (per-screen additions, in this order, after the owner has seen phases 1–4): patch-page "Closest Earth terrain by shape" banner; analogs callouts and sort toggle; pair rank tabs, two-colour heading and check bands; environment page split into terrain and environment-only groups; region page "Five patches to start with" (blocked on T6). Terrain upload (screen 9) is not to be built (T1).
- **Theme gaps:** the home page loads the whole Earth grid file (9.1 MB) to draw two slope tiles, the same file the pair page loads. The region page has no Limits panel (it never had one). The demo path's "Best match" step is a fixed candidate ID in `demo.ts`; the home page computes the best physical fit from the data, and the two agree for this run.
- **Not checked:** a pass with a real screen reader.

## Next, in order

1. Review and commit the per-check gate evidence (code, tests, data export and docs).
2. Ask Darrel about the Survival Unknown count (above).
3. Host decision (T2), then deploy and check the hosted walkthrough.
4. Choose featured tiles for the demo (T6) from [featured-tiles.md](featured-tiles.md).
5. Review and commit the theme (phases 1–4), then phase 5 of [ui-theme-implementation.md](ui-theme-implementation.md).
6. If T1 says yes: terrain upload with ONNX and the `.asc` template.
7. Submission: demo script, project page, and delete this file.

## Stale elsewhere

- Parts of `specs/app/` (moved from `design/docs/specs/app/` on 14 Nov) describe earlier states. Use the other files in `docs/` instead.
- `handoff/developer_handoff_2026-11-13.md` (moved from `design/handoff/` on 14 Nov) lists blockers that are now resolved (see [team-blockers.md](team-blockers.md)).
