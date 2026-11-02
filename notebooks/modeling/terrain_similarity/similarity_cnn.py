"""Shared terrain encoder and similarity objective; no file access or assessment head."""
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F


class TerrainSimilarityCNN(nn.Module):
    """Three-channel 32x32 terrain -> 64 encoder features -> unit retrieval vector."""

    def __init__(self) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 16, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(16, 32, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(32, 64, 3, stride=2, padding=1), nn.ReLU(),
            nn.Flatten(), nn.Linear(64 * 4 * 4, 64), nn.ReLU(),
        )
        self.similarity_head = nn.Sequential(nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 64))

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        if values.ndim != 4 or tuple(values.shape[1:]) != (3, 32, 32):
            raise ValueError('Expected NCHW 32x32 patches with three terrain channels')
        return F.normalize(self.similarity_head(self.encoder(values)), dim=1)


def rotate_batch(values: torch.Tensor, turns: np.ndarray) -> torch.Tensor:
    """Rotate all channels of each patch together without resampling or amplitude changes."""
    if values.ndim != 4 or values.shape[-1] != values.shape[-2] or turns.shape != (len(values),):
        raise ValueError('Expected square NCHW patches and one rotation per patch')
    if not np.issubdtype(turns.dtype, np.integer) or not np.isin(turns, [0, 1, 2, 3]).all():
        raise ValueError('Rotation must be 0, 1, 2 or 3 quarter turns')
    result = torch.empty_like(values)
    for turn in range(4):
        selected = torch.as_tensor(turns == turn, device=values.device)
        result[selected] = torch.rot90(values[selected], turn, dims=(-2, -1))
    return result


def context_overlap(bounds: np.ndarray, bodies: np.ndarray) -> np.ndarray:
    """Bounds already include context and use one common metric CRS per body."""
    if bounds.ndim != 2 or bounds.shape[1] != 4 or bodies.shape != (len(bounds),):
        raise ValueError('Expected Nx4 context bounds and aligned bodies')
    if (not np.isfinite(bounds).all() or (bounds[:, :2] >= bounds[:, 2:]).any()
            or not np.isin(bodies, ['earth', 'moon']).all()):
        raise ValueError('Invalid bounds or bodies')
    return ((bodies[:, None] == bodies[None, :])
            & (bounds[:, None, 0] <= bounds[None, :, 2]) & (bounds[:, None, 2] >= bounds[None, :, 0])
            & (bounds[:, None, 1] <= bounds[None, :, 3]) & (bounds[:, None, 3] >= bounds[None, :, 1]))


def contrastive_loss(first: torch.Tensor, second: torch.Tensor, overlap: torch.Tensor,
                     temperature: float = .2) -> torch.Tensor:
    """NT-Xent with same-patch positives and overlapping-context negatives removed."""
    if first.ndim != 2 or first.shape != second.shape or len(first) < 2:
        raise ValueError('Expected two aligned batches of at least two vectors')
    count = len(first)
    if (overlap.shape != (count, count) or overlap.dtype != torch.bool
            or not torch.equal(overlap, overlap.T) or not overlap.diagonal().all()):
        raise ValueError('Expected a symmetric boolean overlap matrix')
    if not np.isfinite(temperature) or temperature <= 0 or not (~overlap).any(dim=1).all():
        raise ValueError('Positive temperature and at least one nonoverlapping negative per anchor are required')
    values = torch.cat([first, second])
    if not torch.isfinite(values).all() or (torch.linalg.vector_norm(values, dim=1) < 1e-8).any():
        raise ValueError('Embeddings must be finite and nonzero')
    values = F.normalize(values, dim=1)
    logits = values @ values.T / temperature
    target = (torch.arange(2 * count, device=values.device) + count) % (2 * count)
    allowed = (~overlap).repeat(2, 2)
    allowed[torch.arange(2 * count, device=values.device), target] = True
    allowed.fill_diagonal_(False)
    return F.cross_entropy(logits.masked_fill(~allowed, float('-inf')), target)


def training_probabilities(roles: list[str], regions: list[str], mode: str) -> tuple[np.ndarray, np.ndarray]:
    """Training-only indices and sampling probabilities; holdout never enters a batch."""
    if len(roles) != len(regions) or not set(roles) <= {'train', 'holdout'} or mode not in {'region_balanced', 'count_weighted'}:
        raise ValueError('Invalid aligned roles, regions, or sampling mode')
    for region in set(regions):
        if len({role for role, name in zip(roles, regions, strict=True) if name == region}) != 1:
            raise ValueError('A region cannot cross fold roles')
    indices = np.flatnonzero(np.array(roles) == 'train')
    if len(indices) < 2:
        raise ValueError('At least two training patches are required')
    _, inverse, counts = np.unique(np.array(regions)[indices], return_inverse=True, return_counts=True)
    weights = 1. / counts[inverse] if mode == 'region_balanced' else np.ones(len(indices))
    return indices, weights / weights.sum()


def cosine_top_k(query: np.ndarray, candidates: np.ndarray, ids: list[str], k: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """Unit-vector retrieval with stable ID tie breaks, independent of query body."""
    if query.ndim != 1 or candidates.ndim != 2 or candidates.shape[1] != len(query):
        raise ValueError('Aligned query and candidate dimensions are required')
    if len(ids) != len(candidates) or len(set(ids)) != len(ids) or type(k) is not int or k < 1:
        raise ValueError('Unique candidate IDs and positive integer k are required')
    query_norm, norms = np.linalg.norm(query), np.linalg.norm(candidates, axis=1)
    if not np.isfinite(query).all() or not np.isfinite(candidates).all() or query_norm < 1e-8 or (norms < 1e-8).any():
        raise ValueError('Cosine similarity requires finite nonzero vectors')
    scores = np.clip((candidates @ query) / (norms * query_norm), -1., 1.)
    order = np.lexsort((np.array(ids, dtype=str), -scores))[:k]
    return order, scores[order]
