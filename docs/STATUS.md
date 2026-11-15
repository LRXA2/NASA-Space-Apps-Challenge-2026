# Status

## Now

Updated 2026-11-15 on `gareth/app`.
The app is live at <https://lrxa2.github.io/NASA-Space-Apps-Challenge-2026/>, deployed from `main` by [pages.yml](../.github/workflows/pages.yml). The hosted walkthrough passed: every route, refresh and history, the upload with Pyodide reuse, 375 px width, and axe in light and dark.
Team answers T1–T6 are recorded in [team-blockers.md](team-blockers.md). T7 has a proposal awaiting the team.
Final cleanup: unused exports, the `SHOW_APOLLO` flag and unused CSS are removed. A CI test now catches a stale scorer copy. Two finished planning docs are removed (still in git history).

## Next

1. Show the three T6 featured tiles per region in the app ([featured-tiles.md](featured-tiles.md)).
2. Complete a real screen-reader pass on the demo and upload routes.
3. Confirm T7: Gareth regenerates the export by hand ([steps](architecture.md#regenerating-the-export-t7)).
4. Resolve Darrel's differing Survival Unknown count.

## Blockers

- Darrel reported Survival counts of 68/11/4. The current scorer produces 70/11/2. Compare Unknown IDs and input/config versions. The 17 Artemis results agree.
- A real screen-reader pass and final feature acceptance remain open.

## Deferred after the submission

- Terrain (elevation) uploads through both CNNs (T1). The CNNs are shown through the catalogue results.
- Per-tile environment scoring (T4). It needs four LOLA maps and a pipeline rerun, and most inputs would stay region-wide.
