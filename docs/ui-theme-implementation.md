# Implementing the exploration theme

How to build the chosen visual design into `app/`. Written 2026-11-14 for whoever implements it, person or Claude session.

The look itself (tokens, components, screen layouts, what not to copy from Stitch) is specified in [design/exploration-theme/DESIGN.md](../design/exploration-theme/DESIGN.md). The reference renders are in [design/exploration-theme/screens/](../design/exploration-theme/screens/) and the mockup markup and CSS in [design/exploration-theme/mockups/](../design/exploration-theme/mockups/). Read DESIGN.md first; this file says where each part goes in the code.

## Ground rules

- **Data and copy come from the app, not the mockups.** The mockups were built on the 14 Nov pipeline run (`20261114T081013177916Z_da70aa`) and match it, but compute every number from the exported JSON. Where a mockup and the app's wording disagree, keep the app's wording unless DESIGN.md gives new copy.
- **Content rules** (from [PRODUCT.md](../design/PRODUCT.md) and the team's answers in [team-blockers.md](team-blockers.md)) must survive the restyle:
  - Operations and Survival are two separate 0–100 scores and are never combined.
  - A Fail or Unknown shows no score.
  - Unknown is never treated as a Pass.
  - Cosine is a shape similarity, shown like `0.969`, never as a percentage.
  - Gate thresholds are project test values, not NASA limits.
  - Nothing is presented as a safety rating.
  - Status always has an icon and a word, never colour alone.
- **Keep what works:** hash routes, the data loaders, the scorer worker, the shared pair cursor, keyboard access to the maps and grids, and the paged region table.
- **Accessibility stays at zero axe violations** on all routes, with a visible focus style on everything focusable.
- Work on a new branch from `gareth/app`, such as `gareth/exploration-theme`. Ask the owner before committing, pushing or merging.
- Don't edit `.impeccable/` or `design/wireframes.html`.

## Where things are now

| Part | File |
| --- | --- |
| Tokens (placeholder, light and dark) | `app/src/styles/tokens.css` |
| All styles, one file | `app/src/styles/app.css` |
| Shell: header and main | `app/src/App.tsx` |
| Routes and link builders | `app/src/router.ts` |
| Terrain colour ramps (placeholder blue) | `app/src/components/colorScales.ts` |
| Light/dark switch for the ramps | `app/src/components/useColorScheme.ts` |
| Pages | `app/src/pages/*.tsx` |
| Shared components | `app/src/components/*.tsx`: StatusBadge, CheckCount, Limitations, PageState, ProbabilityBars, CrossingAxes, TerrainCanvas, DistributionChart, PatchMap and EarthMap (both Leaflet), PolarOverview, AssessmentView |
| Data export | `app/scripts/export_data.py` writes `app/public/data/` |

The app uses plain CSS with custom properties. There is no Tailwind; don't add it. The Stitch prompt suggested Tailwind, but the theme is easier to land as tokens plus the existing stylesheet.

## Phase 1: tokens, fonts, dark only

1. Rewrite `tokens.css` with the DESIGN.md tokens. Keep the existing names that other CSS already uses and point them at the new values, then add the new ones:

   | Existing token | New value |
   | --- | --- |
   | `--surface-page` | `#080B27` |
   | `--surface-card` | `#12163A` (panels use the gradient from DESIGN.md) |
   | `--text-primary` / `--text-secondary` / `--text-muted` | `#E6E8FF` / `#B3B9DA` / `#8E95BD` |
   | `--border` | `rgba(129,140,248,.16)` |
   | `--hairline` | `#252B57` |
   | `--link` | `#7DD3FC` |
   | `--focus` | `#BAE6FD` |
   | `--bar` / `--bar-track` | `#38BDF8` / `#252B57` |
   | `--status-good` / `--status-warning` / `--status-critical` | `#62C2AD` / `#E2BC5C` / `#E48069` |
   | `--status-mark` / `--status-mark-warning` | `#04121F` / `#04121F` (glyphs inside filled icons) |
   | `--error-surface` | `rgba(228,128,105,.08)` |
   | `--font` / `--mono` | `"Inter", system-ui, sans-serif` / `"IBM Plex Mono", ui-monospace, monospace` |
   | `--radius` | `16px` |

   Add `--font-display: "Space Grotesk", "Inter", sans-serif`, `--accent`, `--accent-hover`, `--on-accent`, `--select`, `--select-line`, `--violet`, `--moon`, `--earth` and the panel gradient.
2. Remove the `prefers-color-scheme` block and set `color-scheme: dark` on `:root`. Make `useColorScheme()` return `"dark"` always, or remove it and its callers. Check `TerrainCanvas`'s `scaleNote` callers, which word their notes by scheme.
3. Fonts. Self-hosting is safer for a live demo on a weak network: `@fontsource-variable/space-grotesk`, `@fontsource-variable/inter` and `@fontsource/ibm-plex-mono` (400 and 500), imported in `main.tsx`. These are new dependencies, so confirm with the owner first. The fallback is a Google Fonts `<link>` in `app/index.html`.
4. Paint the page background on `body`: the three radial washes and three star tiles, copied from `mockups/01-Regions.html`.
5. Theme the browser surfaces: `::selection`, `scrollbar-color`, focus ring (2 px `--focus`, 3 px offset), and `font-variant-numeric: tabular-nums` on `.number` and mono data.

## Phase 2: shell

In `App.tsx`:

- Brand block: round logo (reuse the mockup's logo SVG: horizon line, gold Earth half-disc, three stars) and the "NASA Space Apps 2026" sub-line in gold mono.
- Section links as pills. The current section gets `aria-current="page"` and the cyan tint. The app labels the upload link "Try your own data"; the mockups say "Score your own data". Pick one with the owner.
- New `DemoPath` component: the four steps (Region, Patch, Earth analogs, Best match) in one pill, linking to the demo patch via `links.*` (Leibnitz Beta Plateau, `r192-c192`, rank 5 Atacama). Derive the current step from `useRoute()`; when the route is not on the demo path, show no step as current. Give it `aria-label="Demo path"` and `aria-current="step"` on the current step. Under 640 px show only the current step's label.
- Remove the `topbar-note` line, or move its "Precomputed results · Earth and Moon only" into the footer.
- New footer: product name on the left, `regions.json` `source.run_id` and `pipeline.run_id` in mono on the right.

## Phase 3: shared components and CSS

Restyle these in `app.css`, following the DESIGN.md component specs:

- **Panels:** `.card`, the details cards and the region and page sections get the gradient fill, hairline border and 16 px radius. Titles use `--font-display` 19/600, sentence case.
- **Buttons:** primary, secondary and disabled pills. The pager buttons (`.pager button`) are secondary pills.
- **Status:** in `StatusBadge` and `.badge`, `.badge-small`, `.tone-*`, make badges pills with icon and word; keep the existing icon shapes (check, triangle, octagon). Add a "no score" label wherever a Fail or Unknown replaces a score.
- **Segmented control:** the region page's map-mode radios (`.map-mode`) become a sunken pill track with a solid cyan selected option. Keep them as radios for accessibility.
- **Tables:** `.patch-table`, `.gate-table`, `.crossing-table`, `.probabilities`, `.distribution-table`. Header row with no fill and small uppercase Space Grotesk labels, `--hairline` rules, hover row, and a selected row with the 2 px inset cyan edge.
- **Limits:** `Limitations.tsx` becomes one panel with an amber icon title and short amber rules over each item.
- **Class fills:** `.patch-square` and the hatch classes in `PatchMap`, plus legends and any terrain mix bars, use the three class fills in DESIGN.md (solid, 135° stripes, 45° stripes).
- **Terrain ramps:** in `colorScales.ts`, replace the blue sequential ramp with magma for slope and the navy-to-white ramp for elevation (stops in DESIGN.md), and update each `scaleNote` to match ("Brighter is steeper", "Lighter is higher"). **Decision for the owner:** the app fits the slope domain to each patch (`slopeMax`) and shares it across a pair; the mockups show a fixed 0–20° legend. The default is to keep the fitted, shared domain and change only the colours.
- **Distribution charts:** Moon line `--moon` (solid), Earth line `--earth` (dashed), gridlines `--hairline`.
- **Leaflet:** dark zoom controls and attribution (`.leaflet-bar`, `.leaflet-control-attribution`). `EarthMap` uses light OpenStreetMap tiles, which glare on the dark page. Options: a CSS filter on `.leaflet-tile-pane` (no new provider), or a dark tile provider (needs its terms and attribution checked). Ask the owner.
- **Polar map:** `PolarOverview` gets nodes over dashed true-extent squares (see DESIGN.md). Keep its projection code. Each node is a link with a focus ring. Add a `selected` prop so the home page can mark region 1, and an Operations-Fail style using the environment data.

## Phase 4: home page

Rebuild `RegionsPage.tsx` to the home layout in DESIGN.md: hero with stat rows, sky panel and polar map, region cards, the "Looks alike, measures different" pair, then limits.

Data it needs:

| Element | Source |
| --- | --- |
| Region count with terrain, patch total, patch size | `regions.json` (`regions[].exported_patch_count`) and the patch files' `patch_size_m`, `spacing_m` |
| 17 regions in total, scores and status per region | `environment.json` |
| Earth site count, matches per patch | `regions.json` `pipeline.earth_sites`, `pipeline.top_k_per_site` |
| Rover class counts per region (the mix bar) | **Not exported yet.** The patch files hold it, but they total 3.2 MB, too much for the home page. Add per-region `rover_class_counts` (`operable`, `marginal`, `non_operable`) to each `regions.json` entry in `export_data.py`, with a test in `app/scripts/tests/test_export_data.py`, then re-export |
| Sky panel stars | Copy [design/exploration-theme/sky/sky.json](../design/exploration-theme/sky/sky.json) to `app/public/data/sky.json`, or trim it to magnitude ≤ 5 and the two named stars first (it is 68 KB). Star catalogue: `stars.6.json` from the d3-celestial project (BSD licence), projected for 2026-11-14 12:00 TT by [sky.py](../design/exploration-theme/sky/sky.py). Credit it in the footer or the about text |
| Pair panel values and tiles | `analogs/leibnitz-beta-plateau.json` for patch `r192-c192`: rank 1 and the candidate with the most checks in band (rank 5), their cosines and checks in band. Draw the three slope tiles with `TerrainCanvas` (or a small static variant) on one shared domain |

The sky panel is a new `SkyPanel` component that renders an SVG from `sky.json`: x = 320 + azimuth × 3.3, y = 282 − altitude × 3.3, on a 640 × 330 viewBox. Star radius = max(0.5, 1.9 − 0.3 × magnitude); colour from the B−V index (below 0.2 blue-white `#CFDDFF`, above 1.1 warm `#FFE3BE`, else `#F4F2EA`). The full drawing is `sky_panel()` in the mockup generator; its SVG output is in `mockups/01-Regions.html`. Give the SVG a text alternative.

## Phase 5: per-screen additions

These are new features shown in the mockups. Each is independent; do them in this order and stop when time runs out.

1. **Patch page:** the "Closest Earth terrain by shape" banner (cosine, rank, checks in band, the 0-of-5 warning, button to all matches).
2. **Analogs page:** the "most similar shape" and "best physical fit" callouts and the sort toggle.
3. **Pair page:** rank tabs (current candidate, rank 1, all 15), the two-colour heading, and the physical checks drawn as bands.
4. **Environment page:** regions with terrain and environment-only regions as two groups under one summary.
5. **Region page:** "Five patches to start with". **Blocked:** the featured tiles are a draft ([featured-tiles.md](featured-tiles.md)) waiting on team decision T6. Build it only if T6 is settled, or show the draft list behind a clearly marked flag.
6. **Terrain upload (screen 9): don't build.** It waits on team decision T1.

## Check before handing back

- `npm --prefix app run build` (type-check and build) passes.
- `.\.venv\Scripts\python.exe -m unittest discover -s app/scripts/tests -p "test_*.py"` passes, including the new export test.
- axe-core shows no violations on all 8 routes.
- Every route at 375 px and 1440 px: no horizontal scroll, no overlapping text. Compare against `design/exploration-theme/screens/`.
- Keyboard: Tab reaches the header, demo path, map nodes, grid cells, pager and toggles, with a visible focus ring.
- Contrast: body text at least 4.5:1, large text at least 3:1, on the panel gradient as well as on the page.
- The content rules above, checked on the environment list, a Fail scenario (`eda_007`), the analogs page and the upload results.
- Update [STATUS.md](STATUS.md) with what was done and what is left.
