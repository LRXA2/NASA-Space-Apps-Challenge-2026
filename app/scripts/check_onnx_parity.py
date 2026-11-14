"""Export both CNNs to ONNX and compare onnxruntime output with the saved Python outputs.

For the possible terrain upload (team blocker T1). Nothing in the app reads these models yet.

    .venv/Scripts/python.exe app/scripts/check_onnx_parity.py <out_dir> [hanxi_model_run]

Needs torch, onnx, onnxscript and onnxruntime in the venv, the runs listed in data/README.md, and
Hanxi's model run (default temp/terrain_human_walkability_model/20261112T103924450917Z_bd0fc2).
Writes only into <out_dir>: similarity.onnx and mobility.onnx.

Similarity: every prepared patch (8 rotations/reflections, mean, L2 norm) against embeddings.npz.
Walkability: every lunar patch against predictions.csv probabilities and classes.
"""
import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import pandas as pd
import torch
from torch import nn
from torch.nn import functional as F

sys.path.insert(0, str(Path.cwd()))
from notebooks.modeling.terrain_similarity.similarity_cnn import TerrainSimilarityCNN  # noqa: E402
from operational_cnn.model.terrain_mobility_cnn import TerrainMobilityCNN  # noqa: E402

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
torch.set_num_threads(2)


class SimilarityExport(nn.Module):
    """Same layers and weights as TerrainSimilarityCNN.forward, minus the Python shape check."""

    def __init__(self, model):
        super().__init__()
        self.encoder, self.similarity_head = model.encoder, model.similarity_head

    def forward(self, x):
        return F.normalize(self.similarity_head(self.encoder(x)), dim=1)


class MobilityExport(nn.Module):
    """TerrainMobilityCNN heads with the inference-time softmax/sigmoid folded in."""

    def __init__(self, model):
        super().__init__()
        self.m = model

    def forward(self, x):
        f = self.m.encoder(x)
        return (torch.softmax(self.m.rover_head(f), 1), torch.sigmoid(self.m.direction_head(f)),
                torch.softmax(self.m.human_terrain_head(f), 1))


def export(module, channels, path, outputs):
    module.eval()
    torch.onnx.export(module, torch.zeros(1, channels, 32, 32), str(path), input_names=['x'],
                      output_names=outputs, dynamic_axes={'x': {0: 'n'}, **{o: {0: 'n'} for o in outputs}},
                      opset_version=17, dynamo=False)
    return ort.InferenceSession(str(path), providers=['CPUExecutionProvider'])


def eight_way(run, values):
    """Browser-side orientation policy: 4 rotations x (plain, mirrored), mean, L2 normalise."""
    outs = []
    for mirrored in (False, True):
        base = values[..., ::-1] if mirrored else values
        for turn in range(4):
            outs.append(run(np.ascontiguousarray(np.rot90(base, turn, axes=(-2, -1)), dtype=np.float32)))
    mean = np.mean(outs, axis=0)
    return mean / np.linalg.norm(mean, axis=1, keepdims=True)


report = {}

# ---- Aarron: similarity CNN vs embeddings.npz (orientation cache) ----
root = Path.cwd()
dataset = root / 'data/processed/terrain_learning_readiness/20261101T064233918547Z_4a05ac'
weights = root / 'notebooks/modeling/terrain_similarity/weights/20261101T082707986851Z_5413e6/full_context/region_balanced/model.pt'
cache = root / 'data/processed/terrain_similarity_orientation/20261102T073257899753Z_7b9c4f/embeddings.npz'
model = TerrainSimilarityCNN()
model.load_state_dict(torch.load(weights, map_location='cpu', weights_only=True))
model.eval()
session = export(SimilarityExport(model), 3, OUT / 'similarity.onnx', ['embedding'])
scaler = json.loads((dataset / 'scaler_full_context.json').read_text())
mean, scale = np.array(scaler['mean']), np.array(scaler['scale'])
patches = pd.read_csv(dataset / 'patches.csv').set_index('patch_id')
with np.load(cache, allow_pickle=False) as z:
    ids, cached = z['patch_ids'], z['cnn']
order = {pid: i for i, pid in enumerate(ids)}
diffs, torch_diffs, top1_same = [], [], []
earth_ids = [p for p in ids if patches.loc[p, 'body'] == 'earth']
earth_vectors = cached[[order[p] for p in earth_ids]]
for shard, group in patches.loc[list(ids)].groupby('shard'):
    with np.load(dataset / shard, allow_pickle=False) as z:
        physical = z['physical'][group['tensor_index'].to_numpy()]
    values = np.where(np.isfinite(physical), (physical - mean[None, :, None, None]) / scale[None, :, None, None], 0.)
    values = values.astype(np.float32)
    onnx_vec = eight_way(lambda v: session.run(None, {'x': v})[0], values)
    with torch.no_grad():
        torch_vec = eight_way(lambda v: model(torch.from_numpy(v)).numpy(), values)
    saved = cached[[order[p] for p in group.index]]
    diffs.append(np.abs(onnx_vec - saved).max(axis=1))
    torch_diffs.append(np.abs(onnx_vec - torch_vec).max(axis=1))
    moon = (group['body'] == 'moon').to_numpy()
    if moon.any():
        top1_same.extend(np.argmax(onnx_vec[moon] @ earth_vectors.T, 1) == np.argmax(saved[moon] @ earth_vectors.T, 1))
diffs, torch_diffs = np.concatenate(diffs), np.concatenate(torch_diffs)
report['similarity'] = {
    'onnx_bytes': (OUT / 'similarity.onnx').stat().st_size, 'patches_checked': int(len(diffs)),
    'max_abs_diff_vs_embeddings_npz': float(diffs.max()), 'max_abs_diff_vs_torch_same_input': float(torch_diffs.max()),
    'moon_top1_earth_match_identical': f'{int(np.sum(top1_same))}/{len(top1_same)}'}

# ---- Hanxi: mobility CNN vs predictions.csv ----
model_run = root / (sys.argv[2] if len(sys.argv) > 2 else 'temp/terrain_human_walkability_model/20261112T103924450917Z_bd0fc2')
inference = root / 'data/processed/terrain_human_walkability_lunar_inference/20261112T120422201915Z_101366'
checkpoint = torch.load(model_run / 'model.pt', map_location='cpu', weights_only=True)
mobility = TerrainMobilityCNN()
mobility.load_state_dict(checkpoint['state_dict'])
session = export(MobilityExport(mobility), 5, OUT / 'mobility.onnx', ['rover', 'direction', 'human'])
scaler = json.loads((model_run / 'scaler.json').read_text())
mean, scale = np.asarray(scaler['mean'], np.float32), np.asarray(scaler['scale'], np.float32)
predictions = pd.read_csv(inference / 'predictions.csv')
rover_cols = ['rover_probability_operable', 'rover_probability_marginal', 'rover_probability_non_operable']
human_cols = ['human_probability_easy', 'human_probability_caution', 'human_probability_unsuitable']
dir_cols = [f'probability_{d}' for d in ('north_south', 'east_west', 'northwest_southeast', 'northeast_southwest')]
worst, class_mismatch = 0.0, 0
for shard, group in predictions.groupby('tensor_shard'):
    with np.load(inference / shard.replace('\\', '/'), allow_pickle=False) as z:
        physical = z['physical'][group['tensor_index'].to_numpy()]
    values = ((physical - mean[None, :, None, None]) / scale[None, :, None, None]).astype(np.float32)
    rover, direction, human = session.run(None, {'x': values})
    for got, cols in ((rover, rover_cols), (direction, dir_cols), (human, human_cols)):
        worst = max(worst, float(np.abs(got - group[cols].to_numpy()).max()))
    class_mismatch += int((np.array(['operable', 'marginal', 'non_operable'])[rover.argmax(1)] != group['predicted_rover_class']).sum())
    class_mismatch += int((np.array(['easy', 'caution', 'unsuitable'])[human.argmax(1)] != group['predicted_human_terrain_class']).sum())
report['mobility'] = {'onnx_bytes': (OUT / 'mobility.onnx').stat().st_size, 'patches_checked': int(len(predictions)),
                      'max_abs_prob_diff_vs_predictions_csv': worst, 'class_mismatches': class_mismatch}
print(json.dumps(report, indent=2))
