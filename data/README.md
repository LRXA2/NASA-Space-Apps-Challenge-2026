# Data folder

Git tracks only this file and the empty folders (`.gitkeep`). Everything else under `data/` stays on your machine. This page lists what to put where so that `python -m integration.run_all` works.

Folder and run names must match exactly: [`integration/run_all.json`](../integration/run_all.json) and [the similarity `config.json`](../notebooks/modeling/terrain_similarity/pipeline/config.json) point to these runs by name.

## Needed by `run_all`

| Put this | Here | From |
| --- | --- | --- |
| Hanxi's walkability inference run | `processed/terrain_human_walkability_lunar_inference/20261112T120422201915Z_101366/` | Hanxi (`terrain_human_walkability_lunar_inference.zip`) |
| Aarron's prepared tiles | `processed/terrain_learning_readiness/20261101T064233918547Z_4a05ac/` | Aarron (`CNN terrain similarity stuff.zip`, `data/` folder) |
| Aarron's trained similarity model | `processed/terrain_similarity_cnn/20261101T082707986851Z_5413e6/` | Same zip |
| Aarron's rotation/reflection cache | `processed/terrain_similarity_orientation/20261102T073257899753Z_7b9c4f/` | Same zip |
| Solar illumination map | `raw/moon/illumination_2016/geotiff/south/solar_illumination/AVGVISIB_85S_060M_201608.TIF` | [PGDA Product 69](https://pgda.gsfc.nasa.gov/products/69): Average solar illumination, 85S-90S, 60 m/px, **TIF** (32.4 MiB) |
| Earth visibility map | `raw/moon/illumination_2016/geotiff/south/earth_visibility/AVGVISIB_85S_060M_201608_EARTH.TIF` | Same page: Average Earth visibility, 85S-90S, 60 m/px, **TIF** (23.7 MiB) |
| Permanent shadow map | `raw/moon/illumination_2016/geotiff/south/permanent_shadow/LPSR_85S_060M_201608.TIF` | Same page: Permanent shadow, 85S-90S, 60 m/px, **TIF** (0.6 MiB) |
| Sky visibility map | `raw/moon/illumination_2016/geotiff/south/sky_visibility/SKYV_65S_240M.TIF` | Same page: Sky visibility, 65S-90S, 240 m/px, **TIF** (59.8 MiB) |

Copy each run folder whole. The code checks every file against the run's `provenance.json`, so don't edit, rename or re-save files inside a run.

The four maps can also come from the [download script](../download%20scripts/README.md#lunar-illumination-2016-polar-maps) (`--output "data/raw/moon/illumination_2016" --skip-img --download`). It fetches all ten south-pole maps (318 MiB), six of which `run_all` doesn't use.

**Outside `data/`:** the model weights. Copy `model.pt` from `processed/terrain_similarity_cnn/20261101T082707986851Z_5413e6/full_context/region_balanced/` to `notebooks/modeling/terrain_similarity/weights/20261101T082707986851Z_5413e6/full_context/region_balanced/model.pt`.

Without the maps, run `python -m integration.run_all --environment-scope region` (region-level environment scores) or `--no-environment`.

## Created by the code

Each run writes a new timestamped folder; nothing needs to be supplied.

| Folder | Written by |
| --- | --- |
| `processed/moon_tiles/` | Shared tile IDs (`notebooks/shared/moon_tiles.py`) |
| `processed/moon_sites/` | Per-tile site table (`integration/moon_sites.py`) |
| `processed/terrain_similarity_tile_matches/` | Earth matches per tile (similarity pipeline `--tiles` mode) |
| `processed/terrain_similarity_pipeline/` | Two-site comparison (similarity pipeline `--moon-site`/`--earth-site`) |
| `processed/moon_pipeline/` | `run_all`: the combined folder the app export reads |

Other folders under `raw/` and `processed/` come from the EDA notebooks and download scripts; see the [notebook index](../notebooks/README.md) and [download instructions](../download%20scripts/README.md).
