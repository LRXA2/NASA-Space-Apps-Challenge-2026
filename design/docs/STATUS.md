# Status

## Now

App planning covers one area: [app](specs/app/area.md). All seven specs are due 2026-11-15, the end of the hackathon, which is two days away.
`browse-first-patch` (`3458c47`) and `browse-regions` (`7ae9ae8`, `306e3fe`) are committed on `gareth/app`. The two `browse-regions` commits are not pushed. The other five specs have not started.
The app now shows all seven lunar regions and 2,910 patches. Each region page has a Leaflet patch map, a colour mode for rover or on-foot class, and a patch list. The results are in `specs/app/browse-regions.md`.
The work ran as a goal. Its log and its data check are in `goals/`. Styling is still neutral, and Gareth's wireframes are not applied.
Build order for the rest: `publish-demo`, `earth-analogs`, `compare-terrain`, `environment-assessment`, then `environment-upload` as a stretch goal.

## Next

1. Push `gareth/app`. It is two commits ahead of `origin/gareth/app`. The data commit adds about 15 MB.
2. Decide whether `browse-first-patch` and `browse-regions` get a `Status: done` line now. Both have every task ticked. The board counts neither as finished without it, so every later spec shows as waiting.
3. Start `publish-demo`. Its first task needs a host choice. The repository is private and Ian has write access, not admin, so GitHub Pages needs Aarron. Routes already use `#` and the build uses a relative base path.
4. Ask Aarron for the notebook 36 report folder (`reports/terrain-similarity-oriented-demo/20261104T003123532042Z/`) with the files he is sending.
5. Ask Darrel for results from his new scorer, and where the files moved. His branch merged into `main` and a folder was renamed (`fe01f71`).

## Blockers

- Aarron's files have not arrived: the three data folders and one Haworth–Wadi Rum run, promised in chat on 13 Nov. `origin/dev_aarron` has not changed since 5 Nov. They block wider analog coverage and numeric pair grids. They do not block the first analog and pair screens.
- Aarron's query patches and Hanxi's patches appear to sit on different grids. Until a footprint match is confirmed, analog pages cannot show Hanxi's predictions, and patch pages cannot link to analogs.
- The received `data/app_inputs/results.csv` is still Darrel's old format. Detailed per-check evidence remains unavailable.
- Most environment input values are test assumptions (Darrel's README). The app must label the scores that way.
- GitHub Pages cannot be switched on by Ian: the repository is private and needs an admin.
- Gareth's Windows setup and `temp/` input paths are untested. The export commands for it are in `app/README.md`.
- CNN uploads are not planned. Aarron expects new-site input, and described the CNN input as "just an image". Confirm with him what a user would supply.
- Not recorded as decisions yet: Leaflet without react-leaflet, pattern fills for class colours, and keeping the colour mode when the region changes. They are in the chat from 13 Nov.
- An `.impeccable/` folder and a root `PRODUCT.md` link appeared on 13 Nov from a design session. If that session edits `app/src/`, check it against the `browse-regions` changes.
- Stale: `specs/app/area.md`: it says the specs are "not completed implementation". Two specs are built.
- Stale: `specs/app/browse-first-patch.md`: its Verify section says the commands "do not exist yet". They exist. Its Results say nothing is committed. It is committed.
- Stale: `specs/app/publish-demo.md`: it lists route handling as open. The code uses hash routes (`app/src/router.ts`) and a relative base (`app/vite.config.ts`). `app/package-lock.json` is already committed, which its second task plans to add.
- Stale: `design/handoff/developer_handoff_2026-11-13.md` says `design/` is untracked. It is committed. `design/PRODUCT.md` still lists nine environment domains and one shared hard gate.
