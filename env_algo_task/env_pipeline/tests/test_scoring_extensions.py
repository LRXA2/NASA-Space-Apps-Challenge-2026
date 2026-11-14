"""Opt-in score shaping and transparent margins/contributions; no physical calibration."""
from copy import deepcopy
import json
import math
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import env_pipeline as engine
from test_env_pipeline import config


class ScoringExtensionTests(unittest.TestCase):
    def test_absent_or_explicit_linear_curve_preserves_existing_score(self):
        cfg = config()
        rows = [dict(id="a", sun=".8", uv="2")]
        before = engine.assess(rows, cfg, "hash")[0]
        cfg["domains"]["uv"]["metrics"][0]["preference"]["curve"] = dict(type="linear")
        after = engine.assess(rows, cfg, "hash")[0]
        self.assertEqual(before["final_rec_score"], after["final_rec_score"])
        self.assertEqual(after["final_rec_score"], 80)

    def test_logarithmic_curve_is_normalized_log1p(self):
        curve = dict(type="logarithmic", strength=4)
        engine.validate_curve(curve)
        self.assertAlmostEqual(engine.shape_utility(.5, curve), math.log(3) / math.log(5))

    def test_power_curve_can_penalize_midrange_preferences(self):
        curve = dict(type="power", exponent=2)
        engine.validate_curve(curve)
        self.assertEqual(engine.shape_utility(.5, curve), .25)

    def test_curves_are_bounded_monotonic_and_keep_endpoints(self):
        curves = [None, dict(type="linear"), dict(type="logarithmic", strength=4),
                  dict(type="power", exponent=2), dict(type="power", exponent=.5),
                  dict(type="logistic", steepness=8, midpoint=.4)]
        for curve in curves:
            with self.subTest(curve=curve):
                engine.validate_curve(curve)
                values = [engine.shape_utility(i / 100, curve) for i in range(101)]
                self.assertTrue(all(0 <= x <= 1 for x in values))
                self.assertEqual(values, sorted(values))
                self.assertAlmostEqual(values[0], 0)
                self.assertAlmostEqual(values[-1], 1)

    def test_curve_applies_after_direction_and_range_normalization(self):
        pref = dict(direction="lower", lower=0, upper=10, curve=dict(type="power", exponent=2))
        self.assertAlmostEqual(engine.normalized_utility(2, pref), .8)
        self.assertAlmostEqual(engine.utility(2, pref), .64)
        pref.update(direction="target_range", preferred_lower=3, preferred_upper=7)
        self.assertEqual(engine.utility(5, pref), 1)
        self.assertEqual(engine.utility(0, pref), 0)

    def test_invalid_or_degenerate_curve_configuration_fails_clearly(self):
        invalid = ["linear", {}, dict(type="unknown"), dict(type="power", exponent=0),
                   dict(type="power", exponent="2"), dict(type="logarithmic", strength=-1),
                   dict(type="logistic", steepness=8, midpoint=1),
                   dict(type="logistic", steepness=1e-300, midpoint=.5),
                   dict(type="linear", strength=1), dict(type="logarithmic")]
        for curve in invalid:
            with self.subTest(curve=curve), self.assertRaises(ValueError):
                engine.validate_curve(curve)

    def test_yaml_validation_checks_curve_parameters(self):
        cfg = config()
        cfg["domains"]["uv"]["metrics"][0]["preference"]["curve"] = dict(type="power", exponent=2)
        engine.validate_config(cfg)
        cfg["domains"]["uv"]["metrics"][0]["preference"]["curve"]["exponent"] = float("inf")
        with self.assertRaises(ValueError): engine.validate_config(cfg)

    def test_curves_never_change_raw_hard_gate_decisions(self):
        cfg = config()
        cfg["domains"]["uv"]["metrics"][0]["preference"]["curve"] = dict(type="power", exponent=2)
        rows = engine.assess([dict(id="a", sun=".8", uv="2"), dict(id="b", sun=".4", uv="2")], cfg, "hash")
        self.assertAlmostEqual(rows[0]["final_rec_score"], 72)
        self.assertEqual(rows[1]["hard_gate_status"], "Failed")
        self.assertEqual(rows[1]["final_rec_score"], "")
        self.assertTrue(all(x["final_score_contribution"] is None for x in json.loads(rows[1]["domain_score_details"])))

    def test_signed_gate_margins_retain_native_units(self):
        self.assertEqual(engine.gate_margin(7, dict(operator="above_threshold", threshold=5)), 2)
        self.assertEqual(engine.gate_margin(7, dict(operator="below_threshold", threshold=5)), -2)
        self.assertEqual(engine.gate_margin(5, dict(operator="above_threshold", threshold=5)), 0)
        self.assertEqual(engine.gate_margin(4, dict(operator="between", lower=2, upper=8)), 2)
        self.assertEqual(engine.gate_margin(9, dict(operator="between", lower=2, upper=8)), -1)
        self.assertIsNone(engine.gate_margin(None, dict(operator="above_threshold", threshold=5)))
        self.assertIsNone(engine.gate_margin(7, dict(operator="below_threshold", threshold=None)))

    def test_contributions_reconstruct_domain_and_final_scores(self):
        cfg = config(); cfg["domains"]["solar_illumination"]["multiplier"] = 3
        row = engine.assess([dict(id="a", sun=".6", uv="2")], cfg, "hash")[0]
        domains = [d for d in json.loads(row["domain_score_details"]) if d["included_in_final_score"]]
        self.assertAlmostEqual(sum(d["domain_weight_fraction"] for d in domains), 1)
        self.assertAlmostEqual(sum(d["final_score_contribution"] for d in domains), row["final_rec_score"])
        self.assertAlmostEqual(row["final_rec_score"], 65)
        details = json.loads(row["score_details"])
        for domain in domains:
            metrics = [m for m in details if m["domain"] == domain["domain"] and m["role"] == "score"]
            self.assertAlmostEqual(sum(m["domain_score_contribution"] for m in metrics), domain["domain_score"])

    def test_missing_evidence_keeps_contributions_unknown_not_zero(self):
        row = engine.assess([dict(id="a", sun=".8", uv="")], config(), "hash")[0]
        self.assertEqual(row["final_rec_score"], "")
        self.assertTrue(all(d["final_score_contribution"] is None for d in json.loads(row["domain_score_details"])))
        uv = next(m for m in json.loads(row["score_details"]) if m["column"] == "uv")
        self.assertIsNone(uv["base_utility"])
        self.assertIsNone(uv["domain_score_contribution"])

    def test_priority_labels_and_other_candidates_do_not_change_numeric_scores(self):
        cfg = config(); cfg["domains"]["uv"]["priority"] = "Highest"
        rows = [dict(id="a", sun=".8", uv="2")]
        before = engine.assess(rows, cfg, "hash")[0]["final_rec_score"]
        changed = deepcopy(cfg); changed["domains"]["uv"]["priority"] = "Low"
        after = engine.assess(rows + [dict(id="b", sun=".9", uv="1")], changed, "hash")[0]["final_rec_score"]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
