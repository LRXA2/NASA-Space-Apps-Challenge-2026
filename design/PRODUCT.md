# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static React site (Vite + TypeScript) reading schema v2 JSON and terrain binaries. Environment uploads run locally in Pyodide. No application backend is used.

- Maps: Leaflet. Earth uses a normal lat/lon basemap. The Moon uses a flat per-region grid of clickable 960 m patches in `L.CRS.Simple` (no globe).
- Terrain slope and relative-elevation maps are drawn on canvas from 32×32 grids, which allows hover readouts and a shared colour scale between Moon and Earth.
- Design tokens are delivered as CSS custom properties usable directly in React.
- Each screen has its own hash route, so shared links and the back button work on static hosting.
- Pair distribution charts use plain SVG and the published terrain grids. No chart library is needed.

## Visual Direction

The team selected the exploration theme from Gareth's two proposals on 2026-11-14.
Aarron preferred it because the project supports reconnaissance. Gareth confirmed he would implement that theme.
The lighter-blue exploration proposal replaces the darker mission-control proposal as the design target.
Gareth's exploration theme, Apollo references, and upload input guide are merged through `8769b86`. Final visual acceptance remains for review.

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
- Catalogue results are precomputed. Environment CSV uploads are scored in a browser worker and labelled user-supplied.
- Lunar coordinates use a south-polar stereographic projection; Earth results use lat/lon.

## Capabilities and Constraints

- **A. Terrain similarity CNN:** each 960 m lunar tile has 15 Earth matches, top three per Earth site. Results include ranks, cosine, coordinates, five physical checks, numeric terrain grids, and distribution charts. Similarity relief is p95 minus p5. Terrain-page relief is maximum minus minimum.
  - Earth sites: Northern Arizona, Lanzarote, Atacama (San Pedro), Death Valley, Wadi Rum.
  - Lunar regions with patches (7): Leibnitz Beta Plateau, Malapert Massif, de Gerlache–Kocher Massif, Haworth, Faustini Rim A, de Gerlache Rim 2, Connecting Ridge Extension.
- **B. Environment scorer:** 17 Artemis scenarios, with six Apollo references displayed separately with best-effort input labels following Darrel's T3 answer. Operations and Survival have separate domains, statuses, reasons, and 0–100 scores. A Failed or Unknown assessment leaves only its own final score blank. Detailed gate evidence shows values, rules, and reasons. Thresholds and most inputs are project assumptions.
  - Operations: thermal, solar illumination, dust, plasma charging, Earth visibility, and soil.
  - Survival: radiation, thermal, plasma charging, and UV. Domain lists are read from the scorer output.
  - Gates are enabled in the committed config. Current Artemis results are Operations 14 Pass / 3 Fail and Survival 17 Pass.
- **C. Terrain CNN:** per lunar patch, rover class (operable / marginal / non-operable) and crew-on-foot walkability (easy / caution / unsuitable), each with probabilities, plus predicted rover-crossable directions (N–S, E–W, NW–SE, NE–SW). Trained on Earth terrain: predictions, not safety certifications.
- **Data granularity:** the current export uses region-scope environment scenarios and 2,910 terrain patches across seven regions. Ten scenarios have environment data only. Per-tile environment scoring requires the LOLA maps and a rerun.
- **Terrain rendering:** Moon and Earth panels use numeric 32×32 grids. Each measurement shares a scale across the pair. No PNG fallback is implemented.
- **Not yet built:** Earth simulation-readiness score (climate, land cover, OSM access/logistics). Shown as a designed slot marked "not yet computed."
- General retrieval accuracy and operational suitability are unvalidated.

## Evidence on Hand

- Notebooks 28–36 under `notebooks/modeling/terrain_similarity/` (similarity CNN, model comparison, slope/relative-elevation demo).
- Environmental research: `env_algo_task/research/environmental_data.csv`. Current scorer: `env_algo_task/env_pipeline/`.
- Current engineering records: [status](../docs/STATUS.md), [architecture](../docs/architecture.md), and [app specs](../docs/specs/app/area.md).
- No user testimonials, validation benchmarks or NASA endorsements exist; do not imply any.

## Product Principles

1. Evidence beside every score: never show a similarity or suitability number without the physical or per-check evidence behind it.
2. Unknown is not a pass: missing data is shown as Unknown, and blocked scores show which gate blocked them instead of a number.
3. Keep the weak matches: show misleading and low-quality matches honestly rather than filtering them out.
4. Every screen states what it cannot tell you, specific to that screen.
5. Demo first: the core flow takes 3–4 clicks and is deterministic (curated featured patches).

## Accessibility & Inclusion

Colour is never the only signal for Passed/Failed/Unknown or operable/marginal/non-operable; always pair it with an icon and a label. The demo must also read on a projector.
