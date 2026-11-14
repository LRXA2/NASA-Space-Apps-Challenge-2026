# Docs

Engineering docs for the Lunar Analog Finder app and the pipelines that feed it. UI design (product brief, wireframes, the chosen visual theme) lives in [`design/`](../design/).

| File | What it covers |
| --- | --- |
| [architecture.md](architecture.md) | How the pipelines, the integration step, the export and the static app fit together, and which decisions are still open |
| [ui-theme-implementation.md](ui-theme-implementation.md) | How to build the chosen exploration theme into `app/`: phases, files, data still to export, checks |
| [featured-tiles.md](featured-tiles.md) | Draft featured patches per region, waiting on team decision T6 |
| [team-blockers.md](team-blockers.md) | Open questions for each teammate, collected in one place |
| [specs/app/](specs/app/) | The app's feature specs from 13 Nov, with tasks. Parts are out of date; [STATUS.md](STATUS.md) lists which |
| [handoff/developer_handoff_2026-11-13.md](handoff/developer_handoff_2026-11-13.md) | The first developer handoff: stack, data and blockers as of 13 Nov. Several blockers are since resolved |
| [STATUS.md](STATUS.md) | Current progress and next steps. Internal: **remove before submission** |

Folder-level guides stay next to their code: [`data/README.md`](../data/README.md) (what goes where under `data/`) and [`app/README.md`](../app/README.md) (running the app and the export).
