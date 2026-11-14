# Status

## Now

Updated 2026-11-15 on `gareth/app` after pulling `8769b86`, also on `origin/main`.
Gareth's exploration theme, Apollo references, and upload input guide are merged. Local changes fix upload-row navigation and Earth-marker keyboard linking, with browser checks and reconciled records.
The specs in [specs/app/](specs/app/area.md) are due today. Their verification records include this session's checks. Final acceptance remains open.
Hosting is deferred at Ian's request. See [demo walkthrough](demo-walkthrough.md) for the current examples.

## Next

1. Review the local app changes and feature acceptance. Ian handles commits and pushes.
2. Complete a real screen-reader pass on the demo and upload routes.
3. Confirm featured tiles (T6), export ownership (T7), and the full-catalogue regeneration command.
4. Resolve Darrel's differing Survival Unknown count in [team-blockers.md](team-blockers.md).
5. Settle terrain-upload scope and region-versus-tile environment scope before adding either feature.

## Blockers

- Hosting and hosted checks are deferred. No host or public URL is selected.
- Terrain CNN upload needs the team's scope decision. Browser terrain inference is not implemented.
- Per-tile environment scoring needs four LOLA maps and a pipeline rerun. App exports use region scope.
- Darrel reported Survival counts of 68/11/4. The current scorer produces 70/11/2. Compare Unknown IDs and input/config versions.
- A real screen-reader pass and final feature acceptance remain open.
- This checkout lacks the full research input bundle. The preparation scripts default to Haworth only, which changes catalogue coverage.
