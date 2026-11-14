# Status

## Now

All seven specs are due 2026-11-15, the end of the hackathon, which is one day away.
Every task that does not need a host or Gareth's pipeline run is ticked. Six tasks are left: five wait on a host, and one waits on the pipeline run.
On 14 Nov the pair page gained slope and elevation distribution charts (`app/src/components/DistributionChart.tsx`). That change is not committed.
`gareth/app` is level with `origin/gareth/app` at `acb07e5`. `origin/main` is at `3b5937e`.
The team's log is [docs/STATUS.md](../../docs/STATUS.md).

## Next

1. Review and commit the distribution charts: `app/src/components/DistributionChart.tsx`, `app/src/pages/PairPage.tsx`, `app/src/styles/app.css`.
2. Get the host decision from the team, then start `publish-demo`. The repository is private, so GitHub Pages needs an admin, such as Aarron.
3. Ask Gareth to add per-check evidence from a `--detailed` scorer run, or copy his `data/processed/moon_pipeline/` run to this machine. The detailed output holds each check's column, unit and value.
4. Decide whether `browse-first-patch` and `browse-regions` get a `Status: done` line. Both have every task ticked and are on `main`.
5. Review the tasks marked "Superseded, 14 Nov" in `specs/app/earth-analogs.md` and `specs/app/compare-terrain.md`. Agree, or restore them as open tasks.

## Blockers

- No host is chosen. Deploy, the hosted walkthroughs, and the hosted upload check all wait on it.
- Per-check environment evidence needs a re-export from a pipeline run. No `data/processed/moon_pipeline/` folder is on this machine. The scenario page says the values are not in this build.
- Not run: `npm --prefix app run check:scorer -- ../data/processed/moon_pipeline/<run>/environment.csv`. No `data/processed/moon_pipeline/` folder is on this machine, so there is no reference CSV.
- Not checked on the preview: the Earth map's tile-failure fallback, keyboard focus linking a row to its marker, a failing or blank-score environment row, and a clean `npm install`.
- The planning records are in git. `design/docs/` and `docs/` are both on `main`. Agree with the group whether they stay.
- Most environment input values are test assumptions. The app labels them that way.
- CNN uploads are not planned. Confirm with Aarron what a user would supply.
- Not recorded as decisions yet: Leaflet without react-leaflet, pattern fills for class colours, and keeping the colour mode when the region changes. They are in the chat from 13 Nov.
- Stale: [docs/STATUS.md](../../docs/STATUS.md) says the scorer hash fix, overview map and linked cursor are "not committed yet". They are in `acb07e5`.
- Stale: `specs/app/area.md` says the specs are "not completed implementation". Most tasks are built.
- Stale: `specs/app/earth-analogs.md` and `specs/app/compare-terrain.md`: their Goal, Data sources and Done-when sections describe notebook 36 and a figure mode. The code reads the integrated pipeline run and draws real grids for every match.
- Stale: `specs/app/environment-upload.md`: its Verify section says `check_scorer_parity.mjs` "does not exist yet". It exists in `app/scripts/`.
- Stale: `specs/app/browse-first-patch.md`: its Verify section says the commands "do not exist yet". They exist. Its Results say nothing is committed. It is committed.
- Stale: `specs/app/publish-demo.md` lists route handling as open. The code uses hash routes (`app/src/router.ts`) and a relative base (`app/vite.config.ts`).
- Stale: `handoff/developer_handoff_2026-11-13.md` says `design/` is untracked. It is committed. `PRODUCT.md` still lists nine environment domains and one shared hard gate.
