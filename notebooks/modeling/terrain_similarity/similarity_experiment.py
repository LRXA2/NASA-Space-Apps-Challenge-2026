"""Reproducible development-only CNN training and bidirectional retrieval diagnostics."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from notebooks.shared.inspection import check_input, verify_run
from notebooks.shared.processing import MOON_CRS, Run
from rasterio.warp import transform_bounds
from notebooks.modeling.terrain_similarity.similarity_cnn import (
    TerrainSimilarityCNN,
    context_overlap,
    contrastive_loss,
    cosine_top_k,
    rotate_batch,
    training_probabilities,
)
from notebooks.modeling.terrain_similarity.terrain_dataset import FEATURES
from notebooks.modeling.terrain_similarity.terrain_dataset import validate_config as validate_dataset_config
from notebooks.modeling.terrain_similarity.terrain_learning import (
    SplitFootprint,
    normalize_tensors,
    rank_candidates,
    validate_split_footprints,
)
from torch.nn import functional as F

ROTATION_REFLECTION_POLICY = 'quarter_turns_and_reflections_v1'


def validate_experiment(config: dict[str, Any]) -> None:
    for name in ('seed', 'epochs', 'steps_per_epoch', 'batch_size', 'queries_per_region', 'top_k'):
        if type(config[name]) is not int or config[name] < (0 if name == 'seed' else 1):
            raise ValueError(f'Invalid integer experiment setting: {name}')
    if config['batch_size'] < 2:
        raise ValueError('Contrastive batches need at least two patches')
    for name in ('learning_rate', 'weight_decay', 'temperature'):
        if type(config[name]) not in {float, int} or not np.isfinite(config[name]) or config[name] <= 0:
            raise ValueError(f'Invalid numeric experiment setting: {name}')
    for field, allowed in [('views', {'full_context', 'image_supported'}),
                           ('sampling_modes', {'region_balanced', 'count_weighted'})]:
        items = config[field]
        if not isinstance(items, list) or not items or len(items) != len(set(items)) or not set(items) <= allowed:
            raise ValueError(f'Invalid experiment choices: {field}')


def load_view(dataset: Path, view: str, run: Run) -> tuple[pd.DataFrame, np.ndarray, dict[str, Any], np.ndarray]:
    """Load only verified notebook-28 artifacts; reject unapproved regions and roles."""
    expected, evidence = verify_run(dataset), {}

    def consumed(name: str) -> Path:
        path = check_input(dataset / name, expected, evidence)
        run.input(path)
        return path

    manifest_path = dataset / 'provenance.json'
    run.input(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['stage'] != 'terrain_learning_readiness' or manifest['config']['patch_size_m'] != 960:
        raise ValueError('This architecture requires a notebook-28 960 m dataset')
    validate_dataset_config(manifest['config'])
    footprints = json.loads(consumed('split_footprints.json').read_text(encoding='utf-8'))
    validate_split_footprints([SplitFootprint(**item) for item in footprints['footprints']])
    patches = pd.read_csv(consumed('patches.csv'))
    roles = {(item['body'], item['region']): item['fold'] for item in manifest['config']['regions']}
    for item in pd.DataFrame(patches[['body', 'region', 'role', 'fold']]).drop_duplicates().to_dict('records'):
        if item['role'] != 'development' or roles.get((item['body'], item['region'])) != item['fold']:
            raise ValueError('Patch role or region disagrees with approved development manifest')
    patches = patches.loc[(patches.body == 'earth') | (patches.view == view)].reset_index(drop=True)
    if patches.empty or patches.patch_id.duplicated().any() or patches.location_id.duplicated().any():
        raise ValueError('Expected one selected support view per unique patch location')
    values = np.empty((len(patches), 3, 32, 32), dtype=np.float32)
    for shard, group in patches.groupby('shard', sort=True):
        with np.load(consumed(str(shard)), allow_pickle=False) as stored:
            indices = group.tensor_index.to_numpy(dtype=int)
            if stored['physical'].shape != (len(group), 3, 32, 32) or sorted(indices) != list(range(len(group))):
                raise ValueError('Tensor shard and patch manifest do not align')
            if not stored['valid'].all() or not np.isfinite(stored['physical']).all():
                raise ValueError('Initial CNN requires complete eligible terrain patches')
            values[group.index.to_numpy()] = stored['physical'][indices]
    scaler = json.loads(consumed(f'scaler_{view}.json').read_text(encoding='utf-8'))
    if (set(scaler['training_regions']) != set(patches.loc[patches.fold == 'train', 'region'])
            or scaler['channels'] != ['relative_elevation_m', 'slope_deg', 'local_elevation_std_m']):
        raise ValueError('Scaler training regions or channel order mismatch')
    normalized, valid = normalize_tensors(values, np.array(scaler['mean']), np.array(scaler['scale']))
    if not valid.all():
        raise ValueError('Unexpected invalid CNN input')
    bounds = []
    for item in patches.to_dict('records'):
        halo = item['context_m']
        target = 'EPSG:6933' if item['body'] == 'earth' else MOON_CRS
        bounds.append(transform_bounds(item['crs_wkt'], target, item['left'] - halo, item['bottom'] - halo,
                                       item['right'] + halo, item['top'] + halo, densify_pts=21))
    return patches, normalized, scaler, np.array(bounds)


def embed(model: TerrainSimilarityCNN, values: np.ndarray, device: torch.device,
          *, include_reflections: bool = False) -> np.ndarray:
    """Unit mean of four rotations, optionally all eight square symmetries.

    The default preserves notebook 29's original policy. Reflections move all
    scalar terrain channels together; use this option for BOTH retrieval sides
    and rebuild the candidate bank. No weights or physical scales are changed.
    """
    if type(include_reflections) is not bool:
        raise ValueError('include_reflections must be boolean')
    model.eval()
    outputs = []
    with torch.no_grad():
        for start in range(0, len(values), 256):
            batch = torch.from_numpy(values[start:start + 256]).to(device)
            rotations = [model(torch.rot90(batch, turn, dims=(-2, -1))) for turn in range(4)]
            if include_reflections:
                reflected = torch.flip(batch, dims=(-1,))
                rotations.extend(model(torch.rot90(reflected, turn, dims=(-2, -1))) for turn in range(4))
            outputs.append(F.normalize(torch.stack(rotations).mean(dim=0), dim=1).cpu().numpy())
    result = np.concatenate(outputs)
    if not np.isfinite(result).all() or not np.allclose(np.linalg.norm(result, axis=1), 1., atol=1e-5):
        raise ValueError('Invalid or zero retrieval embeddings')
    return result


def train(model: TerrainSimilarityCNN, values: np.ndarray, patches: pd.DataFrame, bounds: np.ndarray,
          config: dict[str, Any], mode: str, device: torch.device) -> tuple[pd.DataFrame, pd.DataFrame]:
    indices, probabilities = training_probabilities(patches.fold.tolist(), patches.region.tolist(), mode)
    training_values = torch.from_numpy(values[indices]).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config['learning_rate'], weight_decay=config['weight_decay'])
    rng = np.random.default_rng(config['seed'])
    history: list[dict[str, Any]] = []
    exposure = np.zeros(len(patches), dtype=np.int64)
    bodies = patches.body.to_numpy()
    model.train()
    for epoch in range(1, config['epochs'] + 1):
        losses, exclusions = [], []
        started = time.perf_counter()
        for _ in range(config['steps_per_epoch']):
            selected = rng.choice(len(indices), config['batch_size'], replace=True, p=probabilities)
            global_indices = indices[selected]
            np.add.at(exposure, global_indices, 1)
            batch = training_values[torch.as_tensor(selected, device=device)]
            first = rotate_batch(batch, rng.integers(0, 4, len(selected)))
            second = rotate_batch(batch, rng.integers(0, 4, len(selected)))
            overlap = context_overlap(bounds[global_indices], bodies[global_indices])
            loss = contrastive_loss(model(first), model(second), torch.as_tensor(overlap, device=device),
                                    config['temperature'])
            if not torch.isfinite(loss):
                raise ValueError('Nonfinite training loss')
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach()))
            exclusions.append(float((overlap.sum() - len(overlap)) / (len(overlap) * (len(overlap) - 1))))
        history.append({'epoch': epoch, 'loss': float(np.mean(losses)),
                        'excluded_negative_fraction': float(np.mean(exclusions)),
                        'seconds': time.perf_counter() - started})
        print(mode, epoch, 'loss', history[-1]['loss'], flush=True)
    audit = pd.DataFrame(patches[['patch_id', 'region', 'body', 'fold']]).copy()
    audit['training_draws'] = exposure
    if audit.loc[audit.fold == 'holdout', 'training_draws'].sum() != 0:
        raise ValueError('Holdout data entered training')
    return pd.DataFrame(history), audit


def evaluation_queries(patches: pd.DataFrame, per_region: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    selected = []
    for _, group in patches.groupby(['body', 'region'], sort=True):
        ordered = group.sort_values('patch_id').index.to_numpy()
        selected.extend(rng.choice(ordered, min(per_region, len(ordered)), replace=False).tolist())
    return np.array(selected, dtype=int)


def compare_retrieval(patches: pd.DataFrame, queries: np.ndarray, embeddings: dict[str, np.ndarray],
                      k: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare every method on identical queries/candidate pools in both directions."""
    rows, summaries = [], []
    descriptors = patches[FEATURES].to_numpy(dtype=float)
    for query_index in queries:
        query = patches.iloc[query_index]
        other_body = 'earth' if query.body == 'moon' else 'moon'
        cases = [('heldout_candidates', 'holdout')] if query.fold == 'train' else [
            ('heldout_queries', 'train'), ('both_heldout', 'holdout')]
        for case, candidate_role in cases:
            pool = patches.index[(patches.body == other_body) & (patches.fold == candidate_role)].to_numpy()
            ids = patches.iloc[pool].patch_id.tolist()
            physical_order, physical_scores = rank_candidates(descriptors[query_index], descriptors[pool], ids, k)
            choices = {'physical': (physical_order, physical_scores)}
            choices.update({name: cosine_top_k(values[query_index], values[pool], ids, k)
                            for name, values in embeddings.items()})
            for method, (order, scores) in choices.items():
                chosen = patches.iloc[pool[order]]
                summaries.append({
                    'direction': f'{query.body}_to_{other_body}', 'case': case,
                    'query_id': query.patch_id, 'query_region': query.region, 'method': method,
                    'candidate_count': len(pool), 'top_k_region_count': chosen.region.nunique(),
                    'overlap_with_physical_fraction': len(set(order) & set(physical_order)) / len(order) if len(order) else np.nan,
                })
                for rank, (index, score) in enumerate(zip(pool[order], scores, strict=True), 1):
                    candidate = patches.iloc[int(index)]
                    rows.append({'direction': f'{query.body}_to_{other_body}', 'case': case,
                                 'query_id': query.patch_id, 'candidate_id': candidate.patch_id,
                                 'query_region': query.region, 'candidate_region': candidate.region,
                                 'method': method, 'rank': rank, 'score': float(score),
                                 'score_kind': 'band_discrepancy_lower_better' if method == 'physical' else 'cosine_higher_better',
                                 **{f'delta_{name}': float(candidate[name] - query[name]) for name in FEATURES}})
    return pd.DataFrame(rows), pd.DataFrame(summaries)


def embedding_diagnostics(patches: pd.DataFrame, embeddings: np.ndarray) -> dict[str, Any]:
    """Collapse and body-separation clues; neither is a relevance metric."""
    train_mask = (patches.fold == 'train').to_numpy()
    heldout = ~train_mask
    centers = np.stack([embeddings[train_mask & (patches.body == body).to_numpy()].mean(axis=0)
                        for body in ('earth', 'moon')])
    distances = np.linalg.norm(embeddings[heldout, None] - centers[None], axis=2)
    predicted = np.array(['earth', 'moon'])[distances.argmin(axis=1)]
    actual = patches.loc[heldout, 'body'].to_numpy()
    recalls = {body: float(np.mean(predicted[actual == body] == body)) for body in ('earth', 'moon')}
    centered = embeddings - embeddings.mean(axis=0)
    singular = np.linalg.svd(centered, compute_uv=False)
    total = float(np.square(singular).sum())
    proportions = np.square(singular) / total if total > 0 else np.zeros_like(singular)
    positive = proportions[proportions > 0]
    return {'mean_coordinate_sd': float(embeddings.std(axis=0).mean()),
            'effective_rank': float(np.exp(-np.sum(positive * np.log(positive)))) if total > 0 else 0.,
            'heldout_body_centroid_recall': recalls, 'heldout_body_balanced_accuracy': float(np.mean(list(recalls.values()))),
            'interpretation': 'Body classification may reflect real geology or source artifacts; this is a shortcut diagnostic, not proof'}


def run_experiments(root: Path, config_path: Path) -> Path:
    root = root.resolve()
    config = json.loads(config_path.read_text(encoding='utf-8'))
    validate_experiment(config)
    dataset = (root / config['dataset_run']).resolve()
    if not dataset.is_relative_to(root / 'data/processed/terrain_learning_readiness'):
        raise ValueError('Use a local accepted notebook-28 dataset')
    os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.set_num_threads(4)
    device = torch.device(config['device'])
    if device.type == 'cuda' and not torch.cuda.is_available():
        raise ValueError('Configured CUDA is unavailable; explicitly choose CPU in the configuration if needed')
    with Run(root, 'terrain_similarity_cnn', config, 'modeling/terrain_similarity/29_similarity_cnn_experiment.ipynb') as run:
        for path in [config_path, Path(__file__), *(root / 'notebooks' / name for name in
                     ['modeling/terrain_similarity/similarity_cnn.py', 'modeling/terrain_similarity/terrain_learning.py', 'modeling/terrain_similarity/terrain_dataset.py', 'shared/inspection.py',
                      'shared/patch_analysis.py', 'shared/retrieval_analysis.py', 'requirements-modeling.txt'])]:
            run.input(path)
        revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, check=False)
        run.record.update({'git_revision': revision.stdout.strip(), 'torch': str(torch.__version__),
                           'cuda': torch.version.cuda, 'device': str(device),
                           'device_name': torch.cuda.get_device_name(device) if device.type == 'cuda' else 'CPU',
                           'independent_relevance_validated': False, 'reserves_opened': False})
        review_rows = []
        for view in config['views']:
            patches, values, scaler, bounds = load_view(dataset, view, run)
            queries = evaluation_queries(patches, config['queries_per_region'], config['seed'])
            patches.iloc[queries][['patch_id', 'body', 'region', 'fold']].to_csv(run.path(f'{view}/evaluation_queries.csv'), index=False)
            for mode in config['sampling_modes']:
                name = f'{view}/{mode}'
                torch.manual_seed(config['seed'])
                model = TerrainSimilarityCNN().to(device)
                initial = embed(model, values, device)
                history, exposure = train(model, values, patches, bounds, config, mode, device)
                learned = embed(model, values, device)
                history.to_csv(run.path(f'{name}/training_history.csv'), index=False)
                exposure.to_csv(run.path(f'{name}/training_exposure.csv'), index=False)
                checkpoint = run.path(f'{name}/model.pt')
                torch.save({key: value.detach().cpu() for key, value in model.state_dict().items()}, checkpoint)
                restored = TerrainSimilarityCNN().to(device)
                restored.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=True))
                np.testing.assert_allclose(embed(restored, values[queries[:8]], device), learned[queries[:8]], atol=1e-5, rtol=1e-5)
                np.savez_compressed(run.path(f'{name}/embeddings.npz'), patch_ids=patches.patch_id.to_numpy(dtype=str),
                                    cnn=learned, random_encoder=initial)
                run.path(f'{name}/preprocessing.json').write_text(json.dumps({
                    'dataset_run': config['dataset_run'], 'view': view, 'scaler': scaler,
                    'architecture': '3 stride-2 convolutions (16/32/64), 64 encoder features, 64-dimensional similarity head',
                    'inference': 'Mean of four 90-degree rotation embeddings, then L2 normalization',
                    'input_shape': [3, 32, 32], 'assessment_head': False,
                }, indent=2), encoding='utf-8')
                rankings, comparison = compare_retrieval(patches, queries, {'cnn': learned, 'random_encoder': initial}, config['top_k'])
                rankings.to_csv(run.path(f'{name}/retrieval.csv'), index=False)
                comparison.to_csv(run.path(f'{name}/query_comparison.csv'), index=False)
                regional = comparison.groupby(['direction', 'case', 'method', 'query_region'])[
                    ['top_k_region_count', 'overlap_with_physical_fraction']].mean().reset_index()
                regional.to_csv(run.path(f'{name}/regional_comparison.csv'), index=False)
                regional.groupby(['direction', 'case', 'method'])[['top_k_region_count', 'overlap_with_physical_fraction']].mean().to_csv(
                    run.path(f'{name}/macro_comparison.csv'))
                run.path(f'{name}/embedding_diagnostics.json').write_text(json.dumps({
                    key: embedding_diagnostics(patches, array) for key, array in [('random_encoder', initial), ('cnn', learned)]
                }, indent=2), encoding='utf-8')
                # Pool the same seeded two queries per region across methods/modes.
                review_queries = set(patches.iloc[queries].groupby(['body', 'region'], sort=True).head(2).patch_id)
                pooled = rankings.loc[rankings.query_id.isin(review_queries)]
                review_rows.extend(pooled[['direction', 'case', 'query_id', 'candidate_id']].assign(view=view).to_dict('records'))
                rng = np.random.default_rng(config['seed'])
                for query_id in sorted(review_queries):
                    query = patches.loc[patches.patch_id == query_id].iloc[0]
                    query_cases = pooled.loc[pooled.query_id == query_id, ['direction', 'case']].drop_duplicates()
                    for pair in query_cases.to_dict('records'):
                        candidate_role = 'train' if pair['case'] == 'heldout_queries' else 'holdout'
                        pool = patches.loc[(patches.body != query.body) & (patches.fold == candidate_role), 'patch_id']
                        for candidate_id in rng.choice(sorted(pool), min(2, len(pool)), replace=False):
                            review_rows.append({**pair, 'query_id': query_id, 'candidate_id': candidate_id, 'view': view})
        review = pd.DataFrame(review_rows).drop_duplicates().sort_values(['view', 'case', 'query_id', 'candidate_id'])
        review = review.sample(frac=1, random_state=config['seed']).reset_index(drop=True)
        for column in ['relevance', 'reviewer', 'reason']:
            review[column] = ''
        review.to_csv(run.path('pooled_review_unlabeled.csv'), index=False)
        run.record['result_status'] = 'Experimental models trained; independent relevance and no-match calibration still required'
    return run.directory


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    print(run_experiments(args.root, args.config or args.root / 'notebooks/modeling/terrain_similarity/similarity_experiment.json'))
