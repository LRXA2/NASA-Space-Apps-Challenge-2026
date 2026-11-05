"""Verified, read-only access to prepared terrain and the saved CNN/cache."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

from notebooks.modeling.terrain_similarity.model_weights import (
    check_checkpoint,
    checkpoint_references,
)
from notebooks.modeling.terrain_similarity.similarity_cnn import (
    TerrainSimilarityCNN,
    cosine_top_k,
)
from notebooks.modeling.terrain_similarity.similarity_experiment import (
    ROTATION_REFLECTION_POLICY,
    embed,
)
from notebooks.modeling.terrain_similarity.terrain_dataset import (
    CHANNELS,
    FEATURES,
    validate_config,
)
from notebooks.modeling.terrain_similarity.terrain_learning import normalize_tensors
from notebooks.shared.inspection import check_input, file_hash, verify_run
from notebooks.shared.retrieval_analysis import terrain_discrepancies


@dataclass(frozen=True)
class ArtifactConfig:
    model_run: str
    dataset_run: str
    orientation_run: str
    view: str = "full_context"
    sampling: str = "region_balanced"

    def __post_init__(self) -> None:
        if self.view not in {"full_context", "image_supported"}:
            raise ValueError("Unknown lunar support view")
        if self.sampling not in {"region_balanced", "count_weighted"}:
            raise ValueError("Unknown model sampling mode")
        for path in (self.model_run, self.dataset_run, self.orientation_run):
            if not isinstance(path, str) or not path.strip():
                raise ValueError(
                    "Pin nonempty local model, dataset and orientation run paths"
                )


class TerrainModel:
    """Own verified metadata, cached tensors and a saved-model inference session.

    Patch IDs index both ``patches`` and ``vectors`` in identical order. Loading
    writes nothing; callers can record ``evidence`` in their output provenance.
    """

    def __init__(
        self, root: Path, config: ArtifactConfig, *, rebuild_cache: bool = False
    ):
        self.root, self.config = root.resolve(), config
        self.evidence: dict[str, str] = {}
        self._tensors: dict[str, np.ndarray] = {}
        self._expected: dict[str, str] = {}
        self.dataset = self._run_path(config.dataset_run)
        source = self._run_path(config.model_run)
        self._register_run(self.dataset)
        self._register_run(source)
        manifest = json.loads(
            (self.dataset / "provenance.json").read_text(encoding="utf-8")
        )
        validate_config(manifest["config"])
        if (
            manifest.get("stage") != "terrain_learning_readiness"
            or manifest["config"]["patch_size_m"] != 960
            or manifest["config"]["spacing_m"] != 30
        ):
            raise ValueError("Use a prepared 960 m / 30 m terrain dataset")
        patches = pd.read_csv(self._consume(self.dataset / "patches.csv")).set_index(
            "patch_id", verify_integrity=True
        )
        roles = {
            (r["body"], r["region"]): r["fold"] for r in manifest["config"]["regions"]
        }
        for row in (
            pd.DataFrame(patches[["body", "region", "role", "fold"]])
            .drop_duplicates()
            .to_dict("records")
        ):
            if (
                row["role"] != "development"
                or roles.get((row["body"], row["region"])) != row["fold"]
            ):
                raise ValueError(
                    "Patch region or fold is outside the approved development manifest"
                )
        self.patches = patches.loc[
            (patches.body == "earth") | (patches.view == config.view)
        ].copy()
        if (
            self.patches.empty
            or self.patches.location_id.duplicated().any()
            or not (self.patches.size_m == 960).all()
            or not (self.patches.spacing_m == 30).all()
            or not (
                self.patches.loc[self.patches.body == "earth", "view"]
                == "natural_screen"
            ).all()
        ):
            raise ValueError(
                "Expected unique, prepared patches with the selected view and physical scale"
            )
        indices = self.patches.tensor_index.to_numpy(dtype=float)
        if (
            not np.isfinite(indices).all()
            or (indices < 0).any()
            or (indices != np.floor(indices)).any()
        ):
            raise ValueError("Tensor indices must be finite nonnegative integers")
        if self.patches.duplicated(["shard", "tensor_index"]).any():
            raise ValueError("Duplicate tensor rows in the patch manifest")
        # Validate descriptor units/ranges with the shared physical comparator.
        descriptors = self.patches[FEATURES].to_numpy(dtype=float)
        terrain_discrepancies(descriptors[0], descriptors)
        self.scaler = json.loads(
            self._consume(self.dataset / f"scaler_{config.view}.json").read_text(
                encoding="utf-8"
            )
        )
        if self.scaler["channels"] != list(CHANNELS) or set(
            self.scaler["training_regions"]
        ) != set(self.patches.loc[self.patches.fold == "train", "region"]):
            raise ValueError(
                "Scaler channels or training regions do not match the dataset"
            )
        self.folder = source / config.view / config.sampling
        source_preprocessing = json.loads(
            self._consume(self.folder / "preprocessing.json").read_text(
                encoding="utf-8"
            )
        )
        self.checkpoint = check_checkpoint(
            self.root,
            source,
            config.view,
            config.sampling,
            self._expected,
            self.evidence,
        )
        required = {
            "dataset_run": self.dataset.relative_to(self.root).as_posix(),
            "view": config.view,
            "input_shape": [3, 32, 32],
            "scaler": self.scaler,
        }
        if any(
            source_preprocessing.get(key) != value for key, value in required.items()
        ):
            raise ValueError("Saved model dataset/view/scaler/shape mismatch")
        self.preprocessing: dict[str, Any] = {
            **source_preprocessing,
            "source_checkpoint": self.checkpoint.relative_to(self.root).as_posix(),
            "source_model_sha256": self.evidence[str(self.checkpoint)],
            "source_sampling": config.sampling,
            "inference_policy": ROTATION_REFLECTION_POLICY,
            "orientation_checks_passed": True,
            "inference": "Mean of eight rotation/reflection embeddings, then L2 normalization",
        }
        self._model: TerrainSimilarityCNN | None = None
        if rebuild_cache:
            self.preprocessing["orientation_checks_passed"] = False
            self.vectors = self.encode(self.patches.index.tolist())
        else:
            cache = self._run_path(config.orientation_run)
            self._register_run(cache)
            metadata = json.loads(
                self._consume(cache / "preprocessing.json").read_text(encoding="utf-8")
            )
            cache_required = {
                **required,
                **{
                    key: self.preprocessing[key]
                    for key in (
                        "source_model_sha256",
                        "source_sampling",
                        "inference_policy",
                        "orientation_checks_passed",
                    )
                },
            }
            if metadata.get("source_checkpoint") not in checkpoint_references(
                self.root, source, config.view, config.sampling
            ) or any(
                metadata.get(key) != value for key, value in cache_required.items()
            ):
                raise ValueError(
                    "Orientation cache model lineage, scaler, view or inference policy mismatch"
                )
            with np.load(
                self._consume(cache / "embeddings.npz"), allow_pickle=False
            ) as archive:
                ids, self.vectors = archive["patch_ids"].copy(), archive["cnn"].copy()
            if (
                ids.ndim != 1
                or len(set(ids)) != len(ids)
                or set(ids) != set(self.patches.index)
            ):
                raise ValueError(
                    "Orientation cache patch IDs do not match the prepared dataset"
                )
            self.patches = self.patches.loc[ids].copy()
        if (
            self.vectors.shape != (len(self.patches), 64)
            or not np.isfinite(self.vectors).all()
            or not np.allclose(np.linalg.norm(self.vectors, axis=1), 1.0, atol=1e-5)
        ):
            raise ValueError("Expected finite unit embeddings aligned with patch IDs")

    def _run_path(self, relative: str) -> Path:
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root / "data/processed"):
            raise ValueError("Use local accepted runs under data/processed")
        return path

    def _register_run(self, directory: Path) -> None:
        self._expected.update(verify_run(directory))
        path = directory / "provenance.json"
        self.evidence[str(path)] = file_hash(path)

    def _consume(self, path: Path) -> Path:
        return check_input(path.resolve(), self._expected, self.evidence)

    def physical_patch(self, patch_id: str) -> np.ndarray:
        if patch_id not in self.patches.index:
            raise ValueError(f"Unknown prepared patch ID: {patch_id}")
        item = self.patches.loc[patch_id]
        shard = str(item["shard"])
        if shard not in self._tensors:
            path = (self.dataset / shard).resolve()
            if not path.is_relative_to(self.dataset):
                raise ValueError("Tensor shard escapes the prepared dataset")
            with np.load(self._consume(path), allow_pickle=False) as archive:
                physical, valid = archive["physical"], archive["valid"]
                if (
                    physical.ndim != 4
                    or physical.shape[1:] != (3, 32, 32)
                    or valid.shape != physical.shape
                    or valid.dtype != np.bool_
                    or not valid.all()
                    or not np.isfinite(physical).all()
                ):
                    raise ValueError(
                        "Expected complete finite three-channel 32 x 32 terrain tensors"
                    )
                self._tensors[shard] = physical.copy()
        index = int(item["tensor_index"])
        if index >= len(self._tensors[shard]):
            raise ValueError("Tensor index exceeds its shard")
        return self._tensors[shard][index].copy()

    def encode(self, patch_ids: list[str]) -> np.ndarray:
        if not patch_ids:
            raise ValueError("Choose at least one prepared patch to encode")
        if self._model is None:
            self._model = TerrainSimilarityCNN()
            self._model.load_state_dict(
                torch.load(self.checkpoint, map_location="cpu", weights_only=True)
            )
        physical = np.stack([self.physical_patch(patch_id) for patch_id in patch_ids])
        normalized, valid = normalize_tensors(
            physical, np.array(self.scaler["mean"]), np.array(self.scaler["scale"])
        )
        if not valid.all():
            raise ValueError("Invalid values in prepared terrain")
        return embed(
            self._model, normalized, torch.device("cpu"), include_reflections=True
        )

    def check_orientations(self) -> pd.DataFrame:
        """Check eight transformations of one representative per region before publishing a rebuilt cache."""
        ids = self.patches.groupby(["body", "region"], sort=True).head(1).index.tolist()
        reference = self.encode(ids)
        physical = np.stack([self.physical_patch(patch_id) for patch_id in ids])
        values, _ = normalize_tensors(
            physical, np.array(self.scaler["mean"]), np.array(self.scaler["scale"])
        )
        assert self._model is not None  # encode initializes the saved model above.
        pool = np.flatnonzero(self.patches.body.to_numpy() == "earth")
        candidate_ids = self.patches.iloc[pool].index.tolist()
        rows = []
        for mirrored in (False, True):
            for turns in range(4):
                transformed = np.flip(values, axis=-1) if mirrored else values
                transformed = np.rot90(transformed, turns, axes=(-2, -1)).copy()
                current = embed(
                    self._model,
                    transformed,
                    torch.device("cpu"),
                    include_reflections=True,
                )
                for i, patch_id in enumerate(ids):
                    order, _ = cosine_top_k(
                        current[i], self.vectors[pool], candidate_ids, 3
                    )
                    original_order, _ = cosine_top_k(
                        reference[i], self.vectors[pool], candidate_ids, 3
                    )
                    delta = float(np.abs(current[i] - reference[i]).max())
                    same_order = bool(np.array_equal(order, original_order))
                    if delta > 1e-5 or not same_order:
                        raise ValueError(
                            "Rebuilt cache failed rotation/reflection consistency checks"
                        )
                    rows.append(
                        {
                            "patch_id": patch_id,
                            "mirrored": mirrored,
                            "quarter_turns": turns,
                            "max_embedding_difference": delta,
                            "same_top_k_order": same_order,
                        }
                    )
        self.preprocessing["orientation_checks_passed"] = True
        return pd.DataFrame(rows)
