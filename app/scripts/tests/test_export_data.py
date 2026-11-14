"""Checks for app/scripts/export_data.py on a small synthetic pipeline run."""

import csv
import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import export_data  # noqa: E402
from export_data import CHECKS, ExportError, run_export  # noqa: E402

REGION = "A3CLR22_10_Leibnitz_Beta_Plateau"
SLUG = "leibnitz-beta-plateau"
TERRAIN_RUN = "20261112T120422201915Z_101366"
DATASET_RUN = "20261101T064233918547Z_4a05ac"
PIPELINE_RUN = "20261114T000000000000Z_test00"
SHARD = f"tensors/{REGION}_960m.npz"
EARTH_SHARD = "tensors/earth.npz"
CHANNELS = ["relative_elevation_m", "slope_deg", "roughness_90m", "roughness_330m", "laplacian_per_m"]
SITES = ("death_valley", "wadi_rum")
ENVIRONMENT_COLUMNS = [
    "ID", "operations_thermal_score", "operations_soil_score", "survival_radiation_score",
    "operations_status", "survival_status", "operations_fail_reason", "survival_fail_reason",
    "operations_score", "survival_score",
]


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


def tile_of(row: dict[str, str]) -> str:
    return f"{REGION}:{int(row['top_col']) * 30}:{-int(row['top_row']) * 30}"


def similarity_id(row: dict[str, str]) -> str:
    return f"{REGION}:full_context:{int(row['top_row']) + 16}:{int(row['top_col']) + 16}:960"


# Mirrors env_pipeline.py's config interface: load_config returns (config, hash), and assessment_config gives one
# assessment's domains. Operations uses thermal and dust, survival uses radiation.
FAKE_SCORER = """import ast
from pathlib import Path

ASSESSMENTS = ("operations", "survival")
USES = {"operations": ("thermal", "dust"), "survival": ("radiation",)}


def load_config(path):
    return ast.literal_eval(Path(path).read_text()), "hash"


def assessment_config(config, assessment):
    return {"domains": {name: d for name, d in config["domains"].items() if name in USES[assessment]}}
"""


def synthetic_grids(count: int = 2, channels: int = 5) -> np.ndarray:
    """Patch p, channel c, row r, column k has a distinct value."""
    grids = np.zeros((count, channels, 32, 32), dtype=np.float32)
    rows, cols = np.meshgrid(np.arange(32), np.arange(32), indexing="ij")
    for patch in range(count):
        grids[patch, 0] = -100 + patch * 50 + rows * 2.04 + cols * 0.13  # relative elevation, metres
        grids[patch, 1] = patch * 5 + rows * 0.31 + cols * 0.07  # slope, degrees
        grids[patch, 2:] = 999  # channels the app must not read
    return grids


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def environment_row(scenario_id: str, **changes: str) -> dict[str, str]:
    row = {"ID": scenario_id, "operations_thermal_score": "37.0", "operations_soil_score": "0",
           "survival_radiation_score": "55.5", "operations_status": "Pass", "survival_status": "Pass",
           "operations_fail_reason": "", "survival_fail_reason": "", "operations_score": "42.82",
           "survival_score": "51.81"}
    row.update(changes)
    return row


class ExportCase(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        processed = self.root / "data" / "processed"
        self.run_dir = processed / export_data.TERRAIN_STAGE / TERRAIN_RUN
        self.dataset_dir = processed / "terrain_learning_readiness" / DATASET_RUN
        self.pipeline = processed / "moon_pipeline" / PIPELINE_RUN
        self.output_dir = self.root / "out"
        for folder in (self.run_dir / "tensors", self.dataset_dir / "tensors", self.pipeline):
            folder.mkdir(parents=True)
        (self.run_dir / "provenance.json").write_text(json.dumps({"config": {"claim_boundary": "test claim"}}))
        (self.pipeline / "provenance.json").write_text(json.dumps({
            "stage": "moon_pipeline", "status": "complete",
            "config": {
                "terrain_run": f"data/processed/{export_data.TERRAIN_STAGE}/{TERRAIN_RUN}",
                "environment_input": "env/sample_input.csv", "top_k_per_site": 1,
                "similarity": {"dataset_run": f"data/processed/terrain_learning_readiness/{DATASET_RUN}"},
            },
        }))
        (self.pipeline / "summary.json").write_text(json.dumps({
            "earth_sites": list(SITES), "top_k_per_site": 1, "environment_scope": "region",
            "caveat": "test caveat", "similarity_model": {"view": "full_context"},
        }))
        (self.root / "env").mkdir()
        (self.root / "env" / "sample_input.csv").write_bytes(b"id,start_utc\r\neda_001,2009-01-28T20:34:14Z\r\n")
        self.grids = synthetic_grids()
        self.write_tensors(self.grids)
        self.earth = synthetic_grids(2, 3)
        np.savez(self.dataset_dir / EARTH_SHARD, physical=self.earth, valid=np.ones_like(self.earth, dtype=bool))
        write_csv(self.dataset_dir / "patches.csv", [
            {"patch_id": f"{site}:natural_screen:0:{i}:960", "body": "earth", "region": site,
             "shard": EARTH_SHARD, "tensor_index": str(i)} for i, site in enumerate(SITES)
        ] + [{"patch_id": "moon-row", "body": "moon", "region": REGION, "shard": "x", "tensor_index": "0"}])
        self.write_environment([
            environment_row("eda_001"),
            environment_row("eda_008", survival_status="Unknown", survival_score="",
                            survival_fail_reason="radiation: missing | uv: missing"),
            environment_row("apollo_11_mare_tranquillitatis_assumed"),
            environment_row("synthetic_001"),
            environment_row("dummy_001"),
        ])
        # The CSV order differs from the tensor order on purpose.
        self.write_rows([source_row(32, 64, 1), source_row(32, 32, 0)])

    def write_tensors(self, grids: np.ndarray) -> None:
        np.savez(self.run_dir / SHARD, physical=grids, channels=np.array(CHANNELS))

    def write_environment(self, rows: list[dict[str, str]], columns: list[str] | None = None) -> None:
        write_csv(self.pipeline / "environment.csv", rows, columns or ENVIRONMENT_COLUMNS)

    def write_rows(self, rows: list[dict[str, str]], *, matches: bool = True) -> None:
        """Write Hanxi's predictions plus matching moon_tiles, earth_matches and physical_comparison."""
        write_csv(self.run_dir / "predictions.csv", rows)
        unique = list({row["patch_id"]: row for row in rows}.values())
        write_csv(self.pipeline / "moon_tiles.csv", [
            {"tile_id": tile_of(row), "region": REGION, "similarity_full_context_patch_id": similarity_id(row),
             "walkability_patch_id": row["patch_id"]} for row in unique
        ])
        match_rows, physical_rows = [], []
        for row in unique if matches else []:
            for rank, (index, site) in enumerate(((1, SITES[1]), (0, SITES[0])), 1):
                candidate = f"{site}:natural_screen:0:{index}:960"
                within = [True, True, False, True, rank == 1]
                match_rows.append({
                    "tile_id": tile_of(row), "query_id": similarity_id(row), "site_rank": "1",
                    "overall_rank": str(rank), "candidate_id": candidate, "earth_region": site,
                    "cosine_similarity": str(0.97 - rank * 0.1), "latitude": "29.5", "longitude": str(35.4 - index),
                    "physical_checks_within_band": str(sum(within)),
                })
                for i, feature in enumerate(CHECKS):
                    physical_rows.append({
                        "tile_id": tile_of(row), "candidate_id": candidate, "feature": feature,
                        "measurement": f"Label {feature}", "moon": str(1.0 + i), "earth": str(2.0 + i + index),
                        "comparison_band": "1.0", "within_band": str(within[i]),
                    })
        match_fields = ["tile_id", "query_id", "site_rank", "overall_rank", "candidate_id", "earth_region",
                        "cosine_similarity", "latitude", "longitude", "physical_checks_within_band"]
        write_csv(self.pipeline / "earth_matches.csv", match_rows, match_fields)
        write_csv(self.pipeline / "physical_comparison.csv", physical_rows,
                  ["tile_id", "candidate_id", "feature", "measurement", "moon", "earth", "comparison_band",
                   "within_band"])

    def export(self, **options) -> dict:
        options.setdefault("region_slugs", [SLUG])  # the synthetic run holds one region
        return run_export(self.root, self.pipeline, self.output_dir, **options)

    def read(self, name: str) -> dict:
        return json.loads((self.output_dir / name).read_text(encoding="utf-8"))

    def patches(self) -> dict:
        return self.read(f"patches/{SLUG}.json")


class MetadataTests(ExportCase):
    def test_source_values_are_preserved(self) -> None:
        regions = self.export()
        entry = regions["regions"][0]
        self.assertEqual((entry["slug"], entry["source_id"], entry["exported_patch_count"]), (SLUG, REGION, 2))
        self.assertEqual(regions["source"]["run_id"], TERRAIN_RUN)
        self.assertEqual(regions["pipeline"]["run_id"], PIPELINE_RUN)
        patch = self.patches()["patches"][0]
        self.assertEqual(patch["source_id"], f"{REGION}:960:32:64")
        self.assertEqual(patch["tile_id"], f"{REGION}:1920:-960")
        self.assertEqual(patch["similarity_patch_id"], f"{REGION}:full_context:48:80:960")
        self.assertEqual(patch["slug"], "r32-c64")
        self.assertEqual(patch["tensor"], {"shard": SHARD, "index": 1})
        self.assertEqual(patch["rover"], {"class": "operable", "probabilities": {"operable": 0.8, "marginal": 0.19, "non_operable": 0.01}})
        self.assertEqual(patch["walking"]["class"], "caution")
        self.assertEqual(patch["crossing"]["east_west"], {"predicted": True, "probability": 0.9})
        self.assertEqual(patch["physical"]["relative_relief_m"], 180.06)

    def test_region_extent_covers_every_tile(self) -> None:
        extent = self.export()["regions"][0]["extent_m"]
        patches = self.patches()["patches"]
        xs = [patch["center_x_m"] for patch in patches]
        ys = [patch["center_y_m"] for patch in patches]
        self.assertEqual(extent, {"xmin": min(xs) - 480, "xmax": max(xs) + 480, "ymin": min(ys) - 480, "ymax": max(ys) + 480})
        self.assertLess(extent["xmin"], extent["xmax"])

    def test_patch_selection_exports_only_that_patch(self) -> None:
        regions = self.export(region_slugs=[SLUG], patch_ids=[f"{REGION}:960:32:32"])
        self.assertEqual(regions["regions"][0]["exported_patch_count"], 1)
        self.assertEqual(regions["regions"][0]["source_patch_count"], 2)
        self.assertEqual([patch["slug"] for patch in self.patches()["patches"]], ["r32-c32"])
        self.assertEqual(list(self.read(f"analogs/{SLUG}.json")["tiles"]), ["r32-c32"])
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
    def decode(self, file: str, offset: int, channel: int) -> np.ndarray:
        data = (self.output_dir / file).read_bytes()
        start = offset + channel * 32 * 32 * 2
        return np.array(struct.unpack("<1024h", data[start:start + 2048])).reshape(32, 32) / 10

    def test_grids_follow_the_tensor_index_within_tolerance(self) -> None:
        self.export()
        document = self.patches()
        self.assertEqual(document["grid"]["byte_length"], 2 * 4096)
        self.assertEqual([c["name"] for c in document["grid"]["channels"]], ["relative_elevation_m", "slope_deg"])
        for patch in document["patches"]:
            source = self.grids[patch["tensor"]["index"]]
            for channel in (0, 1):
                decoded = self.decode(f"grids/{SLUG}.bin", patch["grid_offset"], channel)
                self.assertLessEqual(np.abs(decoded - source[channel]).max(), 0.05 + 1e-6)
        first = document["patches"][0]  # CSV row 0 points at tensor index 1
        self.assertAlmostEqual(self.decode(f"grids/{SLUG}.bin", first["grid_offset"], 0)[3, 5],
                               float(self.grids[1, 0, 3, 5]), delta=0.05)

    def test_earth_grids_follow_the_prepared_dataset(self) -> None:
        self.export()
        earth = self.read("earth/candidates.json")
        self.assertEqual(earth["grid"]["byte_length"], 2 * 4096)
        for candidate in earth["candidates"]:
            index = int(candidate["id"].split(":")[3])
            for channel in (0, 1):
                decoded = self.decode("earth/grids.bin", candidate["grid_offset"], channel)
                self.assertLessEqual(np.abs(decoded - self.earth[index, channel]).max(), 0.05 + 1e-6)

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

    def test_wrong_shape_missing_file_and_bad_index_are_rejected(self) -> None:
        self.write_tensors(self.grids[:, :, :16, :])
        with self.assertRaisesRegex(ExportError, "unexpected tensor shape"):
            self.export()
        (self.run_dir / SHARD).unlink()
        with self.assertRaisesRegex(ExportError, "Missing tensor file"):
            self.export()
        self.write_tensors(self.grids)
        self.write_rows([source_row(32, 32, 7)])
        with self.assertRaisesRegex(ExportError, "tensor index 7 is outside"):
            self.export()


class AnalogTests(ExportCase):
    def test_matches_keep_rank_cosine_candidate_and_checks(self) -> None:
        self.export()
        analogs = self.read(f"analogs/{SLUG}.json")
        earth = self.read("earth/candidates.json")
        self.assertEqual(analogs["candidate_pool"]["sites"], list(SITES))
        tile = analogs["tiles"]["r32-c32"]
        self.assertEqual(tile["query_id"], f"{REGION}:full_context:48:48:960")
        self.assertEqual(tile["moon_checks"], [1.0, 2.0, 3.0, 4.0, 5.0])
        first, second = tile["matches"]
        self.assertEqual((first["overall_rank"], first["cosine"]), (1, 0.87))
        self.assertEqual(earth["candidates"][first["candidate"]]["id"], "wadi_rum:natural_screen:0:1:960")
        self.assertEqual(earth["candidates"][first["candidate"]]["checks"], [3.0, 4.0, 5.0, 6.0, 7.0])
        self.assertEqual(first["within"], [True, True, False, True, True])
        self.assertEqual(second["within"][4], False)
        self.assertEqual([c["label"] for c in earth["checks"]][0], "Label slope_median_deg")

    def test_a_tile_without_matches_is_left_out(self) -> None:
        self.write_rows([source_row(32, 32, 0)], matches=False)
        regions = self.export()
        self.assertEqual(regions["regions"][0]["patches_with_analogs"], 0)
        self.assertEqual(self.read(f"analogs/{SLUG}.json")["tiles"], {})

    def test_missing_physical_checks_and_bad_counts_are_rejected(self) -> None:
        path = self.pipeline / "physical_comparison.csv"
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExportError, "missing physical checks"):
            self.export()
        self.write_rows([source_row(32, 32, 0)])
        path = self.pipeline / "earth_matches.csv"
        path.write_text(path.read_text(encoding="utf-8").replace(",29.5,34.4,4", ",29.5,34.4,5"), encoding="utf-8")
        with self.assertRaisesRegex(ExportError, "check count disagrees"):
            self.export()


class EnvironmentTests(ExportCase):
    def test_scenarios_exclude_test_rows_and_keep_blank_and_zero(self) -> None:
        regions = self.export()
        self.assertEqual(regions["environment_file"], "environment.json")
        environment = self.read("environment.json")
        self.assertEqual([s["id"] for s in environment["scenarios"]],
                         ["eda_001", "eda_008", "apollo_11_mare_tranquillitatis_assumed"])
        first, unknown, apollo = environment["scenarios"]
        self.assertEqual((first["terrain_region"], first["evidence"]), (REGION, "measured_maps"))
        self.assertEqual(first["operations"]["domains"][1], {"name": "soil", "label": "Soil", "score": 0.0})
        self.assertEqual((unknown["survival"]["status"], unknown["survival"]["score"]), ("Unknown", None))
        self.assertEqual(unknown["survival"]["fail_reasons"], ["radiation: missing", "uv: missing"])
        self.assertEqual((unknown["terrain_region"], unknown["evidence"]), (None, "assumed"))
        self.assertEqual((apollo["kind"], apollo["name"]), ("apollo", "Apollo 11 · Mare Tranquillitatis"))

    def test_sample_input_is_copied_with_lf_endings_and_its_hash(self) -> None:
        # The source has CRLF, as in a Windows checkout. The copy must match what a clean clone holds.
        self.export()
        sample = self.read("environment.json")["sample_input"]
        written = (self.output_dir / sample["file"]).read_bytes()
        self.assertEqual(written, (self.root / "env" / "sample_input.csv").read_bytes().replace(b"\r\n", b"\n"))
        self.assertEqual(sample["sha256"], hashlib.sha256(written).hexdigest())

    def write_scorer(self, domains: dict) -> None:
        """A stand-in scorer with the real one's config interface, written with CRLF like a Windows checkout."""
        scorer = self.root / export_data.SCORER
        scorer.parent.mkdir(parents=True, exist_ok=True)
        scorer.write_bytes(FAKE_SCORER.encode().replace(b"\n", b"\r\n"))
        (self.root / export_data.DEFAULT_SCORER_CONFIG).write_bytes(repr({"domains": domains}).encode() + b"\r\n")

    def test_scorer_hashes_match_the_published_files(self) -> None:
        self.write_scorer({})
        self.export()
        files = self.read("environment.json")["upload_files"]
        self.assertEqual([entry["name"] for entry in files],
                         ["env_pipeline.py", "config.yml", "environment_data.py", "score_upload.py"])
        for entry in files:
            written = (self.output_dir / entry["file"]).read_bytes()
            self.assertNotIn(b"\r\n", written, entry["name"])
            self.assertEqual(entry["sha256"], hashlib.sha256(written).hexdigest(), entry["name"])

    def test_hard_gates_follow_the_effective_config(self) -> None:
        gate = {"operator": "below_threshold", "threshold": 1.0}
        self.write_scorer({
            # Toggle on but no threshold defined: nothing can fail. Operations uses thermal and dust.
            "thermal": {"hard_gates_enabled": True, "metrics": [{"hard_gate": None}]},
            # Threshold defined but toggle off.
            "dust": {"hard_gates_enabled": False, "metrics": [{"hard_gate": gate}]},
            # Threshold defined and toggle on: survival can fail.
            "radiation": {"hard_gates_enabled": True, "metrics": [{"hard_gate": gate}]},
        })
        self.export()
        self.assertEqual(self.read("environment.json")["hard_gates"], {"operations": False, "survival": True})

    def test_hard_gates_are_null_without_the_scorer(self) -> None:
        self.export()
        self.assertIsNone(self.read("environment.json")["hard_gates"])

    def test_current_team_config_has_every_gate_off(self) -> None:
        # Guards the "gates off" label against a config change. Update this when the team switches gates on.
        repo = Path(__file__).resolve().parents[3]
        if not (repo / export_data.SCORER).is_file():
            self.skipTest("scorer not in this checkout")
        self.assertEqual(export_data.hard_gates(repo, None), {"operations": False, "survival": False})

    def test_old_format_and_unknown_ids_are_rejected(self) -> None:
        self.write_environment([{"ID": "eda_001", "final_habitability_score": "50"}],
                               ["ID", "final_habitability_score"])
        with self.assertRaisesRegex(ExportError, "old single-score format"):
            self.export()
        self.write_environment([environment_row("eda_099")])
        with self.assertRaisesRegex(ExportError, "Unknown environment ID 'eda_099'"):
            self.export()


if __name__ == "__main__":
    unittest.main()
