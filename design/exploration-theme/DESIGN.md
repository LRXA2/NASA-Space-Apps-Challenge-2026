# Exploration theme

The chosen visual direction for Lunar Analog Finder, agreed on 2026-11-14. It comes from a Google Stitch exploration ("Artemis Frontier" / "Cosmic Wonder"), rebuilt on the app's real data and content rules.

This file says what the theme looks like. How to build it into `app/` is in [docs/ui-theme-implementation.md](../../docs/ui-theme-implementation.md).

| Reference | Where |
| --- | --- |
| Rendered screens, 1440 px and 375 px | [screens/](screens/) |
| Mockup source: markup and full CSS for each screen | [mockups/](mockups/). These are design-canvas files: they need the canvas runtime and its image store, so open them to read, not to view |
| Live canvas (row 3, "Proposed (exploration theme)") | https://claude.ai/artifact/QvnZuW5fFJMKcaGpRFfnRz. Private: ask the owner for access |
| Star positions for the sky panel | [sky/sky.json](sky/sky.json), made by [sky/sky.py](sky/sky.py) |
| Product facts and audience | [../PRODUCT.md](../PRODUCT.md) |

## Character

A calm night sky over the lunar south pole: deep indigo, a faint violet and cyan glow, and sparse stars. Panels are rounded and quiet; colour is kept for meaning. Two kinds of colour carry information everywhere:

- **Which world:** Earth is gold, the Moon is silver-lavender. Apply this to names, map labels, chart lines and legends.
- **Status:** Pass, Unknown and Fail each have one colour, and always come with an icon and a word.

**Dark only.** There is no light theme. Set `color-scheme: dark` and drop the `prefers-color-scheme` light values.

## Tokens

Use these as CSS custom properties on `:root`. The names here are suggestions; map them onto the app's existing token names where they match (see the implementation doc).

### Colour

| Token | Value | Use |
| --- | --- | --- |
| `--ground` | `#080B27` | Page background |
| `--surface` | `#12163A` | Solid panel fill, inputs |
| `--surface-sunk` | `#0C0F2E` | Segmented controls, step bar, wells |
| `--surface-hover` | `#1A1F4A` | Row and link hover |
| `--panel-fill` | `linear-gradient(160deg, rgba(27,32,74,.9), rgba(14,17,48,.92) 62%)` | Panels and cards |
| `--hairline` | `rgba(129,140,248,.16)` | The one border on panels, cards, dividers |
| `--line` | `#252B57` | Table rules, bar tracks |
| `--line-strong` | `#363E78` | Disabled outlines, step connectors, scrollbar |
| `--text` | `#E6E8FF` | Headings and body |
| `--text-2` | `#B3B9DA` | Secondary text, ledes |
| `--text-3` | `#8E95BD` | Captions, table headers, units (6.2:1 on `--surface`) |
| `--accent` | `#38BDF8` | Primary buttons, current step, selection, focusable map nodes |
| `--accent-hover` | `#7DD3FC` | Primary button hover; also links |
| `--on-accent` | `#04121F` | Text on `--accent` |
| `--focus` | `#BAE6FD` | Focus ring, 2 px, 3 px offset |
| `--select` | `rgba(56,189,248,.12)` | Selected row or chip fill |
| `--select-line` | `rgba(56,189,248,.42)` | Selected outline |
| `--violet` | `#818CF8` | Secondary button hover border only |
| `--moon` | `#C3C9EE` | Moon names, Moon chart line, Moon markers |
| `--earth` | `#F4AE5B` | Earth names, Earth chart line, Earth markers, brand sub-line |
| `--pass` | `#62C2AD` | Pass, operable, easy, in band |
| `--unknown` | `#E2BC5C` | Unknown, marginal, caution |
| `--fail` | `#E48069` | Fail, non-operable, unsuitable, out of band |

Page background, painted on `body`, in this order:

```css
background-color: #080B27;
background-image:
  radial-gradient(900px 620px at 10% -6%, rgba(76,29,149,.30), transparent 70%),
  radial-gradient(1000px 640px at 94% 2%, rgba(56,189,248,.10), transparent 70%),
  radial-gradient(1300px 820px at 50% 112%, rgba(46,16,101,.32), transparent 70%),
  /* three tiled star layers: tiny circles, radius 0.5–0.9 px, colour #CFDBEA at 16–41 % opacity,
     tiles of 420, 673 and 1031 px so the pattern never visibly repeats.
     Copy the three data-URI SVGs from mockups/01-Regions.html (search "data:image/svg+xml"). */;
background-attachment: fixed; /* optional */
```

Rover and on-foot class fills (map squares, terrain mix bars). Each class also differs by pattern, not only colour:

| Class | Fill |
| --- | --- |
| Operable / easy | solid `#3FB8A0` |
| Marginal / caution | `repeating-linear-gradient(135deg, #E2BC5C 0 3px, #7A5F1C 3px 6px)` |
| Non-operable / unsuitable | `repeating-linear-gradient(45deg, #E48069 0 4px, #9E4636 4px 6px)` |

Terrain colour scales, the same for Moon and Earth so the two can be compared:

| Map | Scale | Domain |
| --- | --- | --- |
| Slope | matplotlib **magma**. Stops at 0, 0.2, 0.4, 0.6, 0.8, 1: `#000004 #3B0F70 #8C2981 #DE4968 #FE9F6D #FCFDBF` | 0° to 20°, clamped |
| Relative elevation | `#070A14` at −100 m, `#23305A` at −40, `#56648F` at 0, `#A7B3D3` at +40, `#F2F4FA` at +100 | −100 m to +100 m, clamped |

### Type

| Role | Face | Size / weight | Notes |
| --- | --- | --- | --- |
| Display (home h1) | Space Grotesk | 60 px / 700, line-height 1.02, tracking −0.025em | 36 px under 640 px |
| Page h1 | Space Grotesk | 50 px / 700, line-height 1.06, tracking −0.025em | 34 px under 640 px |
| Section heading | Space Grotesk | 30 px / 600, tracking −0.015em | 24 px under 640 px |
| Panel title (h2) | Space Grotesk | 19 px / 600 | Sentence case, never uppercase |
| Body | Inter | 16 px / 400, line-height 1.5 | Lede 18 px in `--text-2` |
| Caption, note | Inter | 13–14 px | `--text-3` |
| Small label (table header, chip, step) | Space Grotesk | 11 px / 600, uppercase, tracking 0.1em | |
| Data | IBM Plex Mono | inherits size, tabular numbers | **Only** for patch IDs, run IDs, coordinates, scores and measurements |

Load Space Grotesk 500/600/700, Inter 400/500/600 and IBM Plex Mono 400/500.

### Shape and space

- Panels and cards: 16 px radius. Inner wells and images: 12 px. Buttons, chips, badges, segmented controls, nav links and the step bar: fully rounded (pill).
- One elevation: the hairline border plus the gradient fill. No drop shadow on panels. The only shadows are the cyan glow under the primary button (`0 6px 20px -8px rgba(56,189,248,.6)`) and under the selected region card.
- Page width 1320 px max, 32 px side padding (16 px under 640 px). Vertical gap between page sections 28 px.
- Panel header padding `20px 24px 10px`; body `16px 24px 24px`.

## Components

**Header.** Translucent bar (`rgba(8,11,39,.78)` with `backdrop-filter: blur(14px)`), hairline bottom border. Left to right:
1. Brand: round logo (40 px circle, cyan outline, soft cyan glow), "LUNAR ANALOG FINDER" in Space Grotesk 17/700 uppercase, tracking 0.06em, with "NASA SPACE APPS 2026" under it in gold mono 10 px.
2. Section links "Regions", "Environment", "Score your own data" as pills; the current one has a cyan tint and outline.
3. Demo path, pushed right: one pill containing four steps, Region, Patch, Earth analogs, Best match. Each has a 22 px numbered circle; done steps show a check, the current step is a solid cyan circle. Steps link to the demo patch (Leibnitz Beta Plateau, `r192-c192`, rank 5 Atacama). Under 640 px only the current step's label shows.

No avatar, no sign-in, no "telemetry" or "signal" status.

**Footer.** Hairline top border. Left: "LUNAR ANALOG FINDER · NASA SPACE APPS CHALLENGE 2026" (Space Grotesk 13/600 uppercase). Right: the inference and pipeline run IDs in mono 12 px, read from `regions.json`.

**Panel.** Gradient fill, hairline border, 16 px radius, title in sentence case with an optional one-line subtitle in `--text-3` and an optional chip on the right.

**Buttons.**
- Primary: solid cyan pill, dark text, Space Grotesk 15/600, min height 46 px, trailing arrow icon. Hover lightens to `#7DD3FC`.
- Secondary: transparent pill with a cyan outline at 38 %. Hover: violet outline and violet tint.
- Disabled: dashed `--line-strong` outline, `--text-3` text.

**Chip.** Pill, `rgba(11,15,42,.7)` fill, cyan outline at 32 %, cyan-light text, Space Grotesk 11/600 uppercase. Use for small facts beside a title (a date, "Demo path", "Similarity rank 1 of 15"). **Never put a chip above a heading as an eyebrow.**

**Status badge.** Pill, 12 px Space Grotesk 600, icon plus word: check circle for Pass, triangle for Unknown, octagon with a cross for Fail. Tinted fill and outline in the status colour. A Fail or Unknown never shows a score next to it: show "no score" in `--text-3` instead.

**Segmented control** (map colour mode, sort order, upload state). Sunken pill track; the selected option is a solid cyan pill.

**Tables.** No fill on the header row; headers are small uppercase labels. 1 px `--line` rules between rows. Hover tints the row `--surface-hover`. The selected or current row gets `--select` and a 2 px inset cyan line on its left edge.

**Map and list stay in sync.** Whatever is selected on a map (polar nodes, patch squares, Earth markers) is selected in the matching list or card, with the same cyan treatment, and vice versa.

**Polar map.** Dark well with a faint cyan radial glow. Dashed rings each degree from 89°S to 85°S, dashed spokes, "0° · toward Earth" in gold at the top with a small gold tick, and "POLE" in cyan at the centre. Each region is a 28 px circle node with its number, drawn over a dashed square showing the true extent of its tiles. Selected: cyan outline and a soft cyan glow. Operations Fail: coral outline and number. Legend below: node, area covered, Operations Fail, selected.

**Limits of this page.** One panel. Title "Limits of this page" with an amber warning icon. Items in a responsive grid (min 240 px columns), each marked by a short 28 × 2 px amber rule above it. No cards inside the panel and no numbering.

**Focus.** 2 px `--focus` outline, 3 px offset, on every link, button, map node and grid cell. Text selection uses a cyan tint. Scrollbars use `--line-strong` on transparent.

## Screens

Each screen keeps its current route, content, data and behaviour. The table lists what changes. The mockups show only what is described here; where the mockup and the app disagree on data or copy, the app wins.

| Screen | Mockup | What changes |
| --- | --- | --- |
| 1 Regions (home) | `01-Regions` | New layout, described below |
| 2 Region | `02-Region` | Theme. Panels: patch map with Rover / Crew-on-foot toggle; "Five patches to start with" list of featured patches, each with its closest Earth match and checks in band; "Region environment" with both scores and a link to the gate checks; the paged patch table. Featured patch 2 (`r192-c192`) is selected on the map and in the list |
| 3 Patch | `03-Patch` | Theme. Three verdict cards (Rover, Crew on foot, Rover crossing). A full-width "Closest Earth terrain by shape" banner showing the cosine, the rank and the checks in band, with the warning when 0 of 5 are in band and a primary button to all 15 matches. Terrain panel: slope with crossing axes, height, and measured stats |
| 4 Earth analogs | `04-Analogs` | Theme. Callouts for "most similar shape" (rank 1) and "best physical fit" (most checks in band), plus a short note that cosine measures shape, not fit. Sort by shape similarity or physical fit |
| 5 Pair | `05-Pair`, `05b-Pair-WadiRum` | Theme. Rank tabs at the top (the current candidate, rank 1, all 15). Heading "Leibnitz Beta Plateau and Atacama (San Pedro), Chile" with the Moon name in silver and the Earth name in gold. Four grids on shared scales with one cursor. Physical checks drawn as bands: the allowed band around the Moon value, a silver Moon dot, a gold Earth diamond, the difference against the tolerance |
| 6 Environment | `06-Environment` | Theme. Summary of Pass and Fail counts per assessment, then regions with terrain and regions with environment data only, as two groups |
| 7 Scenario | `07-Scenario`, `07b-Scenario-Fail` | Theme. Operations and Survival side by side, each with domain bars and its gate checks table |
| 8 Upload | `08-Upload` | Theme. Three steps: get the template, add your CSV, results. Results rows expand to show both assessments with gate checks |
| 9 Terrain upload | `09-TerrainUpload` | **Do not build.** Design ahead of the team's scope decision T1 |
| Components | `Components` | Reference sheet: tokens, states, 375 px layouts |

### Home layout (screen 1)

1. **Hero**, two columns (copy, then a 340 px stats column); stacks under 1100 px.
   - h1: "Which **Earth terrain** stands in for a **lunar landing site**?" "Earth terrain" is set in `--earth`, "lunar landing site" in `--moon`. Solid colours, no gradient text.
   - Lede: "Pick a south-pole region. See whether a rover and a crew on foot can work each 960 m patch, which of five Earth field sites resembles it, and where the analogy breaks."
   - Buttons: primary "Start at Leibnitz Beta Plateau →" to the region; secondary "Environment checks for all 17 regions".
   - Three stat rows, each with a 48 px icon tile: "7 of 17 · Artemis III candidate regions with terrain"; "960 m · Patch: 32 × 32 cells at 30 m · 2,910 patches"; "5 sites · Earth field sites · 15 matches per patch" (gold icon). Compute the counts from the data; don't hard-code them.
2. **Sky and map row**, 1.3 : 1 columns, aligned to the top.
   - "Sky above the south pole": a 640 × 330 SVG of the real sky looking toward Earth, from [sky/sky.json](sky/sky.json). It shows stars to magnitude 5, sized by magnitude and tinted by colour index; dashed 30° and 60° altitude guides; Sirius and Canopus labelled; the horizon with 90°W, 0° and 90°E ticks; and Earth as a gold half-disc with a glow at azimuth 0 on the horizon, labelled "Earth, on the horizon". Chip "14 Nov 2026". Caption: "**Earth never climbs far:** it stays within about 7° of the horizon, which is why Earth visibility is one of the Operations gates. The Large Magellanic Cloud is almost overhead." The drawing code is `sky_panel()` in the mockup generator; its output is in `mockups/01-Regions.html`.
   - "Where the regions are": the polar map above, with region 1 selected.
3. **Region cards.** Heading "Seven regions with terrain", a one-line description, and a class legend. A 4-column grid (2 columns under 1200 px, 1 under 640 px) with one card per region:
   - number node, patch count, region name
   - rover terrain mix bar with "N% operable"
   - Operations and Survival side by side, each a score with a small "PASS" label, or the status with "no score"
   - "Open region →"

   Region 1 has a "Demo path" chip and the selected style. An eighth, dashed card: "10 more regions · Environment checks only…" linking to Environment.
4. **"Looks alike, measures different"** panel: patch `r192-c192`'s rank 1 match (Wadi Rum, cosine 0.969, 0 of 5 checks in band) against its best physical fit (rank 5, Atacama, cosine 0.952, 4 of 5). Show three slope tiles on the shared 0–20° scale (Moon, Wadi Rum, Atacama, with the best fit outlined in teal) and the button "Compare the Moon and Atacama →". Read the values from the analogs data.
5. Limits panel, then the footer.

## Not taken from Stitch

The Stitch screens looked right but invented things. Do not reintroduce any of these:

- Wrong numbers, such as Malapert Operations 58.5 (the data says 50.5), and a scatter plot whose points don't match the scores.
- Cosine as a percentage ("99.2% Spectral Cosine", "Match 94.2%"). Cosine is a shape similarity, shown as 0.969.
- "Safe Pass" percentages, "Selection Guidance", or any wording that reads as a safety rating.
- A combined or single score. Operations and Survival are never merged.
- A score next to a Fail or Unknown.
- A "Top Earth analog" per region with made-up scores.
- Quotes from invented people, stock photos with fake LOLA IDs, route lines drawn on the patch grid.
- "Telemetry network", "Signal active // nominal", "Orbital telemetry synchronized", a "Mission Specs" nav item, a user avatar.
- Teammates' names in the UI ("Darrel's scorer"): say "the team's scorer".
- Eyebrow chips above headings, gradient text, numbered section labels ("01 // SHAPE SEMANTICS").
