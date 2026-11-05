"""Saved-model pipeline contracts, independent of local model quality."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from notebooks.modeling.terrain_similarity.model_weights import save_checkpoint
from notebooks.modeling.terrain_similarity.pipeline import (
    ArtifactConfig,
    TerrainModel,
    compare_sites,
)
from notebooks.modeling.terrain_similarity.pipeline.main import retrieve_matches
from notebooks.modeling.terrain_similarity.similarity_cnn import TerrainSimilarityCNN
from notebooks.modeling.terrain_similarity.similarity_experiment import embed
from notebooks.shared.inspection import file_hash


def write_manifest(directory: Path, **metadata) -> None:
    outputs = [
        {"path": p.relative_to(directory).as_posix(), "sha256": file_hash(p)}
        for p in sorted(directory.rglob("*"))
        if p.is_file() and p.name != "provenance.json"
    ]
    (directory / "provenance.json").write_text(
        json.dumps({"status": "complete", "outputs": outputs, **metadata}),
        encoding="utf-8",
    )


def prepared_fixture(
    root: Path, *, extra_moon_patch: bool = False, relocate_weights: bool = True
) -> ArtifactConfig:
    """Four approved development patches, identical inputs and a known ID ordering."""
    dataset = root / "data/processed/fixture_dataset"
    source = root / "data/processed/terrain_similarity_cnn/fixture_model"
    cache = root / "data/processed/fixture_cache"
    folder = source / "full_context/region_balanced"
    for path in (dataset, folder, cache):
        path.mkdir(parents=True)
    rows, regions = [], []
    for index, (patch_id, body, region, fold) in enumerate(
        [
            ("earth-a", "earth", "wadi_rum", "train"),
            ("earth-b", "earth", "atacama_san_pedro", "holdout"),
            ("moon-a", "moon", "A3CLR22_2_Haworth", "train"),
            ("moon-b", "moon", "A3CLR22_10_Leibnitz_Beta_Plateau", "holdout"),
        ]
    ):
        regions.append(
            dict(body=body, region=region, fold=fold, role="development", run="fixture")
        )
        rows.append(
            dict(
                patch_id=patch_id,
                location_id=patch_id,
                body=body,
                region=region,
                fold=fold,
                role="development",
                view="natural_screen" if body == "earth" else "full_context",
                size_m=960,
                spacing_m=30,
                context_m=150,
                shard="tensors.npz",
                tensor_index=index,
                left=10.0,
                right=12.0,
                bottom=20.0,
                top=22.0,
                crs_wkt="EPSG:4326",
                slope_median_deg=10.0,
                slope_p90_deg=20.0,
                central_relief_m=100.0,
                plane_residual_fraction=0.2,
                local_sd_median_m=10.0,
            )
        )
    if extra_moon_patch:
        rows.append(
            {
                **rows[2],
                "patch_id": "moon-c",
                "location_id": "moon-c",
                "tensor_index": 4,
            }
        )
    pd.DataFrame(rows).to_csv(dataset / "patches.csv", index=False)
    physical = np.random.default_rng(7).normal(size=(1, 3, 32, 32)).astype(np.float32)
    physical[:, 1:] = np.abs(physical[:, 1:])
    physical = np.repeat(physical, len(rows), axis=0)
    np.savez_compressed(
        dataset / "tensors.npz",
        physical=physical,
        valid=np.ones_like(physical, dtype=bool),
    )
    scaler = dict(
        channels=["relative_elevation_m", "slope_deg", "local_elevation_std_m"],
        mean=[0.0, 0.0, 0.0],
        scale=[1.0, 1.0, 1.0],
        training_regions=["wadi_rum", "A3CLR22_2_Haworth"],
    )
    (dataset / "scaler_full_context.json").write_text(
        json.dumps(scaler), encoding="utf-8"
    )
    write_manifest(
        dataset,
        stage="terrain_learning_readiness",
        config=dict(
            schema_version=1,
            spacing_m=30,
            patch_size_m=960,
            context_m=150,
            top_k=1,
            regions=regions,
            runs={"fixture": "unused"},
        ),
    )
    model = TerrainSimilarityCNN()
    torch.save(model.state_dict(), folder / "model.pt")
    preprocessing = dict(
        dataset_run=dataset.relative_to(root).as_posix(),
        view="full_context",
        input_shape=[3, 32, 32],
        scaler=scaler,
    )
    (folder / "preprocessing.json").write_text(
        json.dumps(preprocessing), encoding="utf-8"
    )
    write_manifest(source, stage="terrain_similarity_cnn")
    vectors = embed(model, physical, torch.device("cpu"), include_reflections=True)
    # A valid cache may use a different row order; each vector must follow its ID.
    order = [3, 1, 2, 0, *([4] if extra_moon_patch else [])]
    np.savez_compressed(
        cache / "embeddings.npz",
        patch_ids=np.array([rows[i]["patch_id"] for i in order]),
        cnn=vectors[order],
    )
    (cache / "preprocessing.json").write_text(
        json.dumps(
            {
                **preprocessing,
                "inference_policy": "quarter_turns_and_reflections_v1",
                "source_sampling": "region_balanced",
                "source_checkpoint": (folder / "model.pt").relative_to(root).as_posix(),
                "source_model_sha256": file_hash(folder / "model.pt"),
                "orientation_checks_passed": True,
            }
        ),
        encoding="utf-8",
    )
    write_manifest(cache, stage="terrain_similarity_orientation")
    if relocate_weights:
        target = (
            root
            / "notebooks/modeling/terrain_similarity/weights/fixture_model/full_context/region_balanced/model.pt"
        )
        target.parent.mkdir(parents=True)
        (folder / "model.pt").rename(target)
    return ArtifactConfig(
        source.relative_to(root).as_posix(),
        dataset.relative_to(root).as_posix(),
        cache.relative_to(root).as_posix(),
    )


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)

    def test_relocated_weights_preserve_legacy_cache_and_reject_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = prepared_fixture(root, relocate_weights=False)
            original = root / config.model_run / "full_context/region_balanced/model.pt"
            target = (
                root
                / "notebooks/modeling/terrain_similarity/weights/fixture_model"
                / "full_context/region_balanced/model.pt"
            )
            target.parent.mkdir(parents=True)
            original.rename(target)
            terrain = TerrainModel(root, config)
            self.assertEqual(terrain.checkpoint, target)
            matches, _, summary = compare_sites(terrain, "Haworth", "wadi_rum", top_k=1)
            self.assertEqual(matches.candidate_id.tolist(), ["earth-a"])
            self.assertAlmostEqual(summary["median_best_patch_cosine"], 1.0, places=6)
            self.assertIn(str(target), terrain.evidence)
            with target.open("ab") as stream:
                stream.write(b"changed")
            with self.assertRaisesRegex(
                ValueError, "Unregistered or changed run output"
            ):
                TerrainModel(root, config)

    def test_new_training_weights_load_with_registered_descriptor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = prepared_fixture(root)
            source = root / config.model_run
            target = (
                root
                / "notebooks/modeling/terrain_similarity/weights/fixture_model/full_context/region_balanced/model.pt"
            )
            state = torch.load(target, weights_only=True)
            target.unlink()  # Replace only this temporary fixture with the training writer.
            saved = save_checkpoint(
                root, source, "full_context", "region_balanced", state
            )
            self.assertEqual(saved, target)
            self.assertFalse(
                (source / "full_context/region_balanced/model.pt").exists()
            )
            write_manifest(source, stage="terrain_similarity_cnn")
            cache = root / config.orientation_run
            metadata_path = cache / "preprocessing.json"
            metadata = json.loads(metadata_path.read_text())
            metadata["source_checkpoint"] = target.relative_to(root).as_posix()
            metadata["source_model_sha256"] = file_hash(target)
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            write_manifest(cache, stage="terrain_similarity_orientation")
            terrain = TerrainModel(root, config)
            _, _, summary = compare_sites(terrain, "Haworth", "wadi_rum", top_k=1)
            self.assertAlmostEqual(summary["median_best_patch_cosine"], 1.0, places=6)
            self.assertIn(
                str(source / "full_context/region_balanced/weights.json"),
                terrain.evidence,
            )
            with self.assertRaises(FileExistsError):
                save_checkpoint(root, source, "full_context", "region_balanced", state)
            with target.open("ab") as stream:
                stream.write(b"changed")
            with self.assertRaisesRegex(
                ValueError, "Unregistered or changed run output"
            ):
                TerrainModel(root, config)

    def test_site_pair_limits_candidates_and_uses_every_lunar_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            terrain = TerrainModel(root, prepared_fixture(root, extra_moon_patch=True))
            matches, _, summary = compare_sites(
                terrain, "Haworth", "Atacama San Pedro", top_k=1
            )
            # earth-a would win an unrestricted ID tie. The requested site is earth-b.
            self.assertEqual(matches.query_id.tolist(), ["moon-a", "moon-c"])
            self.assertEqual(matches.candidate_id.tolist(), ["earth-b", "earth-b"])
            self.assertEqual(summary["moon_patch_count"], 2)
            self.assertEqual(summary["earth_patch_count"], 1)
            self.assertAlmostEqual(summary["median_best_patch_cosine"], 1.0, places=6)

    def test_cli_exports_a_complete_pair_run_and_marks_a_bad_site_run_failed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = prepared_fixture(root)
            # Exercise a standalone module process: no notebook state or project data.
            repository = Path(__file__).resolve().parents[4]
            shutil.copytree(
                repository / "notebooks",
                root / "notebooks",
                ignore=shutil.ignore_patterns(
                    "*.ipynb", "__pycache__", "tests", "weights"
                ),
                dirs_exist_ok=True,
            )
            path = root / "fixture.json"
            path.write_text(json.dumps(asdict(config)), encoding="utf-8")
            command = [
                sys.executable,
                "-m",
                "notebooks.modeling.terrain_similarity.pipeline",
                "--config",
                str(path),
                "--earth-site",
                "wadi_rum",
                "--top-k",
                "1",
                "--no-plots",
            ]
            completed = subprocess.run(
                [*command, "--moon-site", "Haworth"],
                cwd=root,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                completed.returncode, 0, completed.stdout + completed.stderr
            )
            folders = list(
                (root / "data/processed/terrain_similarity_pipeline").iterdir()
            )
            self.assertEqual(len(folders), 1)
            matches = pd.read_csv(folders[0] / "retrieval.csv")
            self.assertEqual(matches.candidate_id.tolist(), ["earth-a"])
            self.assertEqual(
                json.loads((folders[0] / "provenance.json").read_text())["status"],
                "complete",
            )
            failed = subprocess.run(
                [*command, "--moon-site", "unknown"],
                cwd=root,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("Unknown or ambiguous moon site", failed.stderr)
            statuses = [
                json.loads(p.read_text())["status"]
                for p in (root / "data/processed/terrain_similarity_pipeline").glob(
                    "*/provenance.json"
                )
            ]
            self.assertCountEqual(statuses, ["complete", "failed"])

    def test_changed_tensor_and_wrong_body_site_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = prepared_fixture(root)
            terrain = TerrainModel(root, config)
            with self.assertRaisesRegex(ValueError, "Unknown or ambiguous moon site"):
                compare_sites(terrain, "wadi_rum", "Haworth", top_k=1)
            with self.assertRaisesRegex(ValueError, "top_k"):
                compare_sites(terrain, "Haworth", "wadi_rum", top_k=2)
            # Append a byte without changing the registered digest: opening a
            # corrupted tensor must fail before inference, even if NumPy could read it.
            path = root / config.dataset_run / "tensors.npz"
            with path.open("ab") as stream:
                stream.write(b"changed")
            with self.assertRaisesRegex(
                ValueError, "Unregistered or changed run output"
            ):
                compare_sites(terrain, "Haworth", "wadi_rum", top_k=1)

    def test_duplicate_cache_ids_and_malformed_tensor_indices_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = prepared_fixture(root)
            cache = root / config.orientation_run
            path = cache / "embeddings.npz"
            with np.load(path) as archive:
                ids, vectors = archive["patch_ids"].copy(), archive["cnn"].copy()
            ids[0] = ids[1]
            np.savez_compressed(path, patch_ids=ids, cnn=vectors)
            write_manifest(cache)
            with self.assertRaisesRegex(ValueError, "patch IDs"):
                TerrainModel(root, config)
            dataset = root / config.dataset_run
            path = dataset / "patches.csv"
            patches = pd.read_csv(path)
            patches["tensor_index"] = patches.tensor_index.astype(float)
            patches.loc[0, "tensor_index"] = -0.5
            patches.to_csv(path, index=False)
            manifest = json.loads((dataset / "provenance.json").read_text())
            write_manifest(dataset, stage=manifest["stage"], config=manifest["config"])
            with self.assertRaisesRegex(ValueError, "Tensor indices"):
                TerrainModel(root, config)

    def test_saved_cache_aligns_by_patch_id_and_rejects_different_model_lineage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = prepared_fixture(root)
            model = TerrainModel(root, config)
            self.assertEqual(
                model.patches.index.tolist(), ["moon-b", "earth-b", "moon-a", "earth-a"]
            )
            # Corruption here is re-hashed, so lineage checking, not file hashing,
            # must reject a cache belonging to another model.
            cache = root / config.orientation_run
            path = cache / "preprocessing.json"
            metadata = json.loads(path.read_text(encoding="utf-8"))
            metadata["source_model_sha256"] = "0" * 64
            path.write_text(json.dumps(metadata), encoding="utf-8")
            write_manifest(cache)
            with self.assertRaisesRegex(ValueError, "model|lineage"):
                TerrainModel(root, config)

    def test_retrieval_excludes_moon_uses_id_ties_and_does_not_rerank_by_physics(self):
        # Equal cosine scores must favor earth-a even though earth-b is physically closer.
        rows = []
        for patch_id, body, features in [
            ("query", "moon", [10.0, 20.0, 100.0, 0.2, 10.0]),
            ("earth-b", "earth", [10.0, 20.0, 100.0, 0.2, 10.0]),
            ("another-moon", "moon", [10.0, 20.0, 100.0, 0.2, 10.0]),
            ("earth-a", "earth", [14.0, 26.0, 140.0, 0.5, 14.0]),
        ]:
            rows.append(
                dict(
                    zip(
                        [
                            "slope_median_deg",
                            "slope_p90_deg",
                            "central_relief_m",
                            "plane_residual_fraction",
                            "local_sd_median_m",
                        ],
                        features,
                        strict=True,
                    ),
                    patch_id=patch_id,
                    body=body,
                    region=patch_id,
                    fold="train",
                    left=10.0,
                    right=12.0,
                    bottom=20.0,
                    top=22.0,
                    crs_wkt="EPSG:4326",
                )
            )
        patches = pd.DataFrame(rows).set_index("patch_id")
        matches, physical = retrieve_matches(
            patches,
            np.array([[1.0, 0.0]] * 4),
            ("query",),
            np.array([[1.0, 0.0]]),
            2,
        )
        self.assertEqual(matches.candidate_id.tolist(), ["earth-a", "earth-b"])
        self.assertEqual(matches.physical_checks_within_band.tolist(), [0, 5])
        np.testing.assert_allclose(matches.cosine_similarity, [1.0, 1.0])
        np.testing.assert_allclose(
            matches[["longitude", "latitude"]], [[11.0, 21.0], [11.0, 21.0]]
        )
        np.testing.assert_allclose(
            physical.iloc[:5].comparison_band, [1.0, 2.0, 10.0, 0.1, 1.0]
        )
        np.testing.assert_allclose(
            physical.iloc[:5].absolute_difference, [4.0, 6.0, 40.0, 0.3, 4.0]
        )


if __name__ == "__main__":
    unittest.main()
