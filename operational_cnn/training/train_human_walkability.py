"""Train a terrain-only human walkability head alongside the rover tasks."""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from notebooks.shared.inspection import verify_run
from notebooks.shared.processing import Run
from operational_cnn.labels.human_walkability import HUMAN_TERRAIN_CLASSES, human_terrain_class
from operational_cnn.labels.route_labels import DIRECTIONS
from operational_cnn.model.terrain_mobility_cnn import TerrainMobilityCNN
from operational_cnn.training.train_operability import (
    CLASS_NAMES, assign_splits, confusion, fit_scaler, load_tensors,
)


def validate_config(config: dict[str, Any]) -> None:
    if config.get('schema_version') != 1 or config.get('patch_size_m') != 960:
        raise ValueError('Only the 960 m terrain-mobility experiment is supported')
    if config.get('test_region') not in {
            'northern_arizona', 'lanzarote', 'atacama_san_pedro', 'death_valley', 'wadi_rum'}:
        raise ValueError('Unknown test region')
    if not 0 < config.get('validation_group_fraction', 0) < .5:
        raise ValueError('Validation group fraction must be between zero and one half')
    for name in ('seed', 'epochs', 'batch_size'):
        if type(config.get(name)) is not int or config[name] < 1:
            raise ValueError(f'{name} must be a positive integer')
    for name in ('learning_rate', 'weight_decay', 'direction_loss_weight', 'human_loss_weight'):
        value = config.get(name)
        if not isinstance(value, (int, float)) or not np.isfinite(value) or value < 0:
            raise ValueError(f'Invalid {name}')
    required_rule = {
        'easy_min_crossings', 'easy_min_component_fraction', 'easy_max_p90_slope_deg',
        'caution_min_crossings', 'caution_min_component_fraction', 'caution_max_p90_slope_deg'}
    if not isinstance(config.get('human_rule'), dict) or set(config['human_rule']) != required_rule:
        raise ValueError('Invalid human_rule fields')
    # Exercise the rule validator with an otherwise valid example.
    human_terrain_class(conservative_crossings=4, conservative_largest_component_fraction=1,
                        permissive_crossings=4, permissive_largest_component_fraction=1,
                        slope_p90_deg=0, **config['human_rule'])


def build_human_labels(patches: pd.DataFrame, rule: dict[str, Any]) -> np.ndarray:
    required = (
        'conservative_crossing_count', 'conservative_largest_component_fraction',
        'permissive_crossing_count', 'permissive_largest_component_fraction', 'slope_p90_deg')
    if any(name not in patches for name in required):
        raise ValueError('Patch table lacks human terrain rule evidence')
    labels = [
        human_terrain_class(
            conservative_crossings=int(row.conservative_crossing_count),
            conservative_largest_component_fraction=float(row.conservative_largest_component_fraction),
            permissive_crossings=int(row.permissive_crossing_count),
            permissive_largest_component_fraction=float(row.permissive_largest_component_fraction),
            slope_p90_deg=float(row.slope_p90_deg), **rule)
        for row in patches[list(required)].itertuples(index=False)
    ]
    lookup = {name: index for index, name in enumerate(HUMAN_TERRAIN_CLASSES)}
    return np.asarray([lookup[name] for name in labels], dtype=np.int64)


def weighted_loss(targets: np.ndarray) -> tuple[nn.CrossEntropyLoss, np.ndarray]:
    counts = np.bincount(targets, minlength=3)
    if (counts == 0).any():
        raise ValueError('Every training class needs at least one patch')
    weights = counts.sum() / (len(counts) * counts)
    return nn.CrossEntropyLoss(weight=torch.tensor(weights, dtype=torch.float32)), counts


def class_metrics(true: np.ndarray, predicted: np.ndarray,
                  names: tuple[str, ...]) -> dict[str, Any]:
    matrix = confusion(true, predicted)
    totals = matrix.sum(axis=1)
    recalls = np.divide(np.diag(matrix), totals, out=np.zeros(3), where=totals > 0)
    return {
        'accuracy': float((true == predicted).mean()),
        'balanced_accuracy': float(recalls.mean()),
        'class_recall': {name: float(recalls[index]) for index, name in enumerate(names)},
        'confusion_matrix': matrix.tolist(),
    }


def metrics(model: nn.Module, loader: DataLoader) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray]:
    model.eval()
    rover_true, rover_predicted, direction_true, direction_predicted = [], [], [], []
    human_true, human_predicted = [], []
    with torch.no_grad():
        for values, rover, directions, human in loader:
            rover_logits, direction_logits, human_logits = model(values)
            rover_true.append(rover.numpy())
            rover_predicted.append(rover_logits.argmax(1).numpy())
            direction_true.append(directions.numpy())
            direction_predicted.append((direction_logits.sigmoid() >= .5).numpy())
            human_true.append(human.numpy())
            human_predicted.append(human_logits.argmax(1).numpy())
    rover_true_values = np.concatenate(rover_true)
    rover_predictions = np.concatenate(rover_predicted)
    human_true_values = np.concatenate(human_true)
    human_predictions = np.concatenate(human_predicted)
    directions = np.concatenate(direction_true)
    direction_predictions = np.concatenate(direction_predicted)
    result = {
        'samples': int(len(rover_true_values)),
        'rover': class_metrics(rover_true_values, rover_predictions, CLASS_NAMES),
        'human_terrain': class_metrics(human_true_values, human_predictions, HUMAN_TERRAIN_CLASSES),
        'direction_accuracy': {
            name: float((directions[:, index] == direction_predictions[:, index]).mean())
            for index, name in enumerate(DIRECTIONS)
        },
    }
    return result, rover_predictions, human_predictions, direction_predictions


def build_loader(values: np.ndarray, rover: np.ndarray, directions: np.ndarray, human: np.ndarray,
                 selected: np.ndarray, batch_size: int, shuffle: bool) -> DataLoader:
    dataset = TensorDataset(
        torch.from_numpy(values[selected]), torch.from_numpy(rover[selected]),
        torch.from_numpy(directions[selected]), torch.from_numpy(human[selected]))
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, num_workers=0)


def train(root: Path, config_path: Path) -> Path:
    root, config_path = root.resolve(), config_path.resolve()
    config = json.loads(config_path.read_text(encoding='utf-8'))
    validate_config(config)
    dataset = (root / config['dataset_run']).resolve()
    verify_run(dataset)
    patches = pd.read_csv(dataset / 'patches.csv')
    patches = patches.loc[patches['size_m'] == config['patch_size_m']].reset_index(drop=True)
    values = load_tensors(dataset, patches)
    roles = assign_splits(patches, config['test_region'],
                          config['validation_group_fraction'], config['seed'])
    mean, scale = fit_scaler(values, patches, roles)
    values = ((values - mean[None, :, None, None]) /
              scale[None, :, None, None]).astype(np.float32)
    rover_lookup = {name: index for index, name in enumerate(CLASS_NAMES)}
    rover = patches['label_class'].map(rover_lookup).to_numpy(dtype=np.int64)
    human = build_human_labels(patches, config['human_rule'])
    directions = patches[[f'nominal_{name}' for name in DIRECTIONS]].to_numpy(dtype=np.float32)
    random.seed(config['seed'])
    np.random.seed(config['seed'])
    torch.manual_seed(config['seed'])
    model = TerrainMobilityCNN()
    rover_loss, rover_counts = weighted_loss(rover[roles == 'train'])
    human_loss, human_counts = weighted_loss(human[roles == 'train'])
    direction_loss = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config['learning_rate'], weight_decay=config['weight_decay'])
    loaders = {
        role: build_loader(values, rover, directions, human, roles == role,
                           config['batch_size'], role == 'train')
        for role in ('train', 'validation', 'test')
    }
    notebook = '../operational_cnn/training/train_human_walkability.py'
    with Run(root, 'terrain_human_walkability_model', config, notebook) as run:
        run.record['torch'] = {'version': torch.__version__, 'device': 'cpu'}
        for path in (
                config_path, root / 'operational_cnn/model/terrain_mobility_cnn.py',
                root / 'operational_cnn/labels/human_walkability.py',
                dataset / 'provenance.json', dataset / 'patches.csv'):
            run.input(path)
        split_frame = patches[['patch_id', 'region', 'spatial_group', 'label_class']].copy()
        split_frame['human_terrain_class'] = [HUMAN_TERRAIN_CLASSES[index] for index in human]
        split_frame['role'] = roles
        split_frame.to_csv(run.path('splits_and_labels.csv'), index=False)
        run.path('scaler.json').write_text(json.dumps({
            'mean': mean.tolist(), 'scale': scale.tolist(),
            'fit': 'training groups only; equal region moment mass'}, indent=2), encoding='utf-8')
        history, best_state, best_score, best_epoch = [], None, -np.inf, None
        for epoch in range(1, config['epochs'] + 1):
            model.train()
            losses = []
            for batch_values, batch_rover, batch_directions, batch_human in loaders['train']:
                optimizer.zero_grad()
                rover_logits, direction_logits, human_logits = model(batch_values)
                loss = rover_loss(rover_logits, batch_rover)
                loss = loss + config['direction_loss_weight'] * direction_loss(
                    direction_logits, batch_directions)
                loss = loss + config['human_loss_weight'] * human_loss(human_logits, batch_human)
                loss.backward()
                optimizer.step()
                losses.append(float(loss.detach()))
            validation, _, _, _ = metrics(model, loaders['validation'])
            row = {
                'epoch': epoch,
                'train_loss': float(np.mean(losses)),
                'validation_rover_balanced_accuracy': validation['rover']['balanced_accuracy'],
                'validation_human_balanced_accuracy': validation['human_terrain']['balanced_accuracy'],
            }
            history.append(row)
            print(row, flush=True)
            score = validation['human_terrain']['balanced_accuracy']
            if score > best_score:
                best_score, best_epoch = score, epoch
                best_state = {name: value.detach().clone()
                              for name, value in model.state_dict().items()}
        assert best_state is not None
        model.load_state_dict(best_state)
        validation, _, _, _ = metrics(model, loaders['validation'])
        test_result, rover_predictions, human_predictions, direction_predictions = metrics(
            model, loaders['test'])
        torch.save({
            'state_dict': model.state_dict(), 'channels': 5,
            'rover_classes': CLASS_NAMES, 'human_terrain_classes': HUMAN_TERRAIN_CLASSES,
            'directions': DIRECTIONS, 'human_rule': config['human_rule']}, run.path('model.pt'))
        pd.DataFrame(history).to_csv(run.path('history.csv'), index=False)
        test_rows = patches.loc[roles == 'test', ['patch_id', 'region', 'label_class']].copy()
        test_rows['human_terrain_class'] = [HUMAN_TERRAIN_CLASSES[index]
                                            for index in human[roles == 'test']]
        test_rows['predicted_rover_class'] = [CLASS_NAMES[index] for index in rover_predictions]
        test_rows['predicted_human_terrain_class'] = [HUMAN_TERRAIN_CLASSES[index]
                                                      for index in human_predictions]
        for index, name in enumerate(DIRECTIONS):
            test_rows[f'predicted_{name}'] = direction_predictions[:, index]
        test_rows.to_csv(run.path('test_predictions.csv'), index=False)
        results = {
            'best_epoch': best_epoch,
            'validation': validation,
            'test': test_result,
            'train_rover_class_counts': dict(zip(CLASS_NAMES, rover_counts.tolist(), strict=True)),
            'train_human_class_counts': dict(zip(
                HUMAN_TERRAIN_CLASSES, human_counts.tolist(), strict=True)),
            'parameter_count': sum(parameter.numel() for parameter in model.parameters()),
            'claim_boundary': config['claim_boundary'],
        }
        run.path('metrics.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
        run.record['result'] = results
    return run.directory


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--config', type=Path)
    arguments = parser.parse_args()
    default = arguments.root / 'operational_cnn/configs/human_walkability_experiment.json'
    print(train(arguments.root, arguments.config or default))
