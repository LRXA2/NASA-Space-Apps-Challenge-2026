"""Versioned CNN checkpoints kept separately from training tables and caches."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import torch

from notebooks.shared.inspection import check_input, file_hash


def checkpoint_path(root: Path, model_run: Path, view: str, sampling: str) -> Path:
    """Locate a variant's weights using its immutable training run ID."""
    root, model_run = root.resolve(), model_run.resolve()
    if model_run.parent != root / "data/processed/terrain_similarity_cnn":
        raise ValueError("Expected a terrain_similarity_cnn training run")
    if view not in {"full_context", "image_supported"} or sampling not in {
        "region_balanced",
        "count_weighted",
    }:
        raise ValueError("Unknown model view or sampling mode")
    directory = root / "notebooks/modeling/terrain_similarity/weights"
    path = (directory / model_run.name / view / sampling / "model.pt").resolve()
    if not path.is_relative_to(directory):
        raise ValueError("Checkpoint escapes the weights directory")
    return path


def checkpoint_references(
    root: Path, model_run: Path, view: str, sampling: str
) -> tuple[str, str]:
    """Current and historical identities for the same hash-verified checkpoint."""
    current = checkpoint_path(root, model_run, view, sampling)
    original = model_run.resolve() / view / sampling / "model.pt"
    return (
        current.relative_to(root.resolve()).as_posix(),
        original.relative_to(root.resolve()).as_posix(),
    )


def check_checkpoint(
    root: Path,
    model_run: Path,
    view: str,
    sampling: str,
    expected: dict[str, str],
    evidence: dict[str, str],
) -> Path:
    """Verify new weights or relocated weights against the original run digest.

    Historical manifests remain untouched. New training runs register a small
    weights.json output containing the checkpoint's new location and digest.
    """
    path = checkpoint_path(root, model_run, view, sampling)
    folder = model_run.resolve() / view / sampling
    original = str(folder / "model.pt")
    if original in expected:
        digest = expected[original]
    else:
        descriptor = check_input(folder / "weights.json", expected, evidence)
        record = json.loads(descriptor.read_text(encoding="utf-8"))
        if record["path"] != path.relative_to(root.resolve()).as_posix():
            raise ValueError("Checkpoint descriptor does not match the training run")
        digest = record["sha256"]
    return check_input(path, {str(path): digest}, evidence)


def save_checkpoint(
    root: Path,
    model_run: Path,
    view: str,
    sampling: str,
    state: Mapping[str, torch.Tensor],
) -> Path:
    """Write weights once and register their hash in the training run outputs."""
    path = checkpoint_path(root, model_run, view, sampling)
    descriptor = model_run / view / sampling / "weights.json"
    if path.exists() or descriptor.exists():
        raise FileExistsError("A checkpoint already exists for this run and variant")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        torch.save(dict(state), stream)
    record = {
        "path": path.relative_to(root.resolve()).as_posix(),
        "sha256": file_hash(path),
    }
    with descriptor.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
    return path
