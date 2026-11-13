"""Checks for app/scripts/export_data.py on a small synthetic inference run."""

import csv
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import export_data  # noqa: E402
from export_data import ExportError, run_export  # noqa: E402

REGION = "A3CLR22_10_Leibnitz_Beta_Plateau"
SLUG = "leibnitz-beta-plateau"
SHARD = f"tensors/{REGION}_960m.npz"
CHANNELS = ["relative_elevation_m", "slope_deg", "roughness_90m", "roughness_330m", "laplacian_per_m"]


def source_row(top_row: int, top_col: int, tensor_index: int, **changes: str) -> dict[str, str]:
    row = {
        "patch_id": f"{REGION}:960:{top_row}:{top_col}", "region": REGION, "size_m": "960", "spacing_m": "30",
        "top_row": str(top_row), "top_col": str(top_col), "center_x": "66420.0", "center_y": "124560.0",
        "tensor_shard": SHARD, "tensor_index": str(tensor_index),
        "slope_median_deg": "8.87", "slope_p90_deg": "12.84", "relative_relief_m": "180.06",
        "predicted_rover_class": "operable", "predicted_human_terrain_class": "caution",
        "rover_probability_operable": "0.80", "rover_probability_marginal": "0.19", "rover_probability_non_operable": "0.01",
        "human_probability_easy": "0.0", "human_probability_caution": "0.97", "human_probability_unsuitable": "0.03",
        "direct_human_terrain_rule": "caution", "cnn_agrees_with_direct_human_rule": "True",
    }
    for axis in export_data.CROSSING_AXES:
        row[f"probability_{axis}"] = "0.9"
        row[f"predicted_{axis}"] = "True"
    row.update(changes)
    return row


def synthetic_grids() -> np.ndarray:
    """Two patches, five channels. Patch p, channel c, row r, column k has a distinct value."""
    grids = np.zeros((2, 5, 32, 32), dtype=np.float32)
    rows, cols = np.meshgrid(np.arange(32), np.arange(32), indexing="ij")
    for patch in range(2):
        grids[patch, 0] = -100 + patch * 50 + rows * 2.04 + cols * 0.13  # relative elevation, metres
        grids[patch, 1] = patch * 5 + rows * 0.31 + cols * 0.07  # slope, degrees
        grids[patch, 2:] = 999  # channels the app must not read
    return grids


class ExportCase(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.input_dir = Path(temporary.name) / "inputs"
        self.output_dir = Path(temporary.name) / "out"
        self.run_dir = self.input_dir / export_data.STAGE / export_data.DEFAULT_RUN_ID
        (self.run_dir / "tensors").mkdir(parents=True)
        (self.run_dir / "provenance.json").write_text(json.dumps({"config": {"claim_boundary": "test claim"}}))
        self.grids = synthetic_grids()
        self.write_tensors(self.grids)
        # The CSV order differs from the tensor order on purpose.
        self.write_rows([source_row(32, 64, 1), source_row(32, 32, 0)])

    def write_tensors(self, grids: np.ndarray) -> None:
        np.savez(self.run_dir / SHARD, physical=grids, channels=np.array(CHANNELS))

    def write_rows(self, rows: list[dict[str, str]]) -> None:
        with (self.run_dir / "predictions.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def export(self, **options) -> dict:
        options.setdefault("region_slugs", [SLUG])  # the synthetic run holds one region
        return run_export(self.input_dir, self.output_dir, **options)

    def patches(self) -> dict:
        return json.loads((self.output_dir / "patches" / f"{SLUG}.json").read_text(encoding="utf-8"))


class MetadataTests(ExportCase):
    def test_source_values_are_preserved(self) -> None:
        regions = self.export()
        entry = regions["regions"][0]
        self.assertEqual((entry["slug"], entry["source_id"], entry["exported_patch_count"]), (SLUG, REGION, 2))
        self.assertEqual(regions["source"]["run_id"], export_data.DEFAULT_RUN_ID)
        patch = self.patches()["patches"][0]
        self.assertEqual(patch["source_id"], f"{REGION}:960:32:64")
        self.assertEqual(patch["slug"], "r32-c64")
        self.assertEqual(patch["tensor"], {"shard": SHARD, "index": 1})
        self.assertEqual(patch["rover"], {"class": "operable", "probabilities": {"operable": 0.8, "marginal": 0.19, "non_operable": 0.01}})
        self.assertEqual(patch["walking"]["class"], "caution")
        self.assertEqual(patch["crossing"]["east_west"], {"predicted": True, "probability": 0.9})
        self.assertEqual(patch["physical"]["relative_relief_m"], 180.06)

    def test_patch_selection_exports_only_that_patch(self) -> None:
        regions = self.export(region_slugs=[SLUG], patch_ids=[f"{REGION}:960:32:32"])
        self.assertEqual(regions["regions"][0]["exported_patch_count"], 1)
        self.assertEqual(regions["regions"][0]["source_patch_count"], 2)
        self.assertEqual([patch["slug"] for patch in self.patches()["patches"]], ["r32-c32"])
        with self.assertRaisesRegex(ExportError, "Unknown patch ID"):
            self.export(region_slugs=[SLUG], patch_ids=["not-a-patch"])

    def test_duplicate_patch_id_is_rejected(self) -> None:
        self.write_rows([source_row(32, 32, 0), source_row(32, 32, 1)])
        with self.assertRaisesRegex(ExportError, "Duplicate patch_id"):
            self.export()

    def test_unknown_class_and_region_are_rejected(self) -> None:
        self.write_rows([source_row(32, 32, 0, predicted_rover_class="fine")])
        with self.assertRaisesRegex(ExportError, "unknown class 'fine'"):
            self.export()
        self.write_rows([source_row(32, 32, 0, region="Somewhere_Else")])
        with self.assertRaisesRegex(ExportError, "unsupported region"):
            self.export()

    def test_windows_separators_are_normalized_and_outside_paths_rejected(self) -> None:
        self.write_rows([source_row(32, 32, 0, tensor_shard=SHARD.replace("/", "\\"))])
        self.export()
        self.assertEqual(self.patches()["patches"][0]["tensor"]["shard"], SHARD)
        self.write_rows([source_row(32, 32, 0, tensor_shard="..\\other_run\\tensors\\x.npz")])
        with self.assertRaisesRegex(ExportError, "leaves the selected run"):
            self.export()


class GridTests(ExportCase):
    def decode(self, patch: dict, channel: int) -> np.ndarray:
        data = (self.output_dir / "grids" / f"{SLUG}.bin").read_bytes()
        start = patch["grid_offset"] + channel * 32 * 32 * 2
        return np.array(struct.unpack("<1024h", data[start:start + 2048])).reshape(32, 32) / 10

    def test_grids_follow_the_tensor_index_within_tolerance(self) -> None:
        self.export()
        document = self.patches()
        self.assertEqual(document["grid"]["byte_length"], 2 * 4096)
        self.assertEqual([c["name"] for c in document["grid"]["channels"]], ["relative_elevation_m", "slope_deg"])
        for patch in document["patches"]:
            source = self.grids[patch["tensor"]["index"]]
            for channel in (0, 1):
                self.assertLessEqual(np.abs(self.decode(patch, channel) - source[channel]).max(), 0.05 + 1e-6)
        first = document["patches"][0]  # CSV row 0 points at tensor index 1
        self.assertAlmostEqual(self.decode(first, 0)[3, 5], float(self.grids[1, 0, 3, 5]), delta=0.05)

    def test_value_outside_int16_is_rejected(self) -> None:
        self.grids[0, 0, 0, 0] = 3276.8
        self.write_tensors(self.grids)
        with self.assertRaisesRegex(ExportError, "does not fit a signed 16-bit"):
            self.export()

    def test_non_finite_value_is_rejected(self) -> None:
        self.grids[1, 1, 4, 4] = np.nan
        self.write_tensors(self.grids)
        with self.assertRaisesRegex(ExportError, "non-finite"):
            self.export()

    def test_wrong_shape_and_missing_file_are_rejected(self) -> None:
        self.write_tensors(self.grids[:, :, :16, :])
        with self.assertRaisesRegex(ExportError, "unexpected tensor shape"):
            self.export()
        (self.run_dir / SHARD).unlink()
        with self.assertRaisesRegex(ExportError, "Missing tensor file"):
            self.export()

    def test_tensor_index_outside_the_file_is_rejected(self) -> None:
        self.write_rows([source_row(32, 32, 7)])
        with self.assertRaisesRegex(ExportError, "tensor index 7 is outside"):
            self.export()


if __name__ == "__main__":
    unittest.main()
