# App design handoff

> Historical snapshot from 2026-11-13. It is not the current implementation status.
> See [architecture](../../docs/architecture.md) and [app specs](../../docs/specs/app/area.md).

Status as of 2026-11-13. Handoff files in this folder are named `design_handoff_<YYYY-MM-DD>.md`; add a new dated file for each handoff instead of editing an old one. This covers the app (frontend) work only. The models and pipelines are owned by Aarron, Darrel and Hanxi.

## Where things are

| What | Where |
|---|---|
| Clickable low-fi wireframes (revision 3, current) | https://claude.ai/artifact/4iQVvpyT417jgJVm4npdY2. Source: [wireframes.html](../wireframes.html) |
| Product facts and constraints | [PRODUCT.md](../PRODUCT.md) |
| Raw teammate outputs (gitignored) | `temp/` |

The wireframes are greyscale and show layout only. **All numbers in them are sample values**, not real data. Each component carries a chip naming its data source (A, B or C) and how it behaves (click or hover). The notes under each screen give its demo script line, its route and its build notes.

**Not done yet:** the design system (colours, type, spacing as CSS variables) and the mid-fi mockup. The layout needs the owner's approval before those start. You can build the structure now; the styling will drop in later as CSS variables.

## Decisions made

- **Stack:** static React (Vite + TypeScript), Leaflet for maps, all data as precomputed JSON. A Python export script (repo `.venv`, Python 3.12) turns teammate outputs into that JSON. Nothing runs models live. Streamlit was considered and rejected because we wanted more design control.
- **Scope:** Earth and Moon only. Mars is excluded.
- **Persona:** an analog mission planner choosing an Earth site where a crew can rehearse a south-pole traverse. The real audience is judges watching a demo of a few minutes.
- **Flow:** region, then patch. Environment data (B) is per region; terrain data (A, C) is per patch.
- **Theme:** dark base. The visual direction is still open, but it should be grounded in the subject (lunar terrain, elevation data, NASA science), not a generic SaaS dashboard.

## Screens and routes

Demo walkthrough, 4 clicks:

| # | Screen | Route | Click to the next screen |
|---|---|---|---|
| 1 | Region overview: polar SVG map plus a table of 17 regions with Ops and Survivability | `/` | Leibnitz Beta Plateau row |
| 2 | Region: scores plus the patch grid (Leaflet `CRS.Simple`) and featured patches | `/region/:regionId` | Featured patch row or grid square |
| 3 | Patch terrain: rover class, on-foot class, crossable directions, slope and elevation canvases | `/region/:regionId/patch/:patchId` | Earth analogs tab |
| 4 | Earth analogs: top 5 table, Leaflet Earth map, slope CDFs, all linked on hover | `…/patch/:patchId/analogs` | Rank 2 row (the misleading match) |
| 5 | Pair comparison: four canvases on a shared scale with a linked crosshair, the 5 physical checks, height and slope CDFs, Earth readiness placeholder | `…/analogs/:rank` | Not applicable |

Other screens:
- Region environment tab (9 domains): `/region/:regionId/environment`
- Region with environment data only (10 of the 17 regions)
- Region with a failed hard gate: both scores blank, fail reason shown, terrain still available

The demo deliberately uses rank 2: a high cosine score with only 2 of 5 physical checks in band. It shows the judges that a high score doesn't mean a good fit.

## Rules the UI must keep

1. **Colour is never the only signal.** Passed/Failed/Unknown, rover classes (operable/marginal/non-operable) and on-foot classes (easy/caution/unsuitable) always get an icon and a text label. On the patch grid, letters or fill patterns carry the class.
2. **Unknown is never a pass.** Missing data shows as Unknown.
3. **A failed hard gate leaves both Ops and Survivability blank** ("—", "Not scored") and shows the fail reason in readable words.
4. **Show physical evidence beside every similarity score.** Show weak matches; don't filter them out.
5. **Every screen has a visible "Where this breaks down" panel** with 2–4 points specific to that screen. The current text is in the `LIMITS` object in `wireframes.html`.
6. **Label thresholds as project test assumptions, not NASA certification.** Label CNN outputs as predictions, not safety certifications.

## Data: what exists and how it maps

### C: Terrain CNN (rover + on-foot), ready
`temp/terrain_human_walkability_lunar_inference/20261112T120422201915Z_101366/predictions.csv` has 2,910 patches across 7 regions. Useful columns:

- `patch_id` (e.g. `A3CLR22_10_Leibnitz_Beta_Plateau:960:32:64`) and `region`.
- `top_row`, `top_col`: grid position in 30 m cells. Use these directly as `CRS.Simple` coordinates for the patch grid. Each patch is 32 × 32 cells.
- `center_x`, `center_y`: south-polar stereographic metres. Use these for the overview map.
- `slope_median_deg`, `slope_p90_deg`, `relative_relief_m`.
- Rover: `predicted_rover_class`, plus `rover_probability_*`.
- On foot: `predicted_human_terrain_class`, plus `human_probability_*`.
- Directions: `predicted_north_south` and `probability_north_south`, and the same for `east_west`, `northwest_southeast` and `northeast_southwest`.
- Terrain grids for the canvases: `tensor_shard` + `tensor_index`, which point into the `.npz` files in `tensors/`.
- Patch counts vary a lot by region (Leibnitz ~225, Haworth ~840). The "412 patches" in the wireframes is a placeholder.

### B: Environment engine, ready but changing
`temp/darrel pipeline results.csv` has 83 rows. Columns: `ID`, then nine domain scores (`radiation`, `thermal`, `solar_illumination`, `dust`, `plasma_charging`, `uv`, `seismic`, `exosphere`, `communications_geometry`), then `hard_gate_status`, `Fail Reason`, `final_habitability_score`.

- **Changing:** `final_habitability_score` will become two columns, `Ops` and `Survivability`, both 0–100. See `temp/darrel pipeline potential changes.txt`.
- **Mismatch to resolve:** the IDs are `eda_001…eda_083`, not the 17 region names. Ask Darrel how rows map to regions.
- **Wireframe correction:** the real nine domains include *exosphere* and do not include *terrain & surface*. The domain names in the wireframes need updating.
- **Fail reasons are machine text**, e.g. `solar_illumination: window_continuous_sunlight_hours = 150.0 h; required >= 156 h`. The export script or the UI should turn them into readable sentences.

### A: Similarity CNN, pending
Aarron's outputs aren't exported yet. Expected per lunar patch: top-k Earth matches with region, rank, cosine score, centre lat/lon, the 5 physical checks (Moon value, Earth value, difference, in-band flag) and slope/height CDF points. Earth sites: Northern Arizona, Lanzarote, Atacama (San Pedro), Death Valley, Wadi Rum. The notebooks are in `notebooks/modeling/terrain_similarity/` (start with 35 and 36).

### Not built
The Earth simulation-readiness score (climate, land cover, OSM access). The UI shows it as a "Not yet computed" placeholder.

## Open questions

1. Does an **Unknown** hard gate also blank both scores, or only a Failed one? (Darrel)
2. Are the 6 **Apollo baseline** sites still in the environment data? The comparison chart is removed until we know. (Darrel)
3. How do the environment `eda_*` IDs map to the 17 regions? (Darrel)
4. Will the Earth match patches ship as **32×32 grids**, not just PNGs? Moon and Earth canvases can only share a colour scale and crosshair if the Earth side is a grid too. (Aarron)
5. Which 3–5 **featured patches** per region should the demo use? Include at least one misleading high-score match. (Team)
6. Should the south-pole overview map be an SVG schematic (current plan) or Leaflet?

## Suggested next work (none of it depends on the visual design)

- **Export script:** turn `predictions.csv` into one `patches/<region>.json` per region, and the `.npz` tensors into per-patch slope and elevation grids (32 × 32 arrays, rounded). Turn the environment CSV into `regions.json` once the region mapping is known.
- **App shell:** Vite + React + TypeScript, set up with the routes above. Keep selection state in the URL.
- **Patch grid component:** Leaflet `L.CRS.Simple`, one `L.rectangle` per patch from `top_row`/`top_col`. Click opens the patch route. Hover shows the patch's classes. The colour mode can be switched between rover class, on-foot class and best analog score.
- **Terrain canvas component:** draws a 32×32 grid with `image-rendering: pixelated`, accepts a colour scale as a prop, shows a hover readout, and can share its crosshair with sibling canvases.
- **Status badge component:** icon + text label for Passed/Failed/Unknown and for both class sets.

## Repo and tooling

- **To commit when ready:** `design/PRODUCT.md`, `design/handoff/design_handoff_2026-11-13.md` and, optionally, `design/wireframes.html`. Nothing has been committed yet.
- **Do not commit `.impeccable/`.** It only holds a local design-review hook setting (`config.json`) and a personal consent record (`config.local.json`). Consider adding `.impeccable/` to `.gitignore`.
- The Impeccable design hook is on for this machine only (in `.claude/settings.local.json`). It will be turned off when the design pass is finished. It doesn't affect anyone else's checkout.
