"""Synthetic maps check per-tile environment rows; no downloaded data is needed."""
import math
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from integration.tile_environment import MAP_COLUMNS, load_profile, tile_sites
from notebooks.shared.moon_tiles import tile_id
from notebooks.shared.processing import MOON_CRS
from notebooks.shared.tests.test_moon_tiles import REGION

LEFT, TOP = -45240., 93900.   # two 960 m tiles side by side, west then east
PROFILE = load_profile(ROOT)


def write_map(folder: Path, name: str, values: np.ndarray, size: float, crs=MOON_CRS) -> Path:
    path = folder / f'{name}.tif'
    with rasterio.open(path, 'w', driver='GTiff', width=values.shape[1], height=values.shape[0], count=1,
                       dtype='float32', crs=crs, transform=from_origin(LEFT, TOP, size, size), nodata=-1) as out:
        out.write(values.astype('float32'), 1)
    return path


def synthetic_maps(folder: Path, crs=MOON_CRS) -> dict[str, Path]:
    """West tile: Sun 0.2, no shadow. East tile: Sun 0.8, half its cells permanently shadowed."""
    sun = np.full((16, 32), 0.2)
    sun[:, 16:] = 0.8
    shadow = np.zeros((16, 32))
    shadow[:8, 16:] = 1
    return {'sun': write_map(folder, 'sun', sun, 60., crs), 'earth': write_map(folder, 'earth', np.full((16, 32), 0.5), 60., crs),
            'shadow': write_map(folder, 'shadow', shadow, 60., crs),
            'sky': write_map(folder, 'sky', np.full((4, 8), 2 * math.pi), 240., crs)}


def tiles(count: int = 2) -> pd.DataFrame:
    rows = []
    for index in range(count):
        x = LEFT + 480 + 960 * index
        rows.append({'tile_id': tile_id(REGION, x, TOP - 480), 'region': REGION,
                     'xmin': x - 480, 'xmax': x + 480, 'ymin': TOP - 960, 'ymax': TOP})
    return pd.DataFrame(rows)


def baseline() -> pd.DataFrame:
    frame = pd.read_csv(ROOT / 'env_algo_task/env_pipeline/sample_input.csv', dtype={'id': str})
    return frame[frame['id'].isin(['eda_004', 'eda_001'])].reset_index(drop=True)


def run_tile_sites(paths: dict[str, Path], frame: pd.DataFrame):
    with ExitStack() as stack:
        datasets = {name: stack.enter_context(rasterio.open(path)) for name, path in paths.items()}
        return tile_sites(frame, baseline(), datasets, PROFILE)


class TileEnvironmentTests(unittest.TestCase):
    def test_map_columns_are_measured_per_tile_and_the_rest_is_regional(self):
        with tempfile.TemporaryDirectory() as folder:
            sites, support = run_tile_sites(synthetic_maps(Path(folder)), tiles())
        west, east = sites.iloc[0], sites.iloc[1]
        region_row = baseline().set_index('id').loc['eda_004']
        self.assertEqual(list(sites.columns), list(baseline().columns))
        self.assertEqual(sites['id'].tolist(), tiles()['tile_id'].tolist())
        self.assertAlmostEqual(west['median_sun_visibility_fraction'], 0.2, places=6)
        self.assertAlmostEqual(east['median_sun_visibility_fraction'], 0.8, places=6)
        self.assertEqual((west['permanently_shadowed_cell_fraction'], east['permanently_shadowed_cell_fraction']), (0.0, 0.5))
        self.assertAlmostEqual(west['median_visible_sky_fraction'], 0.5, places=6)
        self.assertAlmostEqual(west['median_earth_visibility_fraction'], 0.5, places=6)
        for column in ('orbital_radiation_counter_median', 'start_utc', 'soil_feo_wt_percent'):
            self.assertEqual(west[column], region_row[column])
        self.assertTrue(support['map_values_measured'].all())
        self.assertEqual(support['joint_60m_pixels'].tolist(), [256, 256])

    def test_tile_without_map_support_keeps_regional_values(self):
        far = tiles(1).assign(xmin=0., xmax=960., ymin=0., ymax=960., tile_id=tile_id(REGION, 480., 480.))
        with tempfile.TemporaryDirectory() as folder:
            sites, support = run_tile_sites(synthetic_maps(Path(folder)), pd.concat([tiles(1), far]))
        region_row = baseline().set_index('id').loc['eda_004']
        self.assertEqual(support['map_values_measured'].tolist(), [True, False])
        self.assertIn('outside source raster', support.loc[1, 'reason'])
        for column in MAP_COLUMNS:
            self.assertEqual(sites.iloc[1][column], region_row[column])

    def test_maps_in_another_projection_or_regions_without_baselines_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            other = synthetic_maps(Path(folder), crs='+proj=stere +lat_0=-90 +lat_ts=-71 +lon_0=0 +R=1737400 +units=m')
            with self.assertRaisesRegex(ValueError, 'not in the tile CRS'):
                run_tile_sites(other, tiles())
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'No baseline row'):
                run_tile_sites(synthetic_maps(Path(folder)), tiles().assign(region='Unknown_Region'))


if __name__ == '__main__':
    unittest.main()
