"""Per-tile environment scorer input: one `sites.csv` row per lunar tile.

Each tile starts from its region's baseline row (`eda_001`-`eda_007`) in the
scorer input, so window, orbital, thermal, plasma, dust, soil and regional
reference values stay region-wide. The four map-based columns are then
measured inside the tile's own 960 m bounds from the 2016 LOLA illumination
maps, using the environment pipeline's own `profile` routine
(`env_pipeline/prepare_sites.py`):

- `median_sun_visibility_fraction` and `median_earth_visibility_fraction`
- `permanently_shadowed_cell_fraction`
- `median_visible_sky_fraction`

Tiles whose bounds have no co-supported map pixels keep the regional values;
`tile_support.csv` records which tiles were measured and the pixel counts.
"""
from __future__ import annotations

import importlib.util
from contextlib import ExitStack
from pathlib import Path

import pandas as pd
import rasterio

from integration.moon_sites import REGION_ENVIRONMENT_IDS
from notebooks.shared.processing import MOON_CRS

PREPARE_SITES = 'env_algo_task/env_pipeline/prepare_sites.py'
MAPS_DIRECTORY = 'data/raw/moon/illumination_2016/geotiff/south'
MAPS = {
    'sun': 'solar_illumination/AVGVISIB_85S_060M_201608.TIF',
    'earth': 'earth_visibility/AVGVISIB_85S_060M_201608_EARTH.TIF',
    'shadow': 'permanent_shadow/LPSR_85S_060M_201608.TIF',
    'sky': 'sky_visibility/SKYV_65S_240M.TIF',
}
MAP_COLUMNS = ['median_sun_visibility_fraction', 'median_earth_visibility_fraction',
               'permanently_shadowed_cell_fraction', 'median_visible_sky_fraction']
_PROJECTION_KEYS = ('proj', 'lat_0', 'lat_ts', 'lon_0', 'R', 'a', 'b', 'x_0', 'y_0', 'units')


def load_profile(root: Path):
    """The environment pipeline's own map summary, loaded from its file."""
    spec = importlib.util.spec_from_file_location('env_prepare_sites', root / PREPARE_SITES)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.profile


def _projection(crs) -> dict:
    values = rasterio.crs.CRS.from_user_input(crs).to_dict()
    return {key: values.get(key) for key in _PROJECTION_KEYS if values.get(key) is not None}


def map_paths(root: Path, directory: str = MAPS_DIRECTORY) -> dict[str, Path]:
    paths = {name: root / directory / relative for name, relative in MAPS.items()}
    missing = [str(path.relative_to(root)) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f'Missing illumination maps {missing}; download them with '
                                '"download scripts/download_lunar_illumination_2016.py"')
    return paths


def tile_sites(tiles: pd.DataFrame, baseline: pd.DataFrame, datasets: dict, profile) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (`sites.csv` rows keyed by tile_id, per-tile measurement support)."""
    for name, dataset in datasets.items():
        if _projection(dataset.crs) != _projection(MOON_CRS):
            raise ValueError(f'The {name} map is not in the tile CRS: {dataset.crs}')
    region_of = {region: env_id for env_id, region in REGION_ENVIRONMENT_IDS.items()}
    rows = baseline.set_index('id', verify_integrity=True)
    unknown = sorted(set(tiles['region']) - set(region_of))
    missing = sorted({region_of[r] for r in tiles['region'] if r in region_of} - set(rows.index))
    if unknown or missing:
        raise ValueError(f'No baseline row for regions {unknown} or IDs {missing}')
    sites, support = [], []
    for tile in tiles.itertuples(index=False):
        row = rows.loc[region_of[tile.region]].to_dict()
        try:
            values, counts = profile(datasets, (tile.xmin, tile.ymin, tile.xmax, tile.ymax))
            row.update(values)
            measured = True
        except ValueError as error:
            counts, measured = {'reason': str(error)}, False
        sites.append({'id': tile.tile_id, **row})
        support.append({'tile_id': tile.tile_id, 'region': tile.region, 'baseline_id': region_of[tile.region],
                        'map_values_measured': measured, **counts})
    return pd.DataFrame(sites, columns=baseline.columns), pd.DataFrame(support)


def build_tile_sites(root: Path, tiles: pd.DataFrame, baseline_csv: Path, output: Path) -> Path:
    """Write scorer input rows to `output` and `tile_support.csv` beside it; return `output`."""
    baseline = pd.read_csv(baseline_csv, dtype={'id': str})
    with ExitStack() as stack:
        datasets = {name: stack.enter_context(rasterio.open(path)) for name, path in map_paths(root).items()}
        sites, support = tile_sites(tiles, baseline, datasets, load_profile(root))
    sites.to_csv(output, index=False, lineterminator='\n')
    support.to_csv(output.with_name('tile_support.csv'), index=False)
    return output
