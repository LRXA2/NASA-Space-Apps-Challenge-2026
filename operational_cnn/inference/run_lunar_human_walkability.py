"""Apply the Earth-trained three-head mobility model to lunar terrain patches."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, TensorDataset

from notebooks.shared.inspection import check_input, verify_run
from notebooks.shared.processing import Run
from operational_cnn.data.build_operability_eda import CHANNELS
from operational_cnn.inference.run_lunar_inference import extract_patches, load_region
from operational_cnn.labels.human_walkability import HUMAN_TERRAIN_CLASSES, human_terrain_class
from operational_cnn.labels.route_labels import DIRECTIONS, directional_connectivity
from operational_cnn.model.terrain_mobility_cnn import TerrainMobilityCNN
from operational_cnn.training.train_operability import CLASS_NAMES


def validate_config(config: dict[str, Any]) -> None:
    if (config.get('schema_version') != 1 or config.get('view') != 'full_context'
            or config.get('patch_size_m') != 960 or config.get('spacing_m') != 30):
        raise ValueError('Expected schema 1, full_context, 960 m patches and 30 m spacing')
    for name in ('center_stride_cells', 'batch_size'):
        if type(config.get(name)) is not int or config[name] < 1:
            raise ValueError(f'{name} must be a positive integer')
    threshold = config.get('direction_probability_threshold')
    if not isinstance(threshold, (int, float)) or not np.isfinite(threshold) or not 0 < threshold < 1:
        raise ValueError('direction_probability_threshold must be between zero and one')
    for name in ('lunar_views_run', 'model_run', 'claim_boundary'):
        if not isinstance(config.get(name), str) or not config[name]:
            raise ValueError(f'Missing {name}')


def load_model(model_run: Path, expected: dict[str, str], evidence: dict[str, str],
               run: Run) -> tuple[TerrainMobilityCNN, np.ndarray, np.ndarray, dict[str, Any]]:
    checkpoint_path, scaler_path = model_run / 'model.pt', model_run / 'scaler.json'
    for path in (checkpoint_path, scaler_path):
        check_input(path, expected, evidence)
        run.input(path)
    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=True)
    if (checkpoint.get('channels') != len(CHANNELS)
            or tuple(checkpoint.get('rover_classes', ())) != CLASS_NAMES
            or tuple(checkpoint.get('human_terrain_classes', ())) != HUMAN_TERRAIN_CLASSES
            or tuple(checkpoint.get('directions', ())) != DIRECTIONS):
        raise ValueError('Three-head checkpoint metadata does not match inference code')
    scaler = json.loads(scaler_path.read_text(encoding='utf-8'))
    mean = np.asarray(scaler['mean'], dtype=np.float32)
    scale = np.asarray(scaler['scale'], dtype=np.float32)
    if (mean.shape != (5,) or scale.shape != (5,) or not np.isfinite(mean).all()
            or not np.isfinite(scale).all() or not (scale > 0).all()):
        raise ValueError('Invalid Earth training scaler')
    model = TerrainMobilityCNN()
    model.load_state_dict(checkpoint['state_dict'])
    model.eval()
    human_rule = checkpoint.get('human_rule')
    if not isinstance(human_rule, dict):
        raise ValueError('Checkpoint lacks the human terrain rule')
    return model, mean, scale, human_rule


def predict(model: TerrainMobilityCNN, physical: np.ndarray, mean: np.ndarray,
            scale: np.ndarray, batch_size: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if physical.ndim != 4 or tuple(physical.shape[1:]) != (5, 32, 32):
        raise ValueError('Expected lunar tensors with shape (N, 5, 32, 32)')
    normalized = ((physical - mean[None, :, None, None]) /
                  scale[None, :, None, None]).astype(np.float32)
    if not np.isfinite(normalized).all():
        raise ValueError('Normalized lunar tensors must be finite')
    if len(normalized) == 0:
        return (np.empty((0, 3), dtype=np.float32), np.empty((0, 4), dtype=np.float32),
                np.empty((0, 3), dtype=np.float32), normalized)
    loader = DataLoader(TensorDataset(torch.from_numpy(normalized)), batch_size=batch_size,
                        shuffle=False, num_workers=0)
    rover_parts, direction_parts, human_parts = [], [], []
    with torch.no_grad():
        for (batch,) in loader:
            rover_logits, direction_logits, human_logits = model(batch)
            rover_parts.append(torch.softmax(rover_logits, dim=1).numpy())
            direction_parts.append(torch.sigmoid(direction_logits).numpy())
            human_parts.append(torch.softmax(human_logits, dim=1).numpy())
    return (np.concatenate(rover_parts), np.concatenate(direction_parts),
            np.concatenate(human_parts), normalized)


def add_predictions(records: list[dict[str, Any]], rover: np.ndarray, directions: np.ndarray,
                    human: np.ndarray, threshold: float) -> None:
    if not (len(records) == len(rover) == len(directions) == len(human)):
        raise ValueError('Prediction and patch counts differ')
    for index, record in enumerate(records):
        rover_index = int(np.argmax(rover[index]))
        human_index = int(np.argmax(human[index]))
        record['predicted_rover_class'] = CLASS_NAMES[rover_index]
        record['predicted_rover_probability'] = float(rover[index, rover_index])
        record['predicted_human_terrain_class'] = HUMAN_TERRAIN_CLASSES[human_index]
        record['predicted_human_terrain_probability'] = float(human[index, human_index])
        for class_index, name in enumerate(CLASS_NAMES):
            record[f'rover_probability_{name}'] = float(rover[index, class_index])
        for class_index, name in enumerate(HUMAN_TERRAIN_CLASSES):
            record[f'human_probability_{name}'] = float(human[index, class_index])
        for direction_index, name in enumerate(DIRECTIONS):
            probability = float(directions[index, direction_index])
            record[f'probability_{name}'] = probability
            record[f'predicted_{name}'] = probability >= threshold


def add_direct_rule_evidence(records: list[dict[str, Any]], physical: np.ndarray,
                             rule: dict[str, Any]) -> None:
    """Apply the declared rule directly as a cross-domain sanity check, not truth."""
    if len(records) != len(physical):
        raise ValueError('Physical tensor and record counts differ')
    conservative_limit = float(rule['easy_max_p90_slope_deg'])
    permissive_limit = float(rule['caution_max_p90_slope_deg'])
    for index, record in enumerate(records):
        slope = physical[index, 1]
        conservative = directional_connectivity(slope, conservative_limit)
        permissive = directional_connectivity(slope, permissive_limit)
        direct = human_terrain_class(
            conservative_crossings=conservative.crossing_count,
            conservative_largest_component_fraction=conservative.largest_component_fraction,
            permissive_crossings=permissive.crossing_count,
            permissive_largest_component_fraction=permissive.largest_component_fraction,
            slope_p90_deg=float(np.percentile(slope, 90)), **rule)
        record['direct_human_terrain_rule'] = direct
        record['cnn_agrees_with_direct_human_rule'] = (
            record['predicted_human_terrain_class'] == direct)
        record['direct_conservative_crossing_count'] = conservative.crossing_count
        record['direct_permissive_crossing_count'] = permissive.crossing_count
        record['direct_conservative_largest_component_fraction'] = (
            conservative.largest_component_fraction)
        record['direct_permissive_largest_component_fraction'] = (
            permissive.largest_component_fraction)


def class_summary(predictions: pd.DataFrame, column: str) -> pd.DataFrame:
    summary = (predictions.groupby(['region', column], observed=True).size()
               .rename('patches').reset_index())
    summary['fraction_within_region'] = (
        summary['patches'] / summary.groupby('region')['patches'].transform('sum'))
    return summary


def infer(root: Path, config_path: Path) -> Path:
    root, config_path = root.resolve(), config_path.resolve()
    config = json.loads(config_path.read_text(encoding='utf-8'))
    validate_config(config)
    lunar_run = (root / config['lunar_views_run']).resolve()
    model_run = (root / config['model_run']).resolve()
    lunar_expected, model_expected = verify_run(lunar_run), verify_run(model_run)
    regions = sorted(path.name for path in (lunar_run / 'moon').iterdir() if path.is_dir())
    if len(regions) != 7:
        raise ValueError(f'Expected seven lunar regions, found {len(regions)}')
    notebook = '../operational_cnn/inference/run_lunar_human_walkability.py'
    with Run(root, 'terrain_human_walkability_lunar_inference', config, notebook) as run:
        for path in (
                config_path, lunar_run / 'provenance.json', model_run / 'provenance.json',
                root / 'operational_cnn/model/terrain_mobility_cnn.py',
                root / 'operational_cnn/labels/human_walkability.py'):
            run.input(path)
        evidence: dict[str, str] = {}
        model, mean, scale, human_rule = load_model(model_run, model_expected, evidence, run)
        all_records: list[dict[str, Any]] = []
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
            rover, directions, human, _ = predict(
                model, physical, mean, scale, config['batch_size'])
            add_predictions(records, rover, directions, human, threshold)
            add_direct_rule_evidence(records, physical, human_rule)
            all_records.extend(records)
            print(region, len(records), 'complete lunar patches', flush=True)
        predictions = pd.DataFrame(all_records)
        if predictions.empty or predictions['patch_id'].duplicated().any():
            raise ValueError('No lunar predictions or duplicate patch IDs')
        predictions.to_csv(run.path('predictions.csv'), index=False)
        class_summary(predictions, 'predicted_rover_class').to_csv(
            run.path('rover_prediction_summary.csv'), index=False)
        class_summary(predictions, 'predicted_human_terrain_class').to_csv(
            run.path('human_prediction_summary.csv'), index=False)
        class_summary(predictions, 'direct_human_terrain_rule').to_csv(
            run.path('direct_rule_summary.csv'), index=False)
        agreement_by_region = (predictions.groupby('region')['cnn_agrees_with_direct_human_rule']
                               .agg(['size', 'mean']).reset_index()
                               .rename(columns={'size': 'patches', 'mean': 'agreement_fraction'}))
        agreement_by_region.to_csv(run.path('cnn_direct_rule_agreement_by_region.csv'), index=False)
        pd.crosstab(predictions['direct_human_terrain_rule'],
                    predictions['predicted_human_terrain_class']).to_csv(
                        run.path('cnn_direct_rule_confusion.csv'))
        overall_agreement = float(predictions['cnn_agrees_with_direct_human_rule'].mean())
        run.path('README.md').write_text(
            '# Lunar human-terrain inference\n\n'
            'The human-terrain output is an Earth-trained 30 m terrain proxy. It has no lunar '
            'ground truth and does not include foot-scale hazards, spacesuit performance, lighting, '
            'regolith mechanics, fatigue, gravity adaptation, or human safety. The direct-rule '
            'comparison is a cross-domain consistency check, not lunar ground truth.\n', encoding='utf-8')
        run.record['result'] = {
            'patches': int(len(predictions)), 'regions': regions,
            'rover_classes': CLASS_NAMES, 'human_terrain_classes': HUMAN_TERRAIN_CLASSES,
            'verified_source_outputs': len(evidence), 'lunar_ground_truth': False,
            'cnn_direct_rule_agreement': overall_agreement,
            'claim_boundary': config['claim_boundary'],
        }
    return run.directory


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--config', type=Path)
    arguments = parser.parse_args()
    default = arguments.root / 'operational_cnn/configs/lunar_human_walkability_inference.json'
    print(infer(arguments.root, arguments.config or default))
