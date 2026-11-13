# Lunar Analog Finder app

A static React site (Vite + TypeScript). It reads precomputed files from `public/data/`. Nothing runs a model in the browser.

Current scope: seven lunar regions and 2,910 terrain patches. Each region has a patch map and a patch list. Each patch has rover and on-foot predictions, crossing directions, and slope and relative-elevation grids.

## Run the app

Run these from the repository root. You need Node 22 or newer.

```bash
npm --prefix app install
npm --prefix app run dev
```

Open http://localhost:5173. To check the production build:

```bash
npm --prefix app run build
npm --prefix app run preview
```

## Export the data

The export script turns a teammate's pipeline output into the files the app reads. It needs Python 3.12 and NumPy. It does not load model weights.

`--input-dir` is the folder that holds `terrain_human_walkability_lunar_inference/<run-id>/`.

This exports all seven regions. macOS or Linux:

```bash
python3 app/scripts/export_data.py --input-dir data/app_inputs
python3 -m unittest discover -s app/scripts/tests -p "test_*.py"
```

Windows (Gareth's setup):

```powershell
.\.venv\Scripts\python.exe app\scripts\export_data.py --input-dir temp
.\.venv\Scripts\python.exe -m unittest discover -s app/scripts/tests -p "test_*.py"
```

To review an export before you publish it, add `--output-dir <temporary folder>`. Then copy the files into `app/public/data/`.

To export less, add `--region leibnitz-beta-plateau`, or one region and `--patch-id "A3CLR22_10_Leibnitz_Beta_Plateau:960:32:32"`.

Options:

- `--region <name>`: export one region. Repeat it for more. Leave it out to export all seven.
- `--patch-id <source id>`: export only this patch. Repeat it for more. It needs exactly one `--region`.
- `--output-dir <folder>`: default `app/public/data`.
- `--run-id <id>`: default `20261112T120422201915Z_101366`.

The script stops with a message, and a non-zero exit code, when a record is unsafe to publish. Examples: a duplicate patch ID, an unknown class, a missing tensor, a wrong grid shape, a non-finite value.

## Data files (schema version 1)

| File | Content |
| --- | --- |
| `regions.json` | The exported regions, the source run ID, and the source's own claim boundary |
| `patches/<region>.json` | One record per patch: source ID, grid position, classes, probabilities, crossing predictions, measurements, tensor location |
| `grids/<region>.bin` | Terrain grids for every patch in that region |

Grid file layout:

- Patches are stored in the order of the `patches` array. Each record has its `grid_offset` in bytes.
- Each patch is 4,096 bytes: relative elevation (metres), then slope (degrees).
- Each channel is 32 × 32 cells in row-major order. Row 0 is the top row of the source grid.
- Each value is a little-endian signed 16-bit integer. Divide it by 10 to get the physical value. The rounding error is at most 0.05.

Route names such as `leibnitz-beta-plateau` and `r32-c32` are for URLs. Every record also keeps its original source ID.

## Pages

| URL | Page |
| --- | --- |
| `#/` | Region list |
| `#/region/<region>` | Patch map and patch list for one region |
| `#/region/<region>/patch/<patch>` | One patch |

URLs use a `#` so that links work on any static host without server rules. `src/router.ts` is the only file that knows the URL form.

## Patch map

The region page draws one square per patch with Leaflet. The map uses `L.CRS.Simple`, which is a flat grid with no basemap. Lunar coordinates are never put on an Earth map.

- Map units are source grid cells of 30 m. Each patch is 32 by 32 cells.
- x is the grid column (`top_col`). y is minus the grid row (`top_row`), because Leaflet's y axis points up.
- So row 0 is at the top, and a larger row is drawn lower. A larger column is drawn further right.
- Only patches in the data are drawn. A missing patch stays an empty gap.
- The grid is the stored grid. It is not a north-up map.

`patchBounds` in `src/components/PatchMap.tsx` is the only place that holds this convention.

A square and its row in the patch list open the same URL. The list is the keyboard route to every patch. Class colours on the map also carry a pattern: plain, striped, or cross-hatched.

## Styling

`src/styles/tokens.css` holds placeholder colours and fonts as CSS variables. Replace that file when the design tokens are ready. Terrain colour ramps are in `src/components/colorScales.ts`.
