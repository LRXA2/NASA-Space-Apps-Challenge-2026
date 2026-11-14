# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static React site (Vite + TypeScript) reading precomputed JSON; nothing is computed live, and every view should be fast and clickable. Full visual freedom.

- Maps: Leaflet. Earth uses a normal lat/lon basemap. The Moon uses a flat per-region grid of clickable 960 m patches in `L.CRS.Simple` (no globe).
- Terrain slope and relative-elevation maps are drawn on canvas from 32×32 grids, which allows hover readouts and a shared colour scale between Moon and Earth.
- Design tokens are delivered as CSS custom properties usable directly in React.
- Each screen has its own route, so links and the back button work.

## Users

- **Primary persona: analog mission planner.** Chooses an Earth field site where a crew can rehearse rover route-planning for a lunar south-pole traverse. Needs to know whether a lunar site is operable and which Earth terrain stands in for it, with evidence.
- **Actual audience: hackathon judges** (NASA Space Apps Challenge 2026) watching a live walkthrough of a few minutes. They reward going beyond visual similarity, combining datasets, and stating Earth's limits honestly.

## Product Purpose

Lunar Analog Finder: pick a site near the lunar south pole (Artemis III candidate regions) and get (1) a site assessment (can a mission operate here: environment and terrain), and (2) an Earth analog search (which Earth terrain resembles it, and where the analogy breaks down). Scope is Earth and Moon only; Mars is excluded.

Success: the planner leaves with a ranked Earth analog backed by physical evidence, with its weaknesses stated.

## Positioning

The app combines three independent engines and shows physical differences next to similarity scores, so a high similarity score never hides a large slope or relief mismatch. It treats Earth's limits (gravity, vacuum, radiation, regolith) as content, not a disclaimer.

## Operating Context

- Live demo flow: region on the polar map → site overview (featured patch) → ranked Earth analogs → one Moon–Earth pair comparison.
- All data is precomputed (CSV/JSON/PNG); nothing runs live.
- Lunar coordinates use a south-polar stereographic projection; Earth results use lat/lon.

## Capabilities and Constraints

- **A. Terrain similarity CNN:** 960 m × 960 m lunar patch (32×32 at 30 m) → top-k Earth patches. Per result: Earth region, rank, cosine score, centre lat/lon, slope and relative-elevation PNGs (Moon and Earth), 5 physical checks (median slope, P90 slope, relief, plane residual, local elevation SD) with Moon–Earth difference and an in-band flag, slope/height CDFs.
  - Earth sites: Northern Arizona, Lanzarote, Atacama (San Pedro), Death Valley, Wadi Rum.
  - Lunar regions with patches (7): Leibnitz Beta Plateau, Malapert Massif, de Gerlache–Kocher Massif, Haworth, Faustini Rim A, de Gerlache Rim 2, Connecting Ridge Extension.
- **B. Environmental suitability engine:** per region (17 Artemis candidate regions; Apollo baselines unconfirmed). Nine domains, each check Passed / Failed / Unknown, per-domain score, and two final scores: **Ops** and **Survivability** (0–100). A failed hard gate leaves both blank and comes with a readable fail reason. Missing data is Unknown, never a pass. Whether an Unknown hard gate also blanks the scores is an open question. Thresholds are project test assumptions, not NASA certification.
- **C. Terrain CNN:** per lunar patch, rover class (operable / marginal / non-operable) and crew-on-foot walkability (easy / caution / unsuitable), each with probabilities, plus predicted rover-crossable directions (N–S, E–W, NW–SE, NE–SW). Trained on Earth terrain: predictions, not safety certifications.
- **Data granularity:** environment is per region (17); terrain is per patch (7 regions, ~2,900 patches). The flow is region → patch. 10 regions have environment data only.
- **Lunar terrain rendering:** the app draws slope and relative elevation from the 32×32 terrain grids (no PNG pipeline needed for the Moon side).
- **Not yet built:** Earth simulation-readiness score (climate, land cover, OSM access/logistics). Shown as a designed slot marked "not yet computed."
- General retrieval accuracy and operational suitability are unvalidated.

## Evidence on Hand

- Notebooks 28–36 under `notebooks/modeling/terrain_similarity/` (similarity CNN, model comparison, slope/relative-elevation demo).
- Environmental domain research: `darrel stuff/research/environmental_data.csv`.
- No user testimonials, validation benchmarks or NASA endorsements exist; do not imply any.

## Product Principles

1. Evidence beside every score: never show a similarity or suitability number without the physical or per-check evidence behind it.
2. Unknown is not a pass: missing data is shown as Unknown, and blocked scores show which gate blocked them instead of a number.
3. Keep the weak matches: show misleading and low-quality matches honestly rather than filtering them out.
4. Every screen states what it cannot tell you, specific to that screen.
5. Demo first: the core flow takes 3–4 clicks and is deterministic (curated featured patches).

## Accessibility & Inclusion

Colour is never the only signal for Passed/Failed/Unknown or operable/marginal/non-operable; always pair it with an icon and a label. The demo must also read on a projector.
