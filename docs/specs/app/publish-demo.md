# Publish the app demonstration

Status: blocked: hosting deferred by Ian
Needs: browse-first-patch
Due: 2026-11-15

## Goal

Provide a stable hosted link to the real demonstration for judges and teammates as soon as the first feature works.
Redeploy as later specs merge, so a working site exists even if blocked features never land.
Make direct links, static assets, and documented regeneration work from a fresh checkout. See [shared context](area.md#shared-context).

## Done when

- A selected static host serves a reproducible production build using the committed app exports, without Python or model weights on the host.
- The chosen package manager has a committed lockfile. A clean install, build, and local production preview succeed.
- Every route that exists at deploy time (region and patch first, analog and pair once built) can be opened directly and refreshed. Browser back/forward works at the hosted base path.
- Region JSON, binary grids, and analog assets load from the correct base path. Missing data and failed map tiles retain usable text states.
- The published catalogue and examples match the approved export manifest. Missing scientific coverage is disclosed, not replaced by wireframe values.
- The selected demo route can be completed on a laptop and a narrow screen using labels and keyboard navigation. It shows one real weak match if such an example exists.
- Regeneration and handoff instructions name the input locations, run identifiers, export commands, schema versions, and how to review changed assets.
- The deployment URL and actual checks are recorded only after the hosted walkthrough succeeds. Export ownership is agreed or explicitly marked unassigned.

## Out of scope

- Upload processing, a backend, user accounts, live inference, a global data service, and guaranteed offline access to third-party Earth tiles.
- Building presentation slides, a video, or submission materials. Those can use the finished demo but are separate deliverables.

## Constraints

- Preserve the implemented hash routes and Vite relative base `./`. Verify them against the selected host and its deployed asset paths.
- Keep raw inputs, models, local environments, credentials, and machine settings outside committed app assets.
- Export and deployment are separate operations. Builds must not silently download data or rerun research pipelines.
- Preserve source attribution, scientific caveats, accessible status labels, and the distinction between model predictions and operational evidence.
- Each task changes at most three files and adds at most three functions or five test cases. Do not combine hosting config, navigation rewrites, and asset regeneration in one task.

## Verify

- Seam: clean checkout to production build, then the public site in a browser.
- The package lockfile is committed. Use these existing commands for the clean-install and hosted checks:

```powershell
npm --prefix app ci
npm --prefix app run build
npm --prefix app run preview
```

- Regeneration uses `--pipeline-run` on a machine holding the bundle. A consuming checkout must serve committed exports without `temp/` or `.venv`.
- On the live site, reopen one URL for each route that exists. Refresh each. Check data requests, a missing asset, and back/forward navigation.
- Do not mark deployment done from a build log alone. Record the hosted URL and visible behaviour after review.

## Decisions

- **Deferred, 2026-11-14:** Ian asked to leave hosting out. No host is selected. Resume host selection and hosted checks only when that scope returns.
- **Implemented:** Hash URLs in `app/src/router.ts` and relative asset paths in `app/vite.config.ts` avoid a host rewrite requirement. Hosted verification remains open.
- **Open:** The team has not assigned responsibility for regenerating and reviewing app exports when a model changes.

## My calls

- Treat a successful local build as readiness for deployment, not permission to publish externally. Follow the user's deployment instruction when that step starts.
- Keep demo instructions in the app README and record the delivered URL and checks in this spec's eventual Results section.

## Tasks

- [ ] Record the selected host, route handling, and export-maintenance responsibility with the user. Preserve unresolved ownership explicitly rather than assigning a teammate.
- [x] Add the package lockfile and clean-install documentation. Verify a fresh production build consumes committed exports without local research inputs. Historical note, 14 Nov: `npm --prefix app run build` passed on the existing install. A clean install was not rerun.
- [ ] Configure the selected host's build and static-asset base paths. Verify local production preview resolves region data and binary grids.
- [ ] Make hosted direct links and refresh behaviour match the selected route strategy. Verify region, patch, unknown-route, and missing-asset cases, plus analog and pair routes if they exist.
- [ ] Publish through the authorized hosting workflow and record the real hosted walkthrough, input-regeneration instructions, and known coverage limits (blocked: Ian deferred hosting).
- [x] Verify `npm --prefix app ci` and the production build from a clean dependency installation. Checked 2026-11-15 after pulling `dd3503f`; 37 packages installed, production build passed.

## Results

Verified on 2026-11-15 against `8769b86` plus the local interaction fixes.
`npm --prefix app ci` succeeded earlier on `dd3503f` with the combined lockfile, including theme fonts and browser-check tools.
The upstream `8769b86` update did not change dependencies. Build and browser checks were rerun after reconciliation.
`npm --prefix app run build` passes its TypeScript check and production build.
`npm --prefix app run check:browser` passes all five check groups using production files at an intercepted `/demo/` path.
It checks ten page URLs at 1440 px and 375 px, direct links, history, refresh, demo links, failure states, and uploads.
It opens no listening port. This is local browser evidence, not a hosted walkthrough.
No public host or URL is recorded. Export maintenance remains unassigned.
See [demo walkthrough](../../demo-walkthrough.md) and [app README](../../../app/README.md) for reproducible commands.
