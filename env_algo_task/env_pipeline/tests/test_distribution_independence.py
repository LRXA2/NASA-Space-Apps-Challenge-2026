"""Regression checks: CSV population statistics must not calibrate scoring."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import env_pipeline as engine
from test_env_pipeline import config, metric


class DistributionIndependenceTests(unittest.TestCase):
    def test_repetitions_outliers_and_missing_peers_do_not_change_assessment(self):
        cfg = config()
        target = dict(id="target", sun=".8", uv="2")
        expected = engine.assess([target], cfg, "hash")[0]
        populations = [
            [dict(id=f"repeat_{i}", sun=".8", uv="2") for i in range(64)],
            [dict(id="small", sun="1", uv="1e-12"),
             dict(id="large", sun="1", uv="1e12")],
            [dict(id="missing", sun="", uv=""),
             dict(id="failed", sun="0", uv="2")],
        ]
        for peers in populations:
            with self.subTest(peers=peers[0]["id"]):
                result = engine.assess(peers + [target], cfg, "hash")[-1]
                # Rank is relative to the other eligible rows; the assessment is not.
                self.assertEqual(
                    {k: v for k, v in result.items() if k != "rank"},
                    {k: v for k, v in expected.items() if k != "rank"},
                )
                self.assertEqual(result["final_rec_score"], 80)

    def test_input_order_does_not_change_scores_or_tie_break_ranks(self):
        rows = [dict(id="b", sun=".8", uv="2"),
                dict(id="a", sun=".8", uv="2"),
                dict(id="c", sun="1", uv="0")]
        forward = {r["id"]: r for r in engine.assess(rows, config(), "hash")}
        backward = {r["id"]: r for r in engine.assess(list(reversed(rows)), config(), "hash")}
        self.assertEqual(forward, backward)

    def test_prior_calls_do_not_train_or_mutate_configuration(self):
        cfg = config()
        original = deepcopy(cfg)
        target = dict(id="target", sun=".8", uv="2")
        before = engine.assess([target], cfg, "hash")
        engine.assess([dict(id=f"past_{i}", sun="1", uv="1e9") for i in range(64)], cfg, "hash")
        self.assertEqual(engine.assess([target], cfg, "hash"), before)
        self.assertEqual(cfg, original)

    def test_repeated_counter_value_has_no_special_score_or_threshold(self):
        cfg = config()
        for domain in cfg["domains"].values():
            domain["include_in_score"] = False
            domain["metrics"] = []
        cfg["domains"]["radiation"].update(
            include_in_score=True,
            metrics=[metric("counter", 100, direction="lower",
                            gate=dict(operator="below_threshold", threshold=70))],
        )
        # Fictional software limits only, not a counts-to-hazard calibration.
        target = dict(id="target", counter="32")
        alone = engine.assess([target], cfg, "hash")[0]
        repeats = [dict(id=f"repeat_{i}", counter="32") for i in range(64)]
        varied = [dict(id=f"varied_{i}", counter=str(v))
                  for i, v in enumerate([0, 1, 64, 70, 100, 1e12])]
        for peers in (repeats, varied):
            result = engine.assess([target] + peers, cfg, "hash")[0]
            self.assertAlmostEqual(result["rad_score"], 68)
            self.assertAlmostEqual(result["final_rec_score"], alone["final_rec_score"])
            self.assertEqual(result["hard_gate_status"], "Passed")
            self.assertEqual(json.loads(result["hard_gate_details"])[0]["condition"]["threshold"], 70)

    def test_actual_context_values_cannot_affect_configured_solar_score(self):
        cfg, digest = engine.load_config(HERE / "config.yml")
        for name, domain in cfg["domains"].items():
            domain["include_in_score"] = name == "solar_illumination"
        solar = cfg["domains"]["solar_illumination"]
        solar["multiplier"] = 1
        solar["metrics"][0]["hard_gate"]["threshold"] = .5
        # Configure only an in-memory fictional solar screen to avoid a vacuous
        # comparison of withheld final scores under the shipped null policy.
        target = dict(id="target", median_sun_visibility_fraction=".8")
        context = [m["column"] for d in cfg["domains"].values()
                   for m in d["metrics"] if m["role"] == "context"]
        low = {**target, **dict.fromkeys(context, "0")}
        high = {**target, **dict.fromkeys(context, "1")}
        high.update(orbital_radiation_counter_median="32000",
                    orbital_radiation_counter_maximum="6195000",
                    historical_median_dust_detector_current_charges_per_second="38230000")
        a = engine.assess([low], cfg, digest)[0]
        b = engine.assess([high], cfg, digest)[0]
        self.assertEqual(a["final_rec_score"], 80)
        self.assertEqual(b["final_rec_score"], 80)
        self.assertEqual(a["hard_gate_details"], b["hard_gate_details"])
        self.assertNotEqual(a["score_details"], b["score_details"])


if __name__ == "__main__":
    unittest.main()
