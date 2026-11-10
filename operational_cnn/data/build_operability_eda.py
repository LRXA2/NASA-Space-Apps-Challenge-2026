"""Build current-run Earth terrain tensors and provisional route-label EDA.

This stage performs no CNN training. It uses only the five accepted development
regions and writes an isolated, provenance-recorded processed run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio

from operational_cnn.labels.route_labels import (
    DIRECTIONS,
    directional_connectivity,
    local_elevation_std,
    operational_class,
    spatial_group,
)
from notebooks.shared.inspection import verify_run
from notebooks.shared.processing import Run


CHANNELS = ('relative_elevation_m', 'slope_deg', 'roughness_90m', 'roughness_330m', 'laplacian_per_m')
REGIONS = {'northern_arizona', 'lanzarote', 'atacama_san_pedro', 'death_valley', 'wadi_rum'}


def validate_config(config: dict[str, Any]) -> None:
    if config.get('schema_version') != 1 or config.get('spacing_m') != 30:
        raise ValueError('Only schema 1 on the accepted 30 m grid is supported')
    sizes = config.get('patch_sizes_m')
    if sizes != sorted(set(sizes or [])) or not sizes or any(size % 30 for size in sizes):
        raise ValueError('Patch sizes must be distinct sorted multiples of 30 m')
    if config.get('primary_patch_size_m') not in sizes:
        raise ValueError('Primary patch size must be included')
    if config.get('roughness_windows_cells') != [3, 11]:
        raise ValueError('This first experiment requires 90 m and 330 m roughness')
    if set(config.get('source_runs', {})) != REGIONS:
        raise ValueError('Exactly the five approved Earth development regions are required')
    fraction = config.get('minimum_natural_fraction')
    if type(fraction) not in {int, float} or not 0 <= fraction <= 1:
        raise ValueError('Invalid natural fraction')
    scenarios = config.get('scenarios', {})
    if list(scenarios) != ['conservative', 'nominal', 'permissive']:
        raise ValueError('Expected ordered conservative, nominal and permissive scenarios')
    limits = [scenarios[name]['hard_slope_deg'] for name in scenarios]
    if not all(np.isfinite(limits)) or limits != sorted(limits) or len(set(limits)) != 3:
        raise ValueError('Scenario slope limits must be finite and strictly increasing')


def read_raster(path: Path) -> tuple[np.ndarray, tuple[Any, ...]]:
    with rasterio.open(path) as source:
        if (source.count != 1 or source.crs is None or not source.crs.is_projected
                or source.crs.linear_units != 'metre' or source.res != (30., 30.)
                or source.scales != (1.,) or source.offsets != (0.,)):
            raise ValueError(f'Expected unscaled projected 30 m raster: {path}')
        values = source.read(1, masked=True).astype(np.float32).filled(np.nan)
        return values, (source.shape, source.transform, source.crs)


def source_folder(root: Path, run_relative: str, region: str) -> Path:
    run = (root / run_relative).resolve()
    processed = (root / 'data/processed').resolve()
    if not run.is_relative_to(processed):
        raise ValueError('Source run escapes data/processed')
    verify_run(run)
    return run / 'earth' / region / 'grid_30m'


def load_region(root: Path, config: dict[str, Any], region: str) -> tuple[dict[str, np.ndarray], tuple[Any, ...]]:
    folder = source_folder(root, config['source_runs'][region], region)
    names = ('elevation_m', 'slope_deg', 'local_elevation_std_m', 'laplacian_per_m',
             'valid_input_mask', 'natural_screen_mask')
    layers: dict[str, np.ndarray] = {}
    reference = None
    for name in names:
        values, grid = read_raster(folder / f'{name}.tif')
        if reference is not None and grid != reference:
            raise ValueError(f'Misaligned layer in {region}: {name}')
        reference = grid
        layers[name] = values
    layers['roughness_90m'] = local_elevation_std(layers['elevation_m'], 3)
    assert reference is not None
    return layers, reference


def center_lattice(shape: tuple[int, int], offset_row: int, offset_col: int, stride: int) -> list[tuple[int, int]]:
    """Centers whose 960 m context fits; offset 16 is the baseline origin."""
    height, width = shape
    centers = []
    for row in range(offset_row, height - 15, stride):
        if row - 16 < 0:
            continue
        for col in range(offset_col, width - 15, stride):
            if col - 16 >= 0:
                centers.append((row, col))
    return centers


def eligibility(layers: dict[str, np.ndarray], window: tuple[slice, slice], minimum_natural: float) -> tuple[bool, str, float]:
    required = ('elevation_m', 'slope_deg', 'roughness_90m', 'local_elevation_std_m', 'laplacian_per_m')
    complete = all(np.isfinite(layers[name][window]).all() for name in required)
    valid = np.asarray(layers['valid_input_mask'][window] == 1)
    natural = np.asarray(layers['natural_screen_mask'][window] == 1)
    natural_fraction = float(natural.mean())
    if not complete or not valid.all():
        return False, 'incomplete', natural_fraction
    if natural_fraction < minimum_natural:
        return False, 'natural_screen', natural_fraction
    return True, 'eligible', natural_fraction


def summarize_origin_counts(layers: dict[str, np.ndarray], region: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    stride = config['center_stride_cells']
    for size_m in config['patch_sizes_m']:
        side = size_m // config['spacing_m']
        for origin_row in (16, 32):
            for origin_col in (16, 32):
                counts = {'eligible': 0, 'incomplete': 0, 'natural_screen': 0}
                for center_row, center_col in center_lattice(layers['elevation_m'].shape, origin_row, origin_col, stride):
                    row, col = center_row - side // 2, center_col - side // 2
                    window = np.s_[row:row + side, col:col + side]
                    ok, reason, _ = eligibility(layers, window, config['minimum_natural_fraction'])
                    counts['eligible' if ok else reason] += 1
                rows.append({'region': region, 'size_m': size_m, 'origin_row': origin_row,
                             'origin_col': origin_col, **counts})
    return rows


def extract_region(root: Path, config: dict[str, Any], region: str, run: Run) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    layers, (shape, transform, crs) = load_region(root, config, region)
    origin_rows = summarize_origin_counts(layers, region, config)
    records: list[dict[str, Any]] = []
    tensors_by_size: dict[int, list[np.ndarray]] = {size: [] for size in config['patch_sizes_m']}
    class_rule = config['class_rule']
    for size_m in config['patch_sizes_m']:
        side = size_m // config['spacing_m']
        for center_row, center_col in center_lattice(shape, 16, 16, config['center_stride_cells']):
            row, col = center_row - side // 2, center_col - side // 2
            window = np.s_[row:row + side, col:col + side]
            ok, _, natural_fraction = eligibility(layers, window, config['minimum_natural_fraction'])
            if not ok:
                continue
            elevation = layers['elevation_m'][window]
            slope = layers['slope_deg'][window]
            rough90 = layers['roughness_90m'][window]
            rough330 = layers['local_elevation_std_m'][window]
            laplacian = layers['laplacian_per_m'][window]
            tensor = np.stack((elevation - elevation.mean(), slope, rough90, rough330, laplacian)).astype(np.float32)
            tensor_index = len(tensors_by_size[size_m])
            tensors_by_size[size_m].append(tensor)
            x, y = transform * (center_col + .5, center_row + .5)
            scenario_results = {
                name: directional_connectivity(slope, values['hard_slope_deg'])
                for name, values in config['scenarios'].items()
            }
            label_class = operational_class(
                scenario_results['nominal'], scenario_results['permissive'],
                min_nominal_directions=class_rule['operable_min_nominal_directions'],
                min_largest_component_fraction=class_rule['operable_min_nominal_largest_component_fraction'],
                min_permissive_directions=class_rule['marginal_min_permissive_directions'],
            )
            record: dict[str, Any] = {
                'patch_id': f'{region}:{size_m}:{center_row}:{center_col}',
                'region': region, 'size_m': size_m, 'spacing_m': 30,
                'center_row': center_row, 'center_col': center_col,
                'center_x': x, 'center_y': y, 'crs_wkt': crs.to_wkt(),
                'spatial_group': spatial_group(region, x, y, config['spatial_block_m']),
                'natural_fraction': natural_fraction,
                'tensor_shard': f'tensors/{region}_{size_m}m.npz', 'tensor_index': tensor_index,
                'label_class': label_class, 'label_source': 'generated_slope_connectivity_v1',
                'slope_median_deg': float(np.median(slope)),
                'slope_p90_deg': float(np.percentile(slope, 90)),
                'slope_max_deg': float(np.max(slope)),
                'roughness_90m_median_m': float(np.median(rough90)),
                'roughness_330m_median_m': float(np.median(rough330)),
                'relative_relief_m': float(np.max(tensor[0]) - np.min(tensor[0])),
            }
            for scenario, result in scenario_results.items():
                record[f'{scenario}_passable_fraction'] = result.passable_fraction
                record[f'{scenario}_largest_component_fraction'] = result.largest_component_fraction
                record[f'{scenario}_crossing_count'] = result.crossing_count
                for direction in DIRECTIONS:
                    record[f'{scenario}_{direction}'] = result.crossings[direction]
            records.append(record)
    for size_m, tensors in tensors_by_size.items():
        side = size_m // config['spacing_m']
        values = np.stack(tensors) if tensors else np.empty((0, len(CHANNELS), side, side), dtype=np.float32)
        np.savez_compressed(run.path(f'tensors/{region}_{size_m}m.npz'), physical=values, channels=np.array(CHANNELS))
    return records, origin_rows


def build(root: Path, config_path: Path) -> Path:
    root = root.resolve()
    config_path = config_path.resolve()
    config = json.loads(config_path.read_text(encoding='utf-8'))
    validate_config(config)
    notebook = '../operational_cnn/notebooks/37_operational_terrain_eda.ipynb'
    with Run(root, 'terrain_operability_eda', config, notebook) as run:
        run.input(config_path)
        run.input(Path(__file__))
        run.input(Path(__file__).with_name('route_labels.py'))
        all_records: list[dict[str, Any]] = []
        all_origins: list[dict[str, Any]] = []
        for region in sorted(REGIONS):
            source_run = root / config['source_runs'][region]
            run.input(source_run / 'provenance.json')
            records, origins = extract_region(root, config, region, run)
            all_records.extend(records)
            all_origins.extend(origins)
            print(region, len(records), 'eligible size-specific patches', flush=True)
        patches = pd.DataFrame(all_records)
        if patches.empty or patches['patch_id'].duplicated().any():
            raise ValueError('No patches or duplicate patch IDs')
        patches.to_csv(run.path('patches.csv'), index=False)
        pd.DataFrame(all_origins).to_csv(run.path('origin_sensitivity.csv'), index=False)
        summary = (patches.groupby(['size_m', 'region', 'label_class'], observed=True)
                   .agg(patches=('patch_id', 'size'), spatial_groups=('spatial_group', 'nunique'),
                        median_p90_slope_deg=('slope_p90_deg', 'median'),
                        median_nominal_crossings=('nominal_crossing_count', 'median'))
                   .reset_index())
        summary.to_csv(run.path('label_summary.csv'), index=False)
        class_balance = (patches.groupby(['size_m', 'label_class'], observed=True).size()
                         .rename('patches').reset_index())
        class_balance['fraction'] = class_balance.groupby('size_m')['patches'].transform(lambda x: x / x.sum())
        class_balance.to_csv(run.path('class_balance.csv'), index=False)
        correlations = []
        for (size_m, region), group in patches.groupby(['size_m', 'region']):
            numeric = group[['slope_p90_deg', 'roughness_90m_median_m',
                             'roughness_330m_median_m', 'relative_relief_m']]
            corr = numeric.corr(method='spearman')
            for first in corr.columns:
                for second in corr.columns:
                    if first < second:
                        correlations.append({'size_m': size_m, 'region': region, 'first': first,
                                             'second': second, 'spearman': corr.loc[first, second]})
        pd.DataFrame(correlations).to_csv(run.path('feature_correlations.csv'), index=False)
        run.path('README.md').write_text(
            '# Terrain operability EDA run\n\n'
            'Generated labels measure directional connectivity under declared slope scenarios. '
            'They are provisional development labels, not certified rover safety. No CNN was trained.\n',
            encoding='utf-8')
        run.record['result'] = {
            'patch_records': int(len(patches)),
            'regions': sorted(patches['region'].unique()),
            'sizes_m': sorted(patches['size_m'].unique().tolist()),
            'channels': CHANNELS,
            'trained_model': False,
            'label_status': 'provisional generated connectivity labels; requires review',
        }
    return run.directory


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--config', type=Path)
    arguments = parser.parse_args()
    default = arguments.root / 'operational_cnn/configs/operability_config.json'
    print(build(arguments.root, arguments.config or default))
