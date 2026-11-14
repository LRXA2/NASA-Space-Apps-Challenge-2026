# Docs

Engineering docs for the Lunar Analog Finder app and its pipelines. UI designs live in [`design/`](../design/).

| File | What it covers |
| --- | --- |
| [architecture.md](architecture.md) | How the pipelines, the integration step, the export and the static app fit together, and which decisions are still open |
| [ui-theme-implementation.md](ui-theme-implementation.md) | Theme implementation sequence, delivered phases, remaining gaps, and checks |
| [demo-walkthrough.md](demo-walkthrough.md) | Verified local walkthrough, example values, and known limits |
| [featured-tiles.md](featured-tiles.md) | Draft featured patches per region, waiting on team decision T6 |
| [team-blockers.md](team-blockers.md) | Open questions for each teammate, collected in one place |
| [specs/app/](specs/app/) | Current feature specs, tasks, verification commands, and historical decisions |
| [handoff/developer_handoff_2026-11-13.md](handoff/developer_handoff_2026-11-13.md) | The first developer handoff: stack, data and blockers as of 13 Nov. Several blockers are since resolved |
| [STATUS.md](STATUS.md) | Current progress and next steps. Internal: **remove before submission** |

Folder-level guides stay next to their code: [`data/README.md`](../data/README.md) (what goes where under `data/`) and [`app/README.md`](../app/README.md) (running the app and the export).

## Planning records

Use [STATUS.md](STATUS.md) for current status and [specs/app/area.md](specs/app/area.md) for shared app context.
Run the progress skill with `bash <progress-skill>/scripts/progress.sh --all docs`.
Dated handoffs retain historical content and link to current records.
