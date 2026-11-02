"""Build versioned development terrain tensors and a fixed physical baseline.

Only the explicit development allowlist is opened. No download, training, or
final-reserve inspection occurs here. Run through notebook 28 or this module.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio
from inspection import check_input, verify_run
from patch_analysis import measure_patch, measure_planarity
from processing import MOON_CRS, Run
from rasterio.warp import transform_bounds
from terrain_learning import (
    SplitFootprint,
    fit_scaler,
    prepare_patch,
    rank_candidates,
    validate_split_footprints,
)

CHANNELS = ('relative_elevation_m', 'slope_deg', 'local_elevation_std_m')
SOURCE_CHANNELS = ('elevation_m', 'slope_deg', 'local_elevation_std_m', 'relative_elevation_m', 'laplacian_per_m')
FEATURES = ['slope_median_deg', 'slope_p90_deg', 'central_relief_m', 'plane_residual_fraction', 'local_sd_median_m']
# Protect the existing, EDA-exposed scope even if a config mistakenly labels a
# reserve as development. Expanding this allowlist requires an explicit code edit.
DEVELOPMENT = {
    'earth': {'atacama_san_pedro', 'lanzarote', 'northern_arizona', 'death_valley', 'wadi_rum'},
    'moon': {'A3CLR22_10_Leibnitz_Beta_Plateau', 'A3CLR22_11_Malapert_Massif',
             'A3CLR22_12_deGerlache_Kocher_Massif', 'A3CLR22_2_Haworth',
             'A3CLR22_3_Faustini_Rim_A', 'A3CLR22_4_deGerlache_Rim_2',
             'A3CLR22_5_Connecting_Ridge_Extension'},
}


def validate_config(config: dict[str, Any]) -> None:
    """Fail before opening rasters when a region, fold, or physical scale is invalid."""
    if any(type(config[name]) is not int for name in ('schema_version', 'spacing_m', 'patch_size_m')):
        raise ValueError('Schema version, grid spacing, and patch size must be integers')
    if config['schema_version'] != 1 or config['spacing_m'] != 30 or config['patch_size_m'] not in {300, 600, 960}:
        raise ValueError('Unsupported schema, spacing, or patch size')
    if (type(config['context_m']) not in {int, float} or not np.isfinite(config['context_m'])
            or config['context_m'] < 150):
        raise ValueError('At least 150 m feature context is required')
    if type(config['top_k']) is not int or config['top_k'] < 1:
        raise ValueError('top_k must be a positive integer')
    seen: set[tuple[str, str]] = set()
    for item in config['regions']:
        key = (item['body'], item['region'])
        if key in seen or item['region'] not in DEVELOPMENT.get(item['body'], set()):
            raise ValueError(f'Duplicate or unapproved development region: {key}')
        seen.add(key)
        if item['role'] != 'development' or item['fold'] not in {'train', 'holdout'}:
            raise ValueError('This builder opens development train/holdout regions only')
        if item['run'] not in config['runs']:
            raise ValueError('Unknown source run')
    for body in ('earth', 'moon'):
        if {item['fold'] for item in config['regions'] if item['body'] == body} != {'train', 'holdout'}:
            raise ValueError('Both bodies need training and development holdout regions')


def read_layer(path: Path, expected: dict[str, str], evidence: dict[str, str]) -> tuple[np.ndarray, tuple[Any, ...]]:
    with rasterio.open(check_input(path, expected, evidence)) as source:
        transform = source.transform
        if (source.count != 1 or source.crs is None or not source.crs.is_projected
                or source.crs.linear_units != 'metre' or source.scales != (1.,) or source.offsets != (0.,)
                or (transform.a, transform.e, transform.b, transform.d) != (30., -30., 0., 0.)):
            raise ValueError(f'Expected unscaled, north-up 30 m projected raster: {path}')
        values = source.read(1, masked=True).astype('float32').filled(np.nan)
        if np.isinf(values).any():
            raise ValueError(f'Infinite source values: {path}')
        return values, (source.shape, transform, source.crs)


def collect_sources(root: Path, config: dict[str, Any], run: Run) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Verify manifests and context separation before extracting any tensors."""
    sources: list[dict[str, Any]] = []
    footprints: list[SplitFootprint] = []
    expected: dict[str, str] = {}
    for run_name in sorted({item['run'] for item in config['regions']}):
        relative = config['runs'][run_name]
        folder = (root / relative).resolve()
        if not folder.is_relative_to((root / 'data/processed').resolve()):
            raise ValueError('Inputs must be accepted processed runs')
        expected.update(verify_run(folder))
        run.input(folder / 'provenance.json')
    for item in config['regions']:
        folder = root / config['runs'][item['run']] / item['body'] / item['region']
        views = ['natural_screen'] if item['body'] == 'earth' else ['full_context', 'image_supported']
        for view in views:
            layers = folder / ('grid_30m' if item['body'] == 'earth' else view)
            mask = (layers / 'natural_screen_mask.tif' if item['body'] == 'earth'
                    else folder / 'quality' / f'{view}_complete_feature_mask.tif')
            # Read only metadata here; content hashes are checked during extraction.
            with rasterio.open(layers / 'elevation_m.tif') as raster:
                if raster.crs is None or not raster.crs.is_projected or raster.crs.linear_units != 'metre':
                    raise ValueError('Context buffer requires a projected metric CRS')
                left, bottom, right, top = raster.bounds
                halo = config['context_m']
                context = (left - halo, bottom - halo, right + halo, top + halo)
                common_crs = 'EPSG:6933' if item['body'] == 'earth' else MOON_CRS
                bounds = transform_bounds(raster.crs, common_crs, *context, densify_pts=101)
                footprints.append(SplitFootprint(item['body'], item['region'], item['fold'], bounds))
            sources.append({**item, 'view': view, 'folder': layers, 'mask': mask})
    validate_split_footprints(footprints)
    run.path('split_footprints.json').write_text(json.dumps({
        'policy': 'Whole source bounds plus context on every side; touching cross-role bounds fail',
        'common_crs': {'earth': 'EPSG:6933', 'moon': MOON_CRS},
        'footprints': [asdict(item) for item in footprints],
        'status': 'no cross-role context overlap',
    }, indent=2), encoding='utf-8')
    return sources, expected


def extract_source(source: dict[str, Any], config: dict[str, Any], expected: dict[str, str],
                   evidence: dict[str, str], run: Run) -> tuple[list[dict[str, Any]], np.ndarray, dict[str, Any]]:
    """Keep complete patches under existing masks; count all excluded lattice windows."""
    mask, grid = read_layer(source['mask'], expected, evidence)
    layers: dict[str, np.ndarray] = {}
    for name in SOURCE_CHANNELS:
        values, current_grid = read_layer(source['folder'] / f'{name}.tif', expected, evidence)
        if current_grid != grid:
            raise ValueError('Source channels and policy mask are not aligned')
        layers[name] = values
    shape, transform, crs = grid
    side = config['patch_size_m'] // config['spacing_m']
    complete = np.logical_and.reduce([np.isfinite(values) for values in layers.values()])
    selected = (mask == 1) & complete
    records: list[dict[str, Any]] = []
    tensors: list[np.ndarray] = []
    audit = {name: source[name] for name in ('body', 'region', 'view', 'fold')}
    audit.update({'lattice_windows': 0, 'incomplete_terrain': 0, 'policy_rejected': 0, 'eligible': 0})
    shard = f"tensors/{source['region']}__{source['view']}.npz"
    # Match notebook 16's common center lattice even for the smaller scale follow-ups.
    for center_row in range(16, shape[0] - 15, 32):
        for center_col in range(16, shape[1] - 15, 32):
            audit['lattice_windows'] += 1
            row, col = center_row - side // 2, center_col - side // 2
            window = np.s_[row:row + side, col:col + side]
            if not complete[window].all():
                audit['incomplete_terrain'] += 1
            if not (mask[window] == 1).all():
                audit['policy_rejected'] += 1
            if not selected[window].all():
                continue
            elevation, slope, sd = [layers[name][window] for name in SOURCE_CHANNELS[:3]]
            left, top = transform * (col, row)
            right, bottom = transform * (col + side, row + side)
            records.append({
                'patch_id': f"{source['region']}:{source['view']}:{center_row}:{center_col}:{config['patch_size_m']}",
                'location_id': f"{source['region']}:{center_row}:{center_col}",
                **{name: source[name] for name in ('body', 'region', 'view', 'role', 'fold', 'run')},
                'size_m': config['patch_size_m'], 'spacing_m': 30, 'context_m': config['context_m'],
                'row': row, 'col': col, 'left': left, 'bottom': bottom, 'right': right, 'top': top,
                'crs_wkt': crs.to_wkt(), 'shard': shard, 'tensor_index': len(tensors),
                **measure_patch(elevation, slope, sd), **measure_planarity(elevation),
            })
            tensors.append(prepare_patch(elevation, slope, sd))
    array = np.stack(tensors) if tensors else np.empty((0, 3, side, side), dtype=np.float32)
    np.savez_compressed(run.path(shard), physical=array, valid=np.isfinite(array))
    audit['eligible'] = len(records)
    audit['edge_remainder_cells'] = shape[0] * shape[1] - (shape[0] // 32 * 32) * (shape[1] // 32 * 32)
    return records, array, audit


def save_scalers(patches: pd.DataFrame, tensors: np.ndarray, run: Run) -> None:
    """Keep each lunar view a separate experiment; never count it twice in fitting."""
    for view in ('full_context', 'image_supported'):
        selected = ((patches['body'] == 'earth') | (patches['view'] == view)).to_numpy(dtype=bool)
        frame = patches.loc[selected].copy()
        mean, scale = fit_scaler(tensors[selected], frame['fold'].tolist(), frame['region'].tolist())
        frame['sampling_weight'] = 0.
        training = frame['fold'] == 'train'
        counts = frame.loc[training, 'region'].value_counts()
        frame.loc[training, 'sampling_weight'] = frame.loc[training, 'region'].map(1. / (len(counts) * counts))
        frame[['patch_id', 'sampling_weight']].to_csv(run.path(f'sampling_{view}.csv'), index=False)
        run.path(f'scaler_{view}.json').write_text(json.dumps({
            'channels': CHANNELS, 'mean': mean.tolist(), 'scale': scale.tolist(),
            'fit_role': 'development train only', 'weighting': 'equal region, equal patch within region',
            'training_regions': counts.index.tolist(), 'training_patch_count': int(training.sum()),
            'missingness': 'Initial eligibility requires complete channels; future masked transforms return validity separately',
        }, indent=2), encoding='utf-8')


def baseline_retrieval(patches: pd.DataFrame, k: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate held-out lunar queries, Earth candidates, and both-held-out cases."""
    rows: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    cases = [('heldout_queries', 'holdout', 'train'), ('heldout_candidates', 'train', 'holdout'),
             ('both_heldout', 'holdout', 'holdout')]
    for case, query_role, candidate_role in cases:
        pool = patches.loc[(patches['body'] == 'earth') & (patches['fold'] == candidate_role)].reset_index(drop=True)
        descriptors = pool[FEATURES].to_numpy(dtype=float)
        ids = pool['patch_id'].tolist()
        queries = patches.loc[(patches['body'] == 'moon') & (patches['fold'] == query_role)]
        for query in queries.to_dict('records'):
            order, scores = rank_candidates(np.array([query[name] for name in FEATURES]), descriptors, ids, k)
            coverage.append({'case': case, 'query_id': query['patch_id'], 'region': query['region'],
                             'view': query['view'], 'candidate_count': len(pool), 'returned': len(order),
                             'top_k_regions': len(set(pool.iloc[order]['region'])),
                             'best_band_discrepancy': float(scores[0]) if len(scores) else None})
            for rank, (index, score) in enumerate(zip(order, scores, strict=True), start=1):
                candidate = pool.iloc[int(index)]
                rows.append({'case': case, 'query_id': query['patch_id'], 'query_region': query['region'],
                             'view': query['view'], 'candidate_id': candidate['patch_id'],
                             'candidate_region': candidate['region'], 'rank': rank,
                             'band_discrepancy': float(score),
                             **{f'delta_{name}': float(candidate[name] - query[name]) for name in FEATURES}})
    return pd.DataFrame(rows), pd.DataFrame(coverage)


def review_pairs(patches: pd.DataFrame, rankings: pd.DataFrame) -> pd.DataFrame:
    """Seed a small unlabeled review pool with top and randomly selected candidates."""
    rng = np.random.default_rng(28)
    rows: list[dict[str, Any]] = []
    for _, group in patches.loc[patches['body'] == 'moon'].groupby(['region', 'view'], sort=True):
        ordered = group.sort_values('patch_id')
        query_ids = rng.choice(ordered['patch_id'].to_numpy(), size=min(2, len(ordered)), replace=False)
        for query_id in query_ids:
            ranked = rankings.loc[rankings['query_id'] == query_id]
            for case, part in ranked.groupby('case', sort=True):
                candidate_role = 'train' if case == 'heldout_queries' else 'holdout'
                pool = patches.loc[(patches['body'] == 'earth') & (patches['fold'] == candidate_role), 'patch_id']
                selected = list(part.sort_values('rank')['candidate_id'].head(3))
                other = sorted(set(pool) - set(selected))
                selected.extend(rng.choice(other, size=min(2, len(other)), replace=False).tolist())
                rng.shuffle(selected)
                for candidate_id in selected:
                    rows.append({'case': case, 'query_id': query_id, 'candidate_id': candidate_id,
                                 'relevance': '', 'reviewer': '', 'reason': ''})
    return pd.DataFrame(rows)


def build_dataset(root: Path, config_path: Path) -> Path:
    root = root.resolve()
    config = json.loads(config_path.read_text(encoding='utf-8'))
    validate_config(config)
    with Run(root, 'terrain_learning_readiness', config,
             'modeling/terrain_similarity/28_training_data_readiness_and_baseline.ipynb') as run:
        for path in [config_path, Path(__file__), *(root / 'notebooks' / name for name in
                     ['terrain_learning.py', 'inspection.py', 'patch_analysis.py', 'retrieval_analysis.py'])]:
            run.input(path)
        revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, check=False)
        run.record['git_revision'] = revision.stdout.strip() or 'unavailable'
        run.record['code_state'] = 'Input hashes identify working files, including uncommitted edits'
        sources, expected = collect_sources(root, config, run)
        records, arrays, audits = [], [], []
        evidence: dict[str, str] = {}
        for source in sources:
            rows, array, audit = extract_source(source, config, expected, evidence, run)
            records.extend(rows)
            arrays.append(array)
            audits.append(audit)
            print(source['region'], source['view'], len(rows), 'eligible patches', flush=True)
        patches = pd.DataFrame(records)
        if patches.empty or patches['patch_id'].duplicated().any():
            raise ValueError('Empty dataset or duplicate patch IDs')
        tensors = np.concatenate(arrays)
        patches.to_csv(run.path('patches.csv'), index=False)
        pd.DataFrame(audits).to_csv(run.path('inventory.csv'), index=False)
        save_scalers(patches, tensors, run)
        rankings, coverage = baseline_retrieval(patches, config['top_k'])
        rankings.to_csv(run.path('baseline_top_k.csv'), index=False)
        coverage.to_csv(run.path('query_inventory.csv'), index=False)
        review_pairs(patches, rankings).to_csv(run.path('review_pairs_unlabeled.csv'), index=False)
        regional = coverage.groupby(['case', 'view', 'region']).agg(
            queries=('query_id', 'size'), mean_top_k_regions=('top_k_regions', 'mean'),
            median_best_discrepancy=('best_band_discrepancy', 'median')).reset_index()
        regional.to_csv(run.path('baseline_by_region.csv'), index=False)
        regional.groupby(['case', 'view'])[['mean_top_k_regions', 'median_best_discrepancy']].mean().to_csv(
            run.path('baseline_region_macro.csv'))
        for path, digest in evidence.items():
            run.input(Path(path))
            if run.record['inputs'][str(Path(path).relative_to(root))]['sha256'] != digest:
                raise ValueError('Source changed during extraction')
        run.record['readiness'] = {
            'patches': len(patches), 'trained_model': False, 'independent_labels': False,
            'reserves_opened': False, 'tensor_layout': 'NCHW; three float32 physical channels plus boolean validity',
            'scope': 'EDA-exposed development fold; rankings are discrepancies, not relevance or mobility labels',
            'next': 'Review relevance rubric/pairs before comparing a CNN with the physical baseline',
        }
    return run.directory


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    print(build_dataset(args.root, args.config or args.root / 'notebooks/modeling/terrain_similarity/terrain_dataset.json'))
