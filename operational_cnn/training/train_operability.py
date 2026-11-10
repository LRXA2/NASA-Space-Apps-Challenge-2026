"""Train the first geographically held-out experimental operability CNN."""
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

from operational_cnn.labels.route_labels import DIRECTIONS
from operational_cnn.model.operability_cnn import TerrainOperabilityCNN
from notebooks.shared.inspection import verify_run
from notebooks.shared.processing import Run


CLASS_NAMES = ('operable', 'marginal', 'non_operable')


def validate_config(config: dict[str, Any]) -> None:
    if config.get('schema_version') != 1 or config.get('patch_size_m') != 960:
        raise ValueError('Only the first 960 m experiment is supported')
    if config.get('test_region') not in {'northern_arizona', 'lanzarote', 'atacama_san_pedro', 'death_valley', 'wadi_rum'}:
        raise ValueError('Unknown test region')
    if not 0 < config.get('validation_group_fraction', 0) < .5:
        raise ValueError('Validation group fraction must be between zero and one half')
    for name in ('seed', 'epochs', 'batch_size'):
        if type(config.get(name)) is not int or config[name] < 1:
            raise ValueError(f'{name} must be a positive integer')
    for name in ('learning_rate', 'weight_decay', 'direction_loss_weight'):
        if not np.isfinite(config.get(name)) or config[name] < 0:
            raise ValueError(f'Invalid {name}')


def load_tensors(dataset: Path, patches: pd.DataFrame) -> np.ndarray:
    """Load region shards once and restore the patches.csv row order."""
    result = np.empty((len(patches), 5, 32, 32), dtype=np.float32)
    for region, indices in patches.groupby('region', sort=True).groups.items():
        shard = dataset / f'tensors/{region}_960m.npz'
        with np.load(shard) as archive:
            physical = archive['physical']
        rows = np.asarray(list(indices), dtype=int)
        tensor_indices = patches.loc[rows, 'tensor_index'].to_numpy(dtype=int)
        result[rows] = physical[tensor_indices]
    if not np.isfinite(result).all():
        raise ValueError('Training tensors must be complete and finite')
    return result


def assign_splits(patches: pd.DataFrame, test_region: str, fraction: float, seed: int) -> np.ndarray:
    """Hold out one whole region, then select validation by complete 5 km groups."""
    roles = np.full(len(patches), 'train', dtype=object)
    roles[patches['region'].to_numpy() == test_region] = 'test'
    rng = np.random.default_rng(seed)
    for region in sorted(set(patches['region']) - {test_region}):
        groups = np.array(sorted(patches.loc[patches['region'] == region, 'spatial_group'].unique()))
        rng.shuffle(groups)
        count = max(1, round(len(groups) * fraction))
        selected = set(groups[:count])
        mask = (patches['region'] == region) & patches['spatial_group'].isin(selected)
        roles[mask.to_numpy()] = 'validation'
    for group in patches['spatial_group'].unique():
        if len(set(roles[patches['spatial_group'].to_numpy() == group])) != 1:
            raise ValueError('Spatial group leaked across roles')
    return roles


def fit_scaler(values: np.ndarray, patches: pd.DataFrame, roles: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fit train-only channel moments with every training region given equal mass."""
    means, seconds = [], []
    for region in sorted(patches.loc[roles == 'train', 'region'].unique()):
        selected = values[(roles == 'train') & (patches['region'].to_numpy() == region)].astype(np.float64)
        means.append(selected.mean(axis=(0, 2, 3)))
        seconds.append(np.square(selected).mean(axis=(0, 2, 3)))
    mean = np.mean(means, axis=0)
    scale = np.sqrt(np.maximum(np.mean(seconds, axis=0) - mean * mean, 0.))
    return mean, np.where(scale > 1e-8, scale, 1.)


def confusion(true: np.ndarray, predicted: np.ndarray) -> np.ndarray:
    matrix = np.zeros((len(CLASS_NAMES), len(CLASS_NAMES)), dtype=int)
    np.add.at(matrix, (true, predicted), 1)
    return matrix


def metrics(model: nn.Module, loader: DataLoader) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    model.eval()
    true_classes, predicted_classes, true_directions, predicted_directions = [], [], [], []
    with torch.no_grad():
        for values, classes, directions in loader:
            class_logits, direction_logits = model(values)
            true_classes.append(classes.numpy())
            predicted_classes.append(class_logits.argmax(1).numpy())
            true_directions.append(directions.numpy())
            predicted_directions.append((direction_logits.sigmoid() >= .5).numpy())
    true = np.concatenate(true_classes)
    predicted = np.concatenate(predicted_classes)
    directions = np.concatenate(true_directions)
    direction_predictions = np.concatenate(predicted_directions)
    matrix = confusion(true, predicted)
    recalls = np.divide(np.diag(matrix), matrix.sum(axis=1), out=np.zeros(3), where=matrix.sum(axis=1) > 0)
    result = {
        'samples': int(len(true)),
        'accuracy': float((true == predicted).mean()),
        'balanced_accuracy': float(recalls.mean()),
        'class_recall': {name: float(recalls[index]) for index, name in enumerate(CLASS_NAMES)},
        'direction_accuracy': {
            name: float((directions[:, index] == direction_predictions[:, index]).mean())
            for index, name in enumerate(DIRECTIONS)
        },
        'confusion_matrix': matrix.tolist(),
    }
    return result, predicted, direction_predictions


def build_loader(values: np.ndarray, classes: np.ndarray, directions: np.ndarray,
                 selected: np.ndarray, batch_size: int, shuffle: bool) -> DataLoader:
    dataset = TensorDataset(torch.from_numpy(values[selected]), torch.from_numpy(classes[selected]),
                            torch.from_numpy(directions[selected]))
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
    roles = assign_splits(patches, config['test_region'], config['validation_group_fraction'], config['seed'])
    mean, scale = fit_scaler(values, patches, roles)
    values = ((values - mean[None, :, None, None]) / scale[None, :, None, None]).astype(np.float32)
    class_lookup = {name: index for index, name in enumerate(CLASS_NAMES)}
    classes = patches['label_class'].map(class_lookup).to_numpy(dtype=np.int64)
    directions = patches[[f'nominal_{name}' for name in DIRECTIONS]].to_numpy(dtype=np.float32)
    random.seed(config['seed'])
    np.random.seed(config['seed'])
    torch.manual_seed(config['seed'])
    model = TerrainOperabilityCNN()
    train_counts = np.bincount(classes[roles == 'train'], minlength=3)
    class_weights = train_counts.sum() / (len(CLASS_NAMES) * train_counts)
    class_loss = nn.CrossEntropyLoss(weight=torch.tensor(class_weights, dtype=torch.float32))
    direction_loss = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=config['learning_rate'], weight_decay=config['weight_decay'])
    train_loader = build_loader(values, classes, directions, roles == 'train', config['batch_size'], True)
    validation_loader = build_loader(values, classes, directions, roles == 'validation', config['batch_size'], False)
    test_loader = build_loader(values, classes, directions, roles == 'test', config['batch_size'], False)
    notebook = '../operational_cnn/notebooks/38_operability_cnn_experiment.ipynb'
    with Run(root, 'terrain_operability_model', config, notebook) as run:
        run.record['torch'] = {'version': torch.__version__, 'device': 'cpu'}
        for path in (config_path, Path(__file__), Path(__file__).with_name('operability_cnn.py'),
                     dataset / 'provenance.json', dataset / 'patches.csv'):
            run.input(path)
        split_frame = patches[['patch_id', 'region', 'spatial_group', 'label_class']].copy()
        split_frame['role'] = roles
        split_frame.to_csv(run.path('splits.csv'), index=False)
        run.path('scaler.json').write_text(json.dumps({'mean': mean.tolist(), 'scale': scale.tolist(),
            'fit': 'training groups only; equal region moment mass'}, indent=2), encoding='utf-8')
        history, best_state, best_score, best_epoch = [], None, -np.inf, None
        for epoch in range(1, config['epochs'] + 1):
            model.train()
            losses = []
            for batch_values, batch_classes, batch_directions in train_loader:
                optimizer.zero_grad()
                class_logits, direction_logits = model(batch_values)
                loss = class_loss(class_logits, batch_classes)
                loss = loss + config['direction_loss_weight'] * direction_loss(direction_logits, batch_directions)
                loss.backward()
                optimizer.step()
                losses.append(float(loss.detach()))
            validation, _, _ = metrics(model, validation_loader)
            row = {'epoch': epoch, 'train_loss': float(np.mean(losses)),
                   'validation_accuracy': validation['accuracy'],
                   'validation_balanced_accuracy': validation['balanced_accuracy']}
            history.append(row)
            print(row, flush=True)
            if validation['balanced_accuracy'] > best_score:
                best_score, best_epoch = validation['balanced_accuracy'], epoch
                best_state = {name: value.detach().clone() for name, value in model.state_dict().items()}
        assert best_state is not None
        model.load_state_dict(best_state)
        validation, _, _ = metrics(model, validation_loader)
        test_result, predicted, direction_predictions = metrics(model, test_loader)
        torch.save({'state_dict': model.state_dict(), 'channels': 5, 'classes': CLASS_NAMES,
                    'directions': DIRECTIONS}, run.path('model.pt'))
        pd.DataFrame(history).to_csv(run.path('history.csv'), index=False)
        test_rows = patches.loc[roles == 'test', ['patch_id', 'region', 'label_class']].copy()
        test_rows['predicted_class'] = [CLASS_NAMES[index] for index in predicted]
        for index, name in enumerate(DIRECTIONS):
            test_rows[f'predicted_{name}'] = direction_predictions[:, index]
        test_rows.to_csv(run.path('test_predictions.csv'), index=False)
        results = {'best_epoch': best_epoch, 'validation': validation, 'test': test_result,
                   'train_class_counts': dict(zip(CLASS_NAMES, train_counts.tolist(), strict=True)),
                   'parameter_count': sum(parameter.numel() for parameter in model.parameters()),
                   'claim_boundary': config['claim_boundary']}
        run.path('metrics.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
        run.record['result'] = results
    return run.directory


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--config', type=Path)
    arguments = parser.parse_args()
    default = arguments.root / 'operational_cnn/configs/cnn_experiment.json'
    print(train(arguments.root, arguments.config or default))

