# Status

## Now

Updated 2026-11-15 on `gareth/app` after pulling `8769b86`, also on `origin/main`.
Gareth's exploration theme, Apollo references, and upload input guide are merged. Local changes fix upload-row navigation and Earth-marker keyboard linking, with browser checks and reconciled records.
The specs in [specs/app/](specs/app/area.md) are due today. Their verification records include this session's checks. Final acceptance remains open.
Team answers T1, T2 and T4–T6 are recorded in [team-blockers.md](team-blockers.md): environment-only upload, region-scope environment, static architecture kept, and three featured tiles per region.
The repo is now public. Hosting is GitHub Pages via [pages.yml](../.github/workflows/pages.yml), not yet committed or enabled. See [demo walkthrough](demo-walkthrough.md) for the current examples.

## Next

1. Review the local changes, then commit `pages.yml` and merge to `main`. A repo admin sets Settings → Pages → Source to "GitHub Actions".
2. Verify the live Pages site: every route, the upload's first Pyodide load, phone width and axe.
3. Show the three T6 featured tiles per region in the app ([featured-tiles.md](featured-tiles.md)).
4. Complete a real screen-reader pass on the demo and upload routes.
5. Confirm export ownership (T7) and the full-catalogue regeneration command.
6. Resolve Darrel's differing Survival Unknown count in [team-blockers.md](team-blockers.md).

## Blockers

- The Pages deploy needs a commit to `main` and a one-time admin setting. Hosted checks wait on the first deploy.
- Darrel reported Survival counts of 68/11/4. The current scorer produces 70/11/2. Compare Unknown IDs and input/config versions.
- A real screen-reader pass and final feature acceptance remain open.
- This checkout lacks the full research input bundle. The preparation scripts default to Haworth only, which changes catalogue coverage.

## Deferred after the submission

- Terrain (elevation) uploads through both CNNs (T1). The CNNs are shown through the catalogue results.
- Per-tile environment scoring (T4). It needs four LOLA maps and a pipeline rerun, and most inputs would stay region-wide.
