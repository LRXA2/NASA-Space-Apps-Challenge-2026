"""Readable operator names preserve inclusive boundaries and old YAML compatibility."""
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import env_pipeline as engine


class ReadableGateTests(unittest.TestCase):
    def test_readable_operators_are_inclusive(self):
        for operator, passes, fails in [("above_threshold", 6, 4), ("below_threshold", 4, 6)]:
            with self.subTest(operator=operator):
                gate = dict(operator=operator, threshold=5)
                self.assertEqual(engine.hard_check(5, gate)[0], "Passed")
                self.assertEqual(engine.hard_check(passes, gate)[0], "Passed")
                self.assertEqual(engine.hard_check(fails, gate)[0], "Failed")

    def test_old_aliases_have_identical_results(self):
        for old, new in [("ge", "above_threshold"), ("le", "below_threshold")]:
            for value in [None, 4, 5, 6]:
                with self.subTest(operator=old, value=value):
                    self.assertEqual(engine.hard_check(value, dict(operator=old, threshold=5)),
                                     engine.hard_check(value, dict(operator=new, threshold=5)))

    def test_missing_threshold_is_unknown_and_bad_operator_rejected(self):
        self.assertEqual(engine.hard_check(5, dict(operator="above_threshold", threshold=None))[0], "Unknown")
        for operator in ["above", "below", [], None]:
            with self.subTest(operator=operator), self.assertRaises(ValueError):
                engine.hard_check(5, dict(operator=operator, threshold=5))

    def test_default_yaml_uses_readable_operator(self):
        config, _ = engine.load_config(HERE / "config.yml")
        operators = [m["hard_gate"]["operator"] for d in config["domains"].values()
                     for m in d["metrics"] if m.get("hard_gate") is not None]
        self.assertEqual(operators, ["above_threshold"])


if __name__ == "__main__":
    unittest.main()
