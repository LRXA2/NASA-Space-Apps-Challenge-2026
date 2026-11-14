"""Source-anchored continuous dust resemblance, not an operational wear model."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import env_pipeline as engine


class DustReferenceCurveTests(unittest.TestCase):
    def setUp(self):
        self.config, self.digest = engine.load_config(HERE / "config.yml")
        self.metric = self.config["domains"]["dust"]["metrics"][0]
        self.preference = self.metric["preference"]

    def test_source_anchors(self):
        self.assertEqual(self.preference, {
            "direction": "target_range", "lower": 14332.5, "upper": 100711.25,
            "preferred_lower": 38230.0, "preferred_upper": 38230.0})

    def test_boundaries_and_median(self):
        for value, expected in [(14332.5, 0), (38230, 1), (100711.25, 0), (-1000, 0), (200000, 0)]:
            self.assertEqual(engine.utility(value, self.preference), expected)

    def test_interpolation_has_no_full_score_plateau(self):
        centre = 38230.0
        for bound in [14332.5, 100711.25]:
            self.assertAlmostEqual(engine.utility((bound + centre) / 2, self.preference), .5)
        self.assertLess(engine.utility(centre - 1, self.preference), 1)
        self.assertLess(engine.utility(centre + 1, self.preference), 1)

    def test_only_dust_and_operations_change(self):
        before = deepcopy(self.config)
        before["domains"]["dust"]["metrics"][0]["preference"] = {
            "direction": "target_range", "lower": -72046.25, "upper": 187090,
            "preferred_lower": 14332.5, "preferred_upper": 100711.25}
        rows = engine.read_csv(HERE / "sample_input.csv", self.config)
        old = engine.assess(rows, before, "old")
        new = engine.assess(rows, self.config, self.digest)
        for a, b in zip(old, new):
            self.assertEqual(a["survival_score"], b["survival_score"])
            self.assertEqual(a["operations_status"], b["operations_status"])
            for field in ["operations_solar_illumination_score", "operations_communications_geometry_score", "operations_soil_score"]:
                self.assertEqual(a[field], b[field])
            details = json.loads(b["operations_details"]["domain_score_details"])
            fraction = next(d["domain_weight_fraction"] for d in details if d["domain"] == "dust")
            self.assertAlmostEqual(b["operations_score"] - a["operations_score"],
                                   (b["operations_dust_score"] - a["operations_dust_score"]) * fraction)

    def test_shared_apollo_median_is_not_jittered(self):
        rows = engine.read_csv(HERE / "sample_input.csv", self.config)
        apollo = [r for r in rows if r["id"].startswith("apollo_")]
        self.assertEqual(len(apollo), 6)
        self.assertTrue(all(float(r[self.metric["column"]]) == 38230 for r in apollo))
        results = engine.assess(apollo, self.config, self.digest)
        self.assertTrue(all(r["operations_dust_score"] == 100 for r in results))


if __name__ == "__main__":
    unittest.main()
