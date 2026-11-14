"""Small multi-task CNN for provisional terrain-operability experiments."""
from __future__ import annotations

import torch
from torch import nn


class TerrainOperabilityCNN(nn.Module):
    """Five 32x32 terrain channels -> class and directional crossing logits."""

    def __init__(self) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(5, 16, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(16, 32, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(32, 64, 3, stride=2, padding=1), nn.ReLU(),
            nn.Flatten(), nn.Linear(64 * 4 * 4, 64), nn.ReLU(),
        )
        self.class_head = nn.Linear(64, 3)
        self.direction_head = nn.Linear(64, 4)

    def forward(self, values: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if values.ndim != 4 or tuple(values.shape[1:]) != (5, 32, 32):
            raise ValueError('Expected NCHW tensors with shape (N, 5, 32, 32)')
        features = self.encoder(values)
        return self.class_head(features), self.direction_head(features)

