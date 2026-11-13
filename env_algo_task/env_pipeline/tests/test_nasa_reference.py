"""Reference policy and new domain; fictional numbers never validate lunar safety."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import env_pipeline as engine
from test_env_pipeline import config


class NasaReferenceTests(unittest.TestCase):
    def reference(self):
        return engine.load_config(HERE / "config_nasa_reference.yml")[0]

    def test_old_eight_domain_configs_still_work(self):
        cfg = config()
        cfg["domains"].pop("communications_geometry", None)
        result = engine.assess([dict(id="a", sun=".8", uv="2")], cfg, "hash")[0]
        self.assertEqual(result["final_rec_score"], 80)
        self.assertEqual(result["communications_geometry_score_status"], "Context_only")

    def test_gate_only_metric_is_not_an_unconfigured_preference(self):
        cfg = config()
        cfg["domains"]["solar_illumination"]["metrics"].append(dict(
            column="margin", unit="dB", role="gate",
            hard_gate=dict(operator="above_threshold", threshold=0)))
        row = dict(id="a", sun=".8", uv="2", margin="0")
        result = engine.assess([row], cfg, "hash")[0]
        self.assertEqual(result["final_rec_score"], 80)
        self.assertEqual(result["evidence_coverage"], "2/2")
        row["margin"] = "-.01"
        result = engine.assess([row], cfg, "hash")[0]
        self.assertEqual(result["hard_gate_status"], "Failed")
        self.assertEqual(result["final_rec_score"], "")
        self.assertEqual(result["comparison_preference_score"], 80)
        self.assertEqual(result["rank"], "")

    def test_gate_role_rejects_preference_or_absent_gate(self):
        for gate, preference in [(None, None), (dict(operator="ge", threshold=0), dict(direction="higher", lower=0, upper=1))]:
            cfg = config()
            cfg["domains"]["solar_illumination"]["metrics"].append(dict(
                column="gate", unit="h", role="gate", hard_gate=gate, preference=preference))
            with self.assertRaisesRegex(ValueError, "gate-only"):
                engine.validate_config(cfg)

    def test_reference_does_not_treat_static_visibility_as_continuity_or_link(self):
        result = engine.assess([dict(id="static", median_sun_visibility_fraction="1",
                                    median_earth_visibility_fraction="1")], self.reference(), "hash")[0]
        self.assertEqual(result["comparison_preference_score"], 100)
        self.assertEqual(result["hard_gate_status"], "Unknown")
        self.assertEqual(result["final_rec_score"], "")
        self.assertEqual(result["rank"], "")
        self.assertTrue(all(d["final_score_contribution"] is None
                            for d in json.loads(result["domain_score_details"])))

    def test_reference_boundaries_missing_time_and_failed_margin(self):
        row = dict(id="test", median_sun_visibility_fraction=".8", median_earth_visibility_fraction=".6",
                   window_continuous_sunlight_hours="156", window_minimum_link_margin_db="0",
                   start_utc="2030-01-01T00:00:00Z", stop_utc="2030-01-07T12:00:00Z")
        cfg = self.reference()
        result = engine.assess([row], cfg, "hash")[0]
        self.assertEqual(result["hard_gate_status"], "Passed")
        self.assertAlmostEqual(result["final_rec_score"], 70)
        for changes, status in [({"window_continuous_sunlight_hours":"155.99"}, "Failed"),
                                ({"window_minimum_link_margin_db":"-.01"}, "Failed"),
                                ({"window_minimum_link_margin_db":""}, "Unknown"),
                                ({"start_utc":"", "stop_utc":""}, "Unknown")]:
            with self.subTest(changes=changes):
                result = engine.assess([{**row, **changes}], cfg, "hash")[0]
                self.assertEqual(result["hard_gate_status"], status)
                self.assertEqual(result["final_rec_score"], "")

    def test_metadata_and_scale_groups_survive_export(self):
        cfg = config()
        cfg["metadata_columns"] = ["sample_type", "comparison_scale"]
        cfg["comparison_group_columns"] = ["sample_type", "comparison_scale"]
        rows = [dict(id="dummy", sun="1", uv="0", sample_type="Dummy", comparison_scale="test"),
                dict(id="nasa", sun=".8", uv="2", sample_type="NASA", comparison_scale="region"),
                dict(id="patch", sun=".9", uv="1", sample_type="NASA", comparison_scale="patch")]
        result = engine.assess(rows, cfg, "hash")
        self.assertEqual([r["rank"] for r in result], [1, 1, 1])
        cfg["comparison_group_columns"] = ["unregistered"]
        with self.assertRaisesRegex(ValueError, "registered metadata"):
            engine.validate_config(cfg)
        cfg["comparison_group_columns"] = []
        for reserved in ("rank", "comparison_preference_score", "radiation_score"):
            cfg["metadata_columns"] = [reserved]
            with self.assertRaisesRegex(ValueError, "shadow computed"):
                engine.validate_config(cfg)

    def test_rebuilt_fixture_contract(self):
        cfg = self.reference()
        rows = engine.read_csv(HERE / "inputs/sites.csv", cfg)
        self.assertEqual(len(rows), 30)
        self.assertEqual({kind:sum(r["sample_type"] == kind for r in rows)
                          for kind in ("NASA", "Synthetic", "Dummy")},
                         dict(NASA=7, Synthetic=13, Dummy=10))
        for row in rows:
            if row["sample_type"] != "Dummy":
                self.assertEqual(row["window_continuous_sunlight_hours"], "")
                self.assertEqual(row["window_minimum_link_margin_db"], "")
                self.assertEqual(row["start_utc"], "")
                self.assertEqual(row["orbital_radiation_counter_median"], "")
        results = engine.assess(rows, cfg, "hash")
        self.assertTrue(all(r["rank"] == "" for r in results if r["sample_type"] != "Dummy"))
        with tempfile.TemporaryDirectory() as tmp:
            exported = Path(tmp) / "results.csv"
            engine.run(HERE / "inputs/sites.csv", exported, HERE / "config_nasa_reference.yml")
            with exported.open(newline="") as handle:
                output = list(csv.DictReader(handle))
            self.assertEqual([r["sample_type"] for r in output], [r["sample_type"] for r in rows])
            self.assertEqual([r["evidence_note"] for r in output], [r["evidence_note"] for r in rows])


if __name__ == "__main__":
    unittest.main()
