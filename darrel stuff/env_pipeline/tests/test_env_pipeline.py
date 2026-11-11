"""Standalone CSV/YAML behavior; all numerical screening examples are fictional."""
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import env_pipeline as engine


def metric(column, upper, direction="higher", gate=None):
    return dict(column=column, unit="fictional_unit", role="score", evidence_family=column,
                multiplier=1, preference=dict(direction=direction, lower=0, upper=upper), hard_gate=gate)


def config():
    result = dict(schema=1, body="Moon", name="fictional_test", metadata_columns=[], domains={
        k: dict(include_in_score=False, multiplier=1, metrics=[]) for k in engine.SCORES})
    result["domains"]["solar_illumination"].update(include_in_score=True, metrics=[metric("sun", 1, gate=dict(operator="ge", threshold=.5))])
    result["domains"]["uv"].update(include_in_score=True, metrics=[metric("uv", 10, direction="lower")])
    return result


def evaluate(rows, cfg=None):
    return engine.assess(rows, cfg or config(), "test_config_hash")


class StandalonePipelineTests(unittest.TestCase):
    def test_gate_first_and_missing_soft(self):
        rows = [dict(id="a", sun=".8", uv="2"), dict(id="b", sun=".4", uv="0"),
                dict(id="c", sun="", uv="2"), dict(id="d", sun=".8", uv="")]
        result = evaluate(rows)
        self.assertEqual(result[0]["final_rec_score"], 80)
        self.assertEqual(result[1]["hard_gate_status"], "Failed")
        self.assertEqual(result[2]["hard_gate_status"], "Unknown")
        self.assertEqual(result[3]["hard_gate_status"], "Passed")
        self.assertTrue(all(r["final_rec_score"] == "" for r in result[1:]))

    def test_failure_dominates_unknown(self):
        cfg = config()
        cfg["domains"]["uv"]["metrics"][0]["hard_gate"] = dict(operator="le", threshold=None)
        self.assertEqual(evaluate([dict(id="a", sun=".4", uv="2")], cfg)[0]["hard_gate_status"], "Failed")

    def test_domain_multipliers_are_relative_importance(self):
        cfg = config(); cfg["domains"]["solar_illumination"]["multiplier"] = 3
        self.assertAlmostEqual(evaluate([dict(id="a", sun=".6", uv="2")], cfg)[0]["final_rec_score"], 65)

    def test_metric_multipliers(self):
        cfg = config(); cfg["domains"]["uv"]["include_in_score"] = False
        second = metric("other", 1); second["multiplier"] = 3
        cfg["domains"]["solar_illumination"]["metrics"].append(second)
        self.assertAlmostEqual(evaluate([dict(id="a", sun=".6", other=".9", uv="2")], cfg)[0]["final_rec_score"], 82.5)

    def test_zero_score_can_rank(self):
        cfg = config(); cfg["domains"]["solar_illumination"]["metrics"][0]["hard_gate"]["threshold"] = 0
        row = evaluate([dict(id="a", sun="0", uv="10")], cfg)[0]
        self.assertEqual(row["final_rec_score"], 0)
        self.assertEqual(row["rank"], 1)

    def test_unconfigured_threshold_and_multiplier_are_unknown(self):
        cfg = config(); cfg["domains"]["solar_illumination"]["metrics"][0]["hard_gate"]["threshold"] = None
        self.assertEqual(evaluate([dict(id="a", sun=".8", uv="2")], cfg)[0]["hard_gate_status"], "Unknown")
        cfg = config(); cfg["domains"]["uv"]["multiplier"] = None
        self.assertEqual(evaluate([dict(id="a", sun=".8", uv="2")], cfg)[0]["final_rec_score"], "")

    def test_empty_gate_cannot_pass(self):
        cfg = config(); cfg["domains"]["solar_illumination"]["metrics"][0]["hard_gate"] = None
        self.assertEqual(evaluate([dict(id="a", sun=".8", uv="2")], cfg)[0]["hard_gate_status"], "Unknown")

    def test_context_cannot_be_scored_or_gated(self):
        cfg = config(); item = cfg["domains"]["uv"]["metrics"][0]
        item["role"] = "context"
        with self.assertRaisesRegex(ValueError, "context cannot"):
            engine.validate_config(cfg)
        item["preference"] = None; item["hard_gate"] = dict(operator="le", threshold=1)
        with self.assertRaisesRegex(ValueError, "context cannot"):
            engine.validate_config(cfg)

    def test_context_values_retained_without_scores(self):
        cfg = config(); cfg["domains"]["uv"].update(include_in_score=False, metrics=[dict(column="dust_current", role="context", unit="e/s")])
        row = evaluate([dict(id="a", sun=".8", dust_current="-3")], cfg)[0]
        self.assertEqual(row["uv_score_status"], "Context_only")
        self.assertEqual(row["uv_score"], "")
        self.assertEqual(json.loads(row["score_details"])[-1]["value"], -3)

    def test_preferred_range_and_clipping(self):
        pref = dict(direction="target_range", lower=0, upper=10, preferred_lower=3, preferred_upper=7)
        self.assertEqual(engine.utility(5, pref), 1)
        self.assertEqual(engine.utility(-1, pref), 0)
        self.assertAlmostEqual(engine.utility(1.5, pref), .5)
        self.assertAlmostEqual(engine.utility(8.5, pref), .5)
        self.assertIsNone(engine.utility(1, dict(direction="higher", lower=None, upper=10)))

    def test_between_gate_includes_boundaries(self):
        gate = dict(operator="between", lower=1, upper=3)
        self.assertEqual(engine.hard_check(1, gate)[0], "Passed")
        self.assertEqual(engine.hard_check(3, gate)[0], "Passed")
        self.assertEqual(engine.hard_check(4, gate)[0], "Failed")

    def test_invalid_configuration_is_rejected(self):
        for value in [0, -1, True, "2", float("inf")]:
            with self.subTest(multiplier=value):
                cfg = config(); cfg["domains"]["uv"]["multiplier"] = value
                with self.assertRaises(ValueError): engine.validate_config(cfg)
        cfg = config(); cfg["domains"]["terrain"] = dict(include_in_score=False, multiplier=1, metrics=[])
        with self.assertRaisesRegex(ValueError, "eight environmental"):
            engine.validate_config(cfg)

    def test_shared_evidence_family_is_not_double_weighted(self):
        cfg = config(); cfg["domains"]["uv"]["metrics"][0]["evidence_family"] = "sun"
        with self.assertRaisesRegex(ValueError, "distinct evidence_family"):
            engine.validate_config(cfg)

    def test_yaml_rejects_duplicates_unsafe_tags_and_typos(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.yml"
            for text in ["schema: 1\nschema: 2\n", "!!python/object/apply:os.getcwd []", "schema: 1\nbody: Moon\nwrong_setting: 2\n"]:
                p.write_text(text)
                with self.assertRaises((ValueError, yaml.YAMLError)):
                    engine.load_config(p)

    def test_csv_validation_and_optional_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sites.csv"
            p.write_text("id,sun,uv\na,.8,2\n")
            self.assertEqual(len(engine.read_csv(p, config())), 1)
            for text in ["id,sun,uv\na,NaN,2\n", "id,sun,uv\na,bad,2\n", "id,sun,uv\na,.8,2\na,.8,2\n", "id,sun,uv,typo\na,.8,2,1\n", "id,sun,sun\na,.8,.8\n", "id,sun,uv\na,.8\n"]:
                p.write_text(text)
                with self.assertRaises(ValueError): engine.read_csv(p, config())
            p.write_text("id,sun,uv\na,2,2\n")
            cfg = config(); cfg["domains"]["solar_illumination"]["metrics"][0]["maximum"] = 1
            with self.assertRaisesRegex(ValueError, "physical input bounds"):
                engine.read_csv(p, cfg)

    def test_time_pair_and_rank_groups(self):
        for start, stop in [("2023-01-01T00:00:00Z", ""), ("2023-01-01", "2023-02-01")]:
            with self.assertRaises(ValueError): engine.time_window(start, stop)
        rows = [dict(id="b", sun=".8", uv="2"), dict(id="a", sun=".8", uv="2"),
                dict(id="dated", sun=".8", uv="2", start_utc="2023-01-01T00:00:00Z", stop_utc="2023-02-01T00:00:00Z")]
        result = evaluate(rows)
        self.assertEqual([r["rank"] for r in result], [2, 1, 1])
        self.assertEqual(result[0]["time_mode"], "unspecified")

    def test_optional_time_requirement_withholds_score(self):
        cfg = config(); cfg["domains"]["uv"]["metrics"][0]["requires_time_window"] = True
        self.assertEqual(evaluate([dict(id="a", sun=".8", uv="2")], cfg)[0]["final_rec_score"], "")

    def test_no_sidecar_is_read(self):
        cfg = config(); cfg["metadata_columns"] = ["evidence_ref"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / "config.yml").write_text(yaml.safe_dump(cfg))
            (root / "sites.csv").write_text("id,sun,uv,evidence_ref\na,.8,2,DOES_NOT_EXIST.json\n")
            result = engine.run(root / "sites.csv", root / "results.csv", root / "config.yml")
            self.assertEqual(result[0]["final_rec_score"], 80)
            self.assertEqual({p.name for p in root.iterdir()}, {"sites.csv", "config.yml", "results.csv"})

    def test_output_protection_and_config_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); cfg = root / "config.yml"; cfg.write_text(yaml.safe_dump(config()))
            source = root / "sites.csv"; source.write_text("id,sun,uv\na,.8,2\n")
            output = root / "results.csv"
            rows = engine.run(source, output, cfg)
            self.assertEqual(rows[0]["config_sha256"], hashlib.sha256(cfg.read_bytes()).hexdigest())
            with self.assertRaises(FileExistsError): engine.run(source, output, cfg)
            with self.assertRaises(ValueError): engine.run(source, source, cfg, overwrite=True)

    def test_isolated_copy_needs_only_script_yaml_and_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); shutil.copy2(HERE / "env_pipeline.py", root / "env_pipeline.py")
            (root / "config.yml").write_text(yaml.safe_dump(config()))
            (root / "sites.csv").write_text("id,sun,uv\na,.8,2\n")
            result = subprocess.run([sys.executable, "-I", str(root / "env_pipeline.py"), "--input", str(root / "sites.csv"), "--output", str(root / "results.csv")], cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with (root / "results.csv").open(newline="") as handle:
                reader = csv.DictReader(handle); self.assertNotIn("terrain_score", reader.fieldnames)
                self.assertEqual(float(next(reader)["final_rec_score"]), 80)
            self.assertEqual({p.name for p in root.iterdir()}, {"env_pipeline.py", "config.yml", "sites.csv", "results.csv"})

    def test_default_config_has_no_external_references_or_adopted_limits(self):
        cfg, _ = engine.load_config(HERE / "config.yml")
        self.assertEqual(set(cfg["domains"]), set(engine.SCORES))
        self.assertTrue(all(d["multiplier"] is None for d in cfg["domains"].values()))
        for d in cfg["domains"].values():
            for m in d["metrics"]:
                if m.get("hard_gate"): self.assertIsNone(m["hard_gate"].get("threshold"))


if __name__ == "__main__":
    unittest.main()
