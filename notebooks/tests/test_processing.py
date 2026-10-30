"""Analytical/synthetic checks only: no project data or notebook execution."""
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject

sys.path.insert(0, str(Path(__file__).parents[1]))
from candidate_analysis import terrain_band_components
from environment_analysis import diviner_cell_matrix
from inspection import complete_blocks
from osm_processing import extract_support
from patch_analysis import measure_patch, measure_planarity
from processing import (
    MOON_CRS,
    Grid,
    crop_native,
    decode_packed,
    diviner_chunks,
    landcover_fractions,
    mosaic_elevation,
    mosaic_landcover,
    pad_grid,
    rectangular_coverage,
    safe_output,
    select_covering_tiles,
    terrain,
    warp,
)
from retrieval_analysis import terrain_discrepancies
from screening_analysis import screen_patch
from source_analysis import compare_elevation_surfaces


class ProcessingTests(unittest.TestCase):
    def test_diviner_cell_coverage_keeps_missing_cells_and_bins(self):
        # Two cells: one only in A; the other only in B, with an invalid A row.
        # Both bins exist regionally, but no cell has both; C is wholly absent.
        observations = pd.DataFrame({
            'clon': [10.0, 20.0, 20.0], 'clat': [-88.0, -87.0, -87.0],
            'source_product': ['A', 'A', 'B'], 'tbol': [40.0, np.nan, 80.0],
            'valid_temperature': [True, False, True],
        })
        result = diviner_cell_matrix(observations, ['A', 'B', 'C'])
        self.assertEqual(list(result.columns), ['A', 'B', 'C'])
        np.testing.assert_allclose(result.to_numpy(), [[40, np.nan, np.nan], [np.nan, 80, np.nan]], equal_nan=True)
        self.assertEqual(int(np.isfinite(result[['A', 'B']].to_numpy()).all(axis=1).sum()), 0)

    def test_diviner_cell_matrix_rejects_ambiguous_or_invalid_records(self):
        row = pd.DataFrame({'clon': [10.0], 'clat': [-88.0], 'source_product': ['A'],
                            'tbol': [40.0], 'valid_temperature': [True]})
        for invalid, products in [
            (pd.concat([row, row]), ['A']), (row, ['A', 'A']), (row, ['B']),
            (row.assign(valid_temperature=False), ['A']),
            (row.assign(tbol=np.inf), ['A']), (row.assign(clat=np.nan), ['A']),
        ]:
            with self.assertRaises(ValueError):
                diviner_cell_matrix(invalid, products)

    def test_surface_comparison_rejects_incomplete_or_incompatible_grids(self):
        for reference, estimate in [
            (np.zeros((2, 2)), np.zeros((1, 2))),
            (np.zeros(4), np.zeros(4)),
            (np.empty((0, 2)), np.empty((0, 2))),
            (np.array([[0., np.nan], [2., 3.]]), np.zeros((2, 2))),
            (np.zeros((2, 2)), np.full((2, 2), np.inf)),
        ]:
            with self.subTest(shape=reference.shape), self.assertRaises(ValueError):
                compare_elevation_surfaces(reference, estimate)

    def test_surface_comparison_separates_constant_offset_from_shape_difference(self):
        reference = np.array([[0., 1.], [2., 3.]])
        shifted = compare_elevation_surfaces(reference, reference + 7)
        self.assertEqual(shifted['mean_offset_m'], 7)
        self.assertEqual(shifted['offset_removed_rmse_m'], 0)
        self.assertEqual(shifted['offset_removed_p95_abs_m'], 0)
        changed = compare_elevation_surfaces(reference, np.array([[9., 12.], [13., 12.]]))
        self.assertEqual(changed['mean_offset_m'], 10)
        self.assertEqual(changed['offset_removed_rmse_m'], 1)
        self.assertEqual(changed['offset_removed_p95_abs_m'], 1)

    def test_candidate_components_preserve_relief_floor_empty_pools_and_invalid_data(self):
        query = np.array([1., 2., 10., .1, 1.])
        np.testing.assert_allclose(terrain_band_components(query, np.array([[1., 2., 20., .1, 1.]])), [[0., 0., 2., 0.]])
        self.assertEqual(terrain_band_components(query, np.empty((0, 5))).shape, (0, 4))
        for invalid in [np.array([1., 2., np.nan, .1, 1.]), np.array([4., 2., 10., .1, 1.]),
                        np.array([1., 2., 10., 1.1, 1.]), np.array([1., 2., -1., .1, 1.])]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                terrain_band_components(invalid, query[None, :])

    def test_candidate_components_keep_each_physical_band_visible(self):
        query = np.array([10., 20., 100., .2, 5.])
        candidates = np.array([[12., 26., 80., .5, 5.], [9., 22., 110., .1, 8.]])
        # First row: 2deg,6deg,20m at an 8m band,.3 fraction.
        # Second row: 1deg,2deg,10m at a 10m band,.1 fraction.
        expected = np.array([[2., 3., 2.5, 3.], [1., 1., 1., 1.]])
        np.testing.assert_allclose(terrain_band_components(query, candidates), expected)

    def test_screening_rejects_malformed_or_impossible_fractions(self):
        valid = np.ones((2, 2))
        zero = np.zeros((2, 2))
        for invalid in [np.ones((2, 3)), np.ones(4), np.empty((0, 0)),
                        np.full((2, 2), np.inf), np.full((2, 2), -.1), np.full((2, 2), 1.1)]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                screen_patch(valid, invalid, zero, zero, zero)

    def test_screening_alternatives_keep_support_and_hard_exclusions(self):
        coverage, bare = np.ones((2, 2)), np.ones((2, 2))
        zero = np.zeros((2, 2))
        tiny = np.array([[.001, 0.], [0., 0.]])
        for fields in [(coverage, bare, tiny, zero, zero), (coverage, bare, zero, tiny, zero),
                       (coverage, bare, zero, zero, tiny), (np.full((2, 2), .98), bare, zero, zero, zero),
                       (coverage, np.full((2, 2), np.nan), zero, zero, zero)]:
            with self.subTest(fields=fields):
                result = screen_patch(*fields)
                for policy in ['baseline', 'patch_mean_bare80', 'no_bare_requirement']:
                    self.assertFalse(result[policy])
        boundary = screen_patch(np.full((2, 2), .99), bare, zero, zero, zero)
        self.assertTrue(boundary['baseline'])

    def test_screening_separates_cell_and_patch_bare_requirements(self):
        coverage = np.ones((2, 2))
        absent = np.zeros((2, 2))
        result = screen_patch(coverage, np.array([[.6, 1.], [.6, 1.]]), absent, absent, absent)
        self.assertFalse(result['baseline'])
        self.assertTrue(result['patch_mean_bare80'])
        self.assertTrue(result['no_bare_requirement'])
        self.assertAlmostEqual(result['bare_mean'], .8)
        self.assertEqual(result['bare_failure_cells'], 2)
        # An 80% requirement at each cell differs from averaging the patch first.
        result = screen_patch(coverage, np.full((2, 2), .8), absent, absent, absent)
        self.assertTrue(result['baseline'])
        result = screen_patch(coverage, np.zeros((2, 2)), absent, absent, absent)
        self.assertFalse(result['patch_mean_bare80'])
        self.assertTrue(result['no_bare_requirement'])

    def test_landcover_mosaic_rejects_shifted_source_lattices(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            paths = []
            for i, left in enumerate([0., 1.5]):
                path = folder / f'{i}.tif'
                with rasterio.open(path, 'w', driver='GTiff', width=2, height=2, count=1,
                                   dtype='uint8', nodata=0, crs='EPSG:32611',
                                   transform=from_origin(left, 2, 1, 1)) as dst:
                    dst.write(np.full((2, 2), 60, dtype='uint8'), 1)
                paths.append(path)
            with self.assertRaisesRegex(ValueError, 'aligned'):
                mosaic_landcover(paths, folder / 'shifted.tif', (0, 0, 3.5, 2))

    def test_landcover_mosaic_preserves_classes_across_four_tile_corner(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            paths = []
            for name, left, top, code in [('nw', 0, 6, 60), ('ne', 3, 6, 50),
                                         ('sw', 0, 3, 40), ('se', 3, 3, 80)]:
                path = folder / f'{name}.tif'
                with rasterio.open(path, 'w', driver='GTiff', width=3, height=3, count=1,
                                   dtype='uint8', nodata=0, crs='EPSG:32611',
                                   transform=from_origin(left, top, 1, 1)) as dst:
                    dst.write(np.full((3, 3), code, dtype='uint8'), 1)
                paths.append(path)
            output = folder / 'mosaic.tif'
            mosaic_landcover(paths, output, (1, 1, 5, 5))
            with rasterio.open(output) as src:
                np.testing.assert_array_equal(src.read(1),
                                              [[60, 60, 50, 50], [60, 60, 50, 50],
                                               [40, 40, 80, 80], [40, 40, 80, 80]])
                self.assertEqual(src.transform, from_origin(1, 5, 1, 1))
                self.assertEqual(src.dtypes, ('uint8',))
            fractions = landcover_fractions(output, Grid('EPSG:32611', from_origin(1, 5, 4, 4), 1, 1))
            for name in ['bare_sparse_fraction', 'built_fraction', 'crop_fraction', 'water_fraction']:
                np.testing.assert_allclose(fractions[name], [[.25]], atol=1e-7)
            np.testing.assert_allclose(fractions['source_coverage'], [[1.]])
            with self.assertRaisesRegex(ValueError, 'do not cover'):
                mosaic_landcover(paths[:-1], folder / 'gap.tif', (1, 1, 5, 5))

    def test_terrain_discrepancies_use_physical_bands_and_worst_component(self):
        query = np.array([10., 20., 100., .2, 10.])
        candidates = np.array([[10., 20., 100., .2, 10.],
                               [11., 22., 110., .4, 12.],
                               [10., 20., 80., .2, 10.]])
        # Second candidate hits all three base bands, but both added bands by 2.
        # Third relief difference=20 m; denominator=.1*80=8 m, ratio=2.5.
        result = terrain_discrepancies(query, candidates)
        np.testing.assert_allclose(result['baseline'], [0., 1., 2.5])
        np.testing.assert_allclose(result['with_planarity'], [0., 2., 2.5])
        np.testing.assert_allclose(result['with_local_sd'], [0., 2., 2.5])
        # Low-relief denominators use the physical floors, with symmetric results.
        low = np.array([1., 2., 2., 0., .2])
        high = np.array([1., 2., 7., 0., 1.2])
        for first, second in [(low, high), (high, low)]:
            values = terrain_discrepancies(first, second[None, :])
            for name in ('baseline', 'with_planarity', 'with_local_sd'):
                np.testing.assert_allclose(values[name], [1.])

    def test_terrain_discrepancies_reject_invalid_features_and_support_empty_pools(self):
        query = np.array([10., 20., 100., .2, 10.])
        for bad in [np.array([1., 2.]), np.array([[1., 2., 3., .1, 1.]]),
                    np.array([10., 20., np.nan, .2, 10.]),
                    np.array([10., 91., 100., .2, 10.]),
                    np.array([20., 10., 100., .2, 10.]),
                    np.array([10., 20., -1., .2, 10.]),
                    np.array([10., 20., 100., 1.1, 10.])]:
            with self.subTest(query=bad), self.assertRaises(ValueError):
                terrain_discrepancies(bad, query[None, :])
        for bad in [query, np.zeros((2, 4)), np.array([[10., 20., 100., .2, -1.]])]:
            with self.subTest(candidates=bad), self.assertRaises(ValueError):
                terrain_discrepancies(query, bad)
        empty = terrain_discrepancies(query, np.empty((0, 5)))
        for name in ('baseline', 'with_planarity', 'with_local_sd'):
            self.assertEqual(len(empty[name]), 0)

    def test_planarity_separates_tilt_from_nonplanar_relief(self):
        # A plane has no residual; a symmetric bowl is orthogonal to tilt.
        plane = np.array([[7., 9., 11.], [10., 12., 14.], [13., 15., 17.]])
        bowl = np.array([[2., 1., 2.], [1., 0., 1.], [2., 1., 2.]])
        for surface in [plane, np.full((3, 3), 7.)]:
            result = measure_planarity(surface)
            self.assertAlmostEqual(result['plane_residual_rms_m'], 0., places=12)
            self.assertAlmostEqual(result['plane_residual_fraction'], 0., places=12)
        # Bowl mean=4/3, mean squared deviation=4/9. Tilt variance=26/3.
        for surface, fraction in [(bowl, 1.), (bowl + plane, np.sqrt(2 / 41))]:
            result = measure_planarity(surface)
            self.assertAlmostEqual(result['plane_residual_rms_m'], 2 / 3, places=12)
            self.assertAlmostEqual(result['plane_residual_fraction'], fraction, places=12)
            self.assertEqual(result, measure_planarity(surface + 100))

    def test_planarity_rejects_incomplete_or_degenerate_grids(self):
        for surface in [np.zeros((1, 1)), np.zeros((2, 3)), np.zeros((0, 0)),
                        np.zeros(3), np.full((2, 2), np.nan), np.full((2, 2), np.inf)]:
            with self.subTest(shape=surface.shape), self.assertRaises(ValueError):
                measure_planarity(surface)

    def test_patch_metrics_preserve_physical_relief_and_slope(self):
        # Four ordered heights: P05=1.5, P95=28.5; slope P90=27 degrees.
        metrics = measure_patch(np.array([[0., 10.], [20., 30.]]),
                                np.array([[0., 10.], [20., 30.]]),
                                np.array([[1., 2.], [3., 4.]]))
        expected = {
            'elevation_mean_m': 15., 'relief_m': 30., 'central_relief_m': 27.,
            'slope_median_deg': 15., 'slope_p90_deg': 27., 'local_sd_median_m': 2.5,
        }
        self.assertEqual(set(metrics), set(expected))
        for name, value in expected.items():
            # Linear quantile interpolation can differ by float64 roundoff.
            self.assertAlmostEqual(metrics[name], value, places=12)

    def test_patch_metrics_reject_incomplete_or_incompatible_inputs(self):
        heights = np.zeros((2, 2))
        slope = np.zeros((2, 2))
        roughness = np.ones((2, 2))
        invalid = [
            (np.array([[0., np.nan], [0., 0.]]), slope, roughness),
            (heights, np.full((2, 2), np.inf), roughness),
            (heights, slope, np.ones((2, 3))),
            (np.zeros((2, 3)), np.zeros((2, 3)), np.ones((2, 3))),
            (np.zeros((0, 0)), np.zeros((0, 0)), np.zeros((0, 0))),
            (heights, np.full((2, 2), 91.), roughness),
            (heights, np.full((2, 2), -1.), roughness),
            (heights, slope, -roughness),
        ]
        for inputs in invalid:
            with self.subTest(shapes=[a.shape for a in inputs]), self.assertRaises(ValueError):
                measure_patch(*inputs)


    def test_rectangular_coverage_keeps_short_mask_edges_unknown(self):
        grid = Grid(MOON_CRS, from_origin(0, 60, 30, 30), 3, 3)
        # Source spans x=0..45, y=15..60: full, half, quarter and outside cells.
        np.testing.assert_allclose(rectangular_coverage(grid, (0, 15, 45, 60)),
                                   [[1, .5, 0], [.5, .25, 0], [0, 0, 0]])
        # A count map 5 m shorter than the source leaves the missing strip unknown.
        np.testing.assert_allclose(rectangular_coverage(grid, (0, 5, 55, 60)),
                                   [[1, 5/6, 0], [5/6, 25/36, 0], [0, 0, 0]])
        with self.assertRaises(ValueError):
            rectangular_coverage(grid, (1, 0, 0, 1))

    def test_complete_blocks_excludes_holes_and_partial_edge_blocks(self):
        mask = np.ones((5, 7), dtype=bool)
        mask[0, 0] = False
        mask[3, 4] = False
        mask[4, 6] = False  # Outside the six complete 2-by-2 candidates.
        np.testing.assert_array_equal(
            complete_blocks(mask, 2), [[False, True, True], [True, True, False]])
        self.assertEqual(complete_blocks(mask, 8).size, 0)
        invalid_sides: list[Any] = [0, -1, 1.5, True]
        for invalid in invalid_sides:
            with self.assertRaises(ValueError):
                complete_blocks(mask, invalid)
        with self.assertRaises(ValueError):
            complete_blocks(np.array([[1.0, np.nan]]), 1)

    def test_actual_shifted_tile_footprints_require_all_neighbors(self):
        footprints = {'core': (-.1, .1, .9, 1.1), 'south': (-.1, -.9, .9, .1),
                      'east': (.9, .1, 1.9, 1.1), 'corner': (.9, -.9, 1.9, .1),
                      'distant': (5, 5, 6, 6)}
        self.assertEqual(select_covering_tiles(footprints, (0, 0, 1, 1)),
                         ['core', 'corner', 'east', 'south'])
        del footprints['corner']
        with self.assertRaisesRegex(ValueError, 'do not cover'):
            select_covering_tiles(footprints, (0, 0, 1, 1))

    def test_grid_padding_preserves_original_lattice(self):
        grid = Grid('EPSG:32612', from_origin(300, 600, 30, 30), 4, 3)
        padded = pad_grid(grid, 5)
        self.assertEqual((padded.width, padded.height), (14, 13))
        self.assertEqual(padded.transform, from_origin(150, 750, 30, 30))

    def test_terrain_roi_mask_preserves_source_halo(self):
        # dz/dx=1 yields 45 degrees; three-column variance is (900+0+900)/3.
        z = np.tile(np.arange(5, dtype=float) * 30, (5, 1))
        inside = np.zeros((5, 5), dtype=bool)
        inside[1:4, 1:4] = True
        result = terrain(z, 30, 3, output_mask=inside)
        np.testing.assert_allclose(result['slope_deg'][inside], 45)
        np.testing.assert_allclose(result['local_elevation_std_m'][inside], np.sqrt(600))
        np.testing.assert_allclose(result['laplacian_per_m'][inside], 0)
        np.testing.assert_allclose(result['relative_elevation_m'][1, 1:4], [-30, 0, 30])
        for values in result.values():
            self.assertTrue(np.isnan(values[~inside]).all())
        asymmetric = inside.copy()
        asymmetric[:, 3] = False
        centered = terrain(z, 30, 3, output_mask=asymmetric)
        np.testing.assert_allclose(centered['relative_elevation_m'][1, 1:3], [-15, 15])
        # A genuine missing source neighbor still invalidates the affected derivative.
        z[0, 1] = np.nan
        result = terrain(z, 30, 3, output_mask=inside)
        self.assertTrue(np.isnan(result['slope_deg'][1, 1]))
        self.assertAlmostEqual(result['slope_deg'][3, 3], 45)

    def test_native_crop_requires_documented_missing_crs_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / 'unreferenced.tif', Path(directory) / 'crop.tif'
            transform = from_origin(100, 200, 5, 5)
            with rasterio.open(source, 'w', driver='GTiff', width=4, height=4,
                               count=1, dtype='int16', transform=transform, nodata=-9999) as dst:
                dst.write(np.array([[10, 10, 10, 10], [10, -9999, 20, 10],
                                    [10, 30, 40, 10], [10, 10, 10, 10]], dtype='int16'), 1)
                dst.scales = (0.5,)
            with self.assertRaisesRegex(ValueError, 'Missing CRS.*unreferenced'):
                crop_native(source, target, (105, 185, 115, 195), MOON_CRS)
            self.assertFalse(target.exists())
            with self.assertRaisesRegex(ValueError, 'documented fallback'):
                crop_native(source, target, (105, 185, 115, 195), MOON_CRS,
                            fallback_crs=MOON_CRS)
            metadata = crop_native(source, target, (105, 185, 115, 195), MOON_CRS,
                                   fallback_crs=MOON_CRS, crs_evidence='Product README')
            with rasterio.open(target) as result:
                self.assertEqual(result.crs, CRS.from_string(MOON_CRS))
                self.assertEqual(result.transform, from_origin(105, 195, 5, 5))
                np.testing.assert_allclose(result.read(1), [[np.nan, 10], [15, 20]])
                self.assertEqual(result.tags()['crs_evidence'], 'Product README')
            self.assertTrue(metadata['crs_inferred'])
            with rasterio.open(source) as original:
                self.assertIsNone(original.crs)

    def test_lunar_notebook_aligns_count_mask_without_filling_gaps(self):
        notebook = json.loads((Path(__file__).parents[1] / 'preprocessing/05_lunar_terrain_environment.ipynb').read_text(encoding='utf-8'))
        cell = next(''.join(c['source']) for c in notebook['cells']
                    if 'with Run(ROOT, "lunar_terrain_environment"' in ''.join(c['source']))
        # Exercise the notebook's actual alignment/aggregation block, without its run/output shell.
        block = textwrap.dedent(cell[cell.index('        with rasterio.open(info["elevation"])'):
                                     cell.index('        del heights')])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            elevation, mask = root / 'elevation.tif', root / 'mask.tif'
            grid = Grid(MOON_CRS, from_origin(0, 35, 5, 5), 7, 7)
            with rasterio.open(elevation, 'w', driver='GTiff', width=7, height=7,
                               count=1, dtype='float32', crs=grid.crs, transform=grid.transform) as dst:
                dst.write(np.full((7, 7), 100, dtype='float32'), 1)
            with rasterio.open(mask, 'w', driver='GTiff', width=2, height=2,
                               count=1, dtype='float32', crs=grid.crs,
                               transform=from_origin(0, 35, 15, 15), nodata=-9999) as dst:
                dst.write(np.array([[2, 0], [-9999, 4]], dtype='float32'), 1)
            scope: dict[str, Any] = {'info': {'elevation': elevation, 'mask': mask}, 'grid': grid,
                                     'np': np, 'rasterio': rasterio, 'Resampling': Resampling,
                                     'reproject': reproject, 'Grid': Grid, 'warp': warp}
            exec(compile(block, 'lunar_alignment', 'exec'), scope)  # noqa: S102 - trusted local notebook regression
            expected = np.zeros((7, 7), dtype=bool)
            expected[:3, :3] = True
            expected[3:6, 3:6] = True
            np.testing.assert_array_equal(np.isfinite(scope['elevation']), expected)
            np.testing.assert_allclose(scope['elevation'][expected], 100)
            np.testing.assert_allclose(scope['fraction'], expected.astype('float32'))

    def test_lunar_crs_matches_sdem_polar_standard_parallel(self):
        # CRS metadata from the delivered SDEM GeoTIFF, independent of our PROJ string.
        source_crs = CRS.from_wkt(
            'PROJCS["Moon (2015) - Sphere / Ocentric / South Polar",'
            'GEOGCS["Moon (2015) - Sphere / Ocentric",'
            'DATUM["Moon (2015) - Sphere",SPHEROID["Moon (2015) - Sphere",1737400,0]],'
            'PRIMEM["Reference Meridian",0],UNIT["degree",0.0174532925199433]],'
            'PROJECTION["Polar_Stereographic"],PARAMETER["latitude_of_origin",-90],'
            'PARAMETER["central_meridian",0],PARAMETER["false_easting",0],'
            'PARAMETER["false_northing",0],UNIT["metre",1],'
            'AXIS["Easting",NORTH],AXIS["Northing",NORTH]]'
        )
        self.assertEqual(source_crs, CRS.from_string(MOON_CRS))

    def test_adjacent_tiles_form_continuous_interpolated_plane(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for index in range(2):
                path = root / f'tile{index}.tif'
                heights = np.tile(np.arange(5 + index * 40, 40 + index * 40, 10, dtype='float32'), (4, 1))
                with rasterio.open(path, 'w', driver='GTiff', height=4, width=4, count=1, dtype='float32',
                                   crs='EPSG:32612', transform=from_origin(index*40,40,10,10), nodata=np.nan) as dst:
                    dst.write(heights,1)
                paths.append(path)
            merged = root/'mosaic.tif'
            mosaic_elevation(paths, merged)
            grid = Grid('EPSG:32612', from_origin(5,35,10,10),7,3)
            actual = warp(merged,grid)
            np.testing.assert_allclose(actual, np.tile(np.arange(10,80,10),(3,1)))

    def test_newer_osm_node_outside_zone_removes_stale_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths=[]
            for version,lon in ((1,0.5),(2,2.0)):
                path=root/f'v{version}.osm'
                path.write_text(f'<osm version="0.6"><node id="3" version="{version}" lat="0.5" lon="{lon}"><tag k="place" v="village"/></node></osm>')
                paths.append(path)
            result=extract_support(paths,(0,0,1,1),root/'out.geojson')
            self.assertEqual(result['feature_count'],0)
            self.assertEqual(result['diagnostics']['superseded_selected_features'],1)

    def test_plane_slope_laplacian_and_hole_support(self):
        _rows, columns = np.mgrid[:15, :15]
        z = columns * 30.0  # dz/dx = 1: 45 degrees, zero Laplacian.
        result = terrain(z, 30, 3)
        np.testing.assert_allclose(result["slope_deg"][2:-2, 2:-2], 45)
        np.testing.assert_allclose(result["laplacian_per_m"][2:-2, 2:-2], 0)
        # Three columns with deviations -30,0,30 => std sqrt(600).
        np.testing.assert_allclose(result["local_elevation_std_m"][2:-2, 2:-2], np.sqrt(600))
        z[7, 7] = np.nan
        hole = terrain(z, 30, 3)
        self.assertTrue(np.isnan(hole["slope_deg"][6:9, 6:9]).all())
        self.assertTrue(np.isnan(hole["slope_deg"][0]).all())

    def test_mask_before_scaling_and_raw_output_rejected(self):
        np.testing.assert_allclose(decode_packed([100, -32768], [-32768], .01, -1), [0, np.nan])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(safe_output(root, root / "data/processed/a"), root / "data/processed/a")
            with self.assertRaises(ValueError):
                safe_output(root, root / "data/raw/a")

    def test_class_fractions_not_average_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "classes.tif"
            data = np.array([[50, 60], [60, 0]], dtype="uint8")
            with rasterio.open(path, "w", driver="GTiff", width=2, height=2, count=1,
                               dtype="uint8", crs="EPSG:32612", transform=from_origin(0, 20, 10, 10), nodata=0) as dst:
                dst.write(data, 1)
            grid = Grid("EPSG:32612", from_origin(0, 20, 20, 20), 1, 1)
            result = landcover_fractions(path, grid)
            self.assertAlmostEqual(float(result["built_fraction"][0, 0]), 1 / 3, places=6)
            self.assertAlmostEqual(float(result["bare_sparse_fraction"][0, 0]), 2 / 3, places=6)
            self.assertAlmostEqual(float(result["source_coverage"][0, 0]), .75, places=6)

    def test_scaled_raster_crop_and_warp(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "source.tif", Path(directory) / "crop.tif"
            grid = Grid("EPSG:32612", from_origin(0, 40, 10, 10), 4, 4)
            raw = np.full((4, 4), 100, dtype="int16")
            raw[0, 0] = -32768
            with rasterio.open(source, "w", driver="GTiff", width=4, height=4, count=1, dtype="int16",
                               crs=grid.crs, transform=grid.transform, nodata=-32768) as dst:
                dst.write(raw, 1)
                dst.scales = (.01,)
                dst.offsets = (.5,)
            metadata = crop_native(source, target, (0, 0, 40, 40), grid.crs,
                                   fallback_crs=MOON_CRS, crs_evidence='Unused fallback')
            self.assertFalse(metadata['crs_inferred'])
            with rasterio.open(target) as result:
                self.assertEqual(result.crs, CRS.from_string(grid.crs))
                self.assertEqual(result.scales, (1.0,))
                self.assertAlmostEqual(float(result.read(1)[1, 1]), 1.5)
                self.assertTrue(np.isnan(result.read(1)[0, 0]))
            np.testing.assert_allclose(warp(source, grid)[1:, 1:], 1.5)

    def test_diviner_layout_and_special_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Four fixed-width fields, independent synthetic PDS layout.
            rows = [f'{-10:8.2f}{-85:8.2f}{200:8.2f}{12:8.2f}\n',
                    f'{-11:8.2f}{-86:8.2f}{-9999:8.2f}{13:8.2f}\n']
            (root / "sample.tab").write_bytes(''.join(rows).encode('ascii'))
            fields = ''.join(f'<Field_Character><name>{name}</name><field_location>{1+8*i}</field_location>'
                             '<field_length>8</field_length><Special_Constants><unknown_constant>-9999</unknown_constant>'
                             '</Special_Constants></Field_Character>' for i, name in enumerate(('clon','clat','tbol','ltim')))
            label = root / "sample.xml"
            label.write_text('<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"><File_Area_Observational>'
                             '<File><file_name>sample.tab</file_name></File><Table_Character><offset>0</offset>'
                             '<records>2</records><Record_Character><record_length>33</record_length>' + fields +
                             '</Record_Character></Table_Character></File_Area_Observational></Product_Observational>')
            chunks = list(diviner_chunks(label, 1))
            self.assertEqual(len(chunks), 2)
            self.assertEqual(chunks[0]['tbol'].iloc[0], 200)
            self.assertTrue(np.isnan(chunks[1]['tbol'].iloc[0]))

    def test_osm_clips_crossing_way_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "tiny.osm"
            source.write_text('''<osm version="0.6"><node id="1" version="1" lat="0.5" lon="-1"/>
            <node id="2" version="1" lat="0.5" lon="2"/>
            <node id="3" version="1" lat="0.5" lon="0.5"><tag k="place" v="village"/></node>
            <way id="10" version="1"><nd ref="1"/><nd ref="2"/><tag k="highway" v="track"/></way></osm>''')
            output = root / "out.geojson"
            result = extract_support([source, source], (0, 0, 1, 1), output)
            self.assertEqual(result["feature_count"], 2)
            self.assertEqual(result["diagnostics"]["duplicates"], 2)
            import json
            collection = json.loads(output.read_text())
            line = next(f for f in collection["features"] if f["id"] == "way/10")
            self.assertEqual(line["geometry"]["coordinates"], [[0.0, .5], [1.0, .5]])


if __name__ == "__main__":
    unittest.main()
