"""Cut lunar terrain into 960 m patches and run the Earth-trained model.

This is inference only. Lunar patches have no class ground truth, so this stage
does not calculate accuracy and must not be used to claim measured rover safety.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio
import torch
from affine import Affine
from rasterio.crs import CRS
from torch.utils.data import DataLoader, TensorDataset

from notebooks.shared.inspection import check_input, verify_run
from notebooks.shared.processing import Run
from operational_cnn.data.build_operability_eda import CHANNELS
from operational_cnn.labels.route_labels import DIRECTIONS, local_elevation_std
from operational_cnn.model.operability_cnn import TerrainOperabilityCNN


Grid = tuple[tuple[int, int], Affine, CRS]


def validate_config(config: dict[str, Any]) -> None:
    if config.get('schema_version') != 1:
        raise ValueError('Unsupported lunar inference config schema')
    if config.get('view') != 'full_context':
        raise ValueError('Only the corrected full_context lunar view is supported')
    if config.get('patch_size_m') != 960 or config.get('spacing_m') != 30:
        raise ValueError('The Earth-trained model requires 960 m patches on a 30 m grid')
    for name in ('center_stride_cells', 'batch_size'):
        if type(config.get(name)) is not int or config[name] < 1:
            raise ValueError(f'{name} must be a positive integer')
    threshold = config.get('direction_probability_threshold')
    if not isinstance(threshold, (int, float)) or not np.isfinite(threshold) or not 0 < threshold < 1:
        raise ValueError('direction_probability_threshold must be between zero and one')
    for name in ('lunar_views_run', 'model_run', 'claim_boundary'):
        if not isinstance(config.get(name), str) or not config[name]:
            raise ValueError(f'Missing {name}')


def read_registered_raster(path: Path, expected: dict[str, str], evidence: dict[str, str],
                           run: Run) -> tuple[np.ndarray, Grid]:
    check_input(path, expected, evidence)
    run.input(path)
    with rasterio.open(path) as source:
        if source.count != 1 or source.crs is None or not source.crs.is_projected:
            raise ValueError(f'Expected one projected raster band: {path}')
        values = source.read(1)
        grid = (values.shape, source.transform, source.crs)
    return values, grid


def extract_patches(layers: dict[str, np.ndarray], complete_mask: np.ndarray, *, region: str,
                    transform: Affine, crs: CRS, side: int = 32,
                    stride: int = 32) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """Return complete model-ready physical tensors and their map locations."""
    required = ('elevation_m', 'slope_deg', 'roughness_90m', 'roughness_330m', 'laplacian_per_m')
    if not region or side < 1 or stride < 1 or complete_mask.ndim != 2:
        raise ValueError('Invalid lunar patch extraction inputs')
    shape = complete_mask.shape
    if any(name not in layers or layers[name].shape != shape for name in required):
        raise ValueError('Lunar layers are missing or misaligned')
    eligible = complete_mask.astype(bool, copy=True)
    for name in required:
        eligible &= np.isfinite(layers[name])

    tensors: list[np.ndarray] = []
    records: list[dict[str, Any]] = []
    height, width = shape
    for row in range(0, height - side + 1, stride):
        for col in range(0, width - side + 1, stride):
            window = np.s_[row:row + side, col:col + side]
            if not eligible[window].all():
                continue
            elevation = layers['elevation_m'][window]
            tensor = np.stack((
                elevation - elevation.mean(),
                layers['slope_deg'][window],
                layers['roughness_90m'][window],
                layers['roughness_330m'][window],
                layers['laplacian_per_m'][window],
            )).astype(np.float32)
            index = len(tensors)
            tensors.append(tensor)
            center_row, center_col = row + side / 2, col + side / 2
            center_x, center_y = transform @ (center_col, center_row)
            records.append({
                'patch_id': f'{region}:960:{row}:{col}',
                'region': region,
                'size_m': 960,
                'spacing_m': 30,
                'top_row': row,
                'top_col': col,
                'center_row': center_row,
                'center_col': center_col,
                'center_x': center_x,
                'center_y': center_y,
                'crs_wkt': crs.to_wkt(),
                'tensor_shard': f'tensors/{region}_960m.npz',
                'tensor_index': index,
                'slope_median_deg': float(np.median(tensor[1])),
                'slope_p90_deg': float(np.percentile(tensor[1], 90)),
                'relative_relief_m': float(np.max(tensor[0]) - np.min(tensor[0])),
            })
    values = (np.stack(tensors) if tensors else
              np.empty((0, len(CHANNELS), side, side), dtype=np.float32))
    return values, records


def load_region(lunar_run: Path, region: str, view: str, expected: dict[str, str],
                evidence: dict[str, str], run: Run) -> tuple[dict[str, np.ndarray], np.ndarray, Grid]:
    folder = lunar_run / 'moon' / region
    source_names = ('elevation_m', 'slope_deg', 'local_elevation_std_m', 'laplacian_per_m')
    loaded: dict[str, np.ndarray] = {}
    reference: Grid | None = None
    for name in source_names:
        values, grid = read_registered_raster(folder / view / f'{name}.tif', expected, evidence, run)
        if reference is not None and grid != reference:
            raise ValueError(f'Misaligned lunar layer in {region}: {name}')
        reference = grid
        loaded[name] = values
    mask, mask_grid = read_registered_raster(
        folder / 'quality' / 'full_context_complete_feature_mask.tif', expected, evidence, run)
    if reference is None or mask_grid != reference:
        raise ValueError(f'Misaligned lunar completeness mask in {region}')
    shape, transform, _ = reference
    if (not np.isclose(transform.a, 30) or not np.isclose(transform.e, -30)
            or transform.b != 0 or transform.d != 0):
        raise ValueError(f'Lunar grid is not north-up at 30 m in {region}')
    layers = {
        'elevation_m': loaded['elevation_m'],
        'slope_deg': loaded['slope_deg'],
        'roughness_90m': local_elevation_std(loaded['elevation_m'], 3),
        'roughness_330m': loaded['local_elevation_std_m'],
        'laplacian_per_m': loaded['laplacian_per_m'],
    }
    if mask.shape != shape:
        raise ValueError(f'Unexpected mask shape in {region}')
    return layers, np.asarray(mask == 1), reference


def load_model(model_run: Path, expected: dict[str, str], evidence: dict[str, str],
               run: Run) -> tuple[TerrainOperabilityCNN, tuple[str, ...], np.ndarray, np.ndarray]:
    checkpoint_path, scaler_path = model_run / 'model.pt', model_run / 'scaler.json'
    for path in (checkpoint_path, scaler_path):
        check_input(path, expected, evidence)
        run.input(path)
    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=True)
    classes = tuple(checkpoint['classes'])
    if checkpoint.get('channels') != len(CHANNELS) or tuple(checkpoint['directions']) != DIRECTIONS:
        raise ValueError('Checkpoint channels or directions do not match lunar inference')
    if len(classes) != 3:
        raise ValueError('Expected a three-class operability checkpoint')
    scaler = json.loads(scaler_path.read_text(encoding='utf-8'))
    mean = np.asarray(scaler['mean'], dtype=np.float32)
    scale = np.asarray(scaler['scale'], dtype=np.float32)
    if mean.shape != (len(CHANNELS),) or scale.shape != mean.shape or not np.isfinite(mean).all() \
            or not np.isfinite(scale).all() or not (scale > 0).all():
        raise ValueError('Invalid Earth training scaler')
    model = TerrainOperabilityCNN()
    model.load_state_dict(checkpoint['state_dict'])
    model.eval()
    return model, classes, mean, scale


def predict(model: TerrainOperabilityCNN, physical: np.ndarray, mean: np.ndarray,
            scale: np.ndarray, batch_size: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if physical.ndim != 4 or tuple(physical.shape[1:]) != (5, 32, 32):
        raise ValueError('Expected lunar tensors with shape (N, 5, 32, 32)')
    normalized = ((physical - mean[None, :, None, None]) /
                  scale[None, :, None, None]).astype(np.float32)
    if not np.isfinite(normalized).all():
        raise ValueError('Normalized lunar tensors must be finite')
    if len(normalized) == 0:
        return (np.empty((0, 3), dtype=np.float32), np.empty((0, 4), dtype=np.float32), normalized)
    loader = DataLoader(TensorDataset(torch.from_numpy(normalized)), batch_size=batch_size,
                        shuffle=False, num_workers=0)
    class_parts, direction_parts = [], []
    with torch.no_grad():
        for (batch,) in loader:
            class_logits, direction_logits = model(batch)
            class_parts.append(torch.softmax(class_logits, dim=1).numpy())
            direction_parts.append(torch.sigmoid(direction_logits).numpy())
    return np.concatenate(class_parts), np.concatenate(direction_parts), normalized


def infer(root: Path, config_path: Path) -> Path:
    root, config_path = root.resolve(), config_path.resolve()
    config = json.loads(config_path.read_text(encoding='utf-8'))
    validate_config(config)
    lunar_run = (root / config['lunar_views_run']).resolve()
    model_run = (root / config['model_run']).resolve()
    lunar_expected, model_expected = verify_run(lunar_run), verify_run(model_run)
    regions = sorted(path.name for path in (lunar_run / 'moon').iterdir() if path.is_dir())
    if len(regions) != 7:
        raise ValueError(f'Expected seven lunar development regions, found {len(regions)}')
    notebook = '../operational_cnn/inference/run_lunar_inference.py'
    with Run(root, 'terrain_operability_lunar_inference', config, notebook) as run:
        for path in (config_path, lunar_run / 'provenance.json', model_run / 'provenance.json',
                     root / 'operational_cnn/model/operability_cnn.py',
                     root / 'operational_cnn/labels/route_labels.py'):
            run.input(path)
        evidence: dict[str, str] = {}
        model, classes, mean, scale = load_model(model_run, model_expected, evidence, run)
        all_records: list[dict[str, Any]] = []
        shift_rows: list[dict[str, Any]] = []
        threshold = float(config['direction_probability_threshold'])
        for region in regions:
            layers, complete, (_, transform, crs) = load_region(
                lunar_run, region, config['view'], lunar_expected, evidence, run)
            physical, records = extract_patches(
                layers, complete, region=region, transform=transform, crs=crs,
                side=config['patch_size_m'] // config['spacing_m'],
                stride=config['center_stride_cells'])
            np.savez_compressed(run.path(f'tensors/{region}_960m.npz'), physical=physical,
                                channels=np.asarray(CHANNELS))
            class_probabilities, direction_probabilities, normalized = predict(
                model, physical, mean, scale, config['batch_size'])
            for index, record in enumerate(records):
                predicted_index = int(np.argmax(class_probabilities[index]))
                record['predicted_class'] = classes[predicted_index]
                record['predicted_class_probability'] = float(class_probabilities[index, predicted_index])
                for class_index, name in enumerate(classes):
                    record[f'probability_{name}'] = float(class_probabilities[index, class_index])
                for direction_index, name in enumerate(DIRECTIONS):
                    probability = float(direction_probabilities[index, direction_index])
                    record[f'probability_{name}'] = probability
                    record[f'predicted_{name}'] = probability >= threshold
            all_records.extend(records)
            for channel_index, channel in enumerate(CHANNELS):
                channel_values = normalized[:, channel_index]
                shift_rows.append({
                    'region': region,
                    'channel': channel,
                    'patches': len(physical),
                    'normalized_mean': float(channel_values.mean()) if len(physical) else np.nan,
                    'normalized_std': float(channel_values.std()) if len(physical) else np.nan,
                    'fraction_abs_z_above_5': float((np.abs(channel_values) > 5).mean()) if len(physical) else np.nan,
                })
            print(region, len(records), 'complete lunar patches', flush=True)
        predictions = pd.DataFrame(all_records)
        if predictions.empty or predictions['patch_id'].duplicated().any():
            raise ValueError('No lunar patches or duplicate patch IDs')
        predictions.to_csv(run.path('predictions.csv'), index=False)
        pd.DataFrame(shift_rows).to_csv(run.path('normalized_channel_summary.csv'), index=False)
        summary = (predictions.groupby(['region', 'predicted_class'], observed=True).size()
                   .rename('patches').reset_index())
        summary['fraction_within_region'] = summary['patches'] / summary.groupby('region')['patches'].transform('sum')
        summary.to_csv(run.path('prediction_summary.csv'), index=False)
        run.path('README.md').write_text(
            '# Lunar terrain operability inference\n\n'
            'These are Earth-trained predictions on unlabeled lunar terrain. No lunar accuracy was '
            'calculated. Probabilities are model outputs, not calibrated safety ratings. Missing or '
            'incomplete terrain windows were excluded rather than treated as suitable.\n', encoding='utf-8')
        run.record['result'] = {
            'patches': int(len(predictions)),
            'regions': regions,
            'classes': classes,
            'channels': CHANNELS,
            'verified_source_outputs': len(evidence),
            'lunar_ground_truth': False,
            'claim_boundary': config['claim_boundary'],
        }
    return run.directory


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--config', type=Path)
    arguments = parser.parse_args()
    default = arguments.root / 'operational_cnn/configs/lunar_inference.json'
    print(infer(arguments.root, arguments.config or default))
