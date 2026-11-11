import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import environment_engine as engine
import stage3_assessment as stage3


class Stage3Tests(unittest.TestCase):
    def test_consumable_margin_and_reserve(self):
        margin, demand = stage3.consumable_margin(2, 3, 1, .5, 4, 1)
        self.assertEqual(demand, 3); self.assertEqual(margin, 0)
        self.assertLess(stage3.consumable_margin(2, 3, 1, .5, 3, 1)[0], 0)
        with self.assertRaises(ValueError): stage3.consumable_margin(2, 3, 1, 1.1, 4, 1)

    def test_power_chronology_cannot_borrow_future_sunlight(self):
        settings = {"battery_usable_Wh": 10, "initial_energy_Wh": 5, "reserve_Wh": 0,
                    "charge_efficiency": 1, "discharge_efficiency": 1}
        frame = pd.DataFrame({"generation_W": [0, 20], "load_W": [6, 0], "hours": [1, 1]})
        margin, detail = stage3.power_margin(frame, settings)
        self.assertEqual(margin, -1); self.assertEqual(detail["unserved_storage_energy_Wh"], 1)
        margin, _ = stage3.power_margin(frame.iloc[::-1], settings)
        self.assertEqual(margin, 4)

    def test_power_efficiency_capacity_and_initial_reserve(self):
        settings = {"battery_usable_Wh": 10, "initial_energy_Wh": 2, "reserve_Wh": 3,
                    "charge_efficiency": .5, "discharge_efficiency": .5}
        margin, _ = stage3.power_margin(pd.DataFrame({"generation_W": [100], "load_W": [0], "hours": [1]}), settings)
        self.assertEqual(margin, -1)

    def test_interval_gaps_and_overlap_rejected(self):
        start, stop = stage3.timestamp("2020-01-01T00:00Z"), stage3.timestamp("2020-01-01T02:00Z")
        f = pd.DataFrame({"start_utc": ["2020-01-01T00:00Z", "2020-01-01T01:00Z"],
                          "stop_utc": ["2020-01-01T01:00Z", "2020-01-01T02:00Z"]})
        self.assertEqual(stage3.intervals(f, start, stop).hours.sum(), 2)
        f.loc[1, "start_utc"] = "2020-01-01T01:30Z"
        with self.assertRaises(ValueError): stage3.intervals(f, start, stop)
        with self.assertRaises(ValueError): stage3.timestamp("2020-01-01")

    def test_thermal_component_and_outage_margins(self):
        f = pd.DataFrame({"minimum_component_K": [280, 275], "maximum_component_K": [290, 295]})
        self.assertEqual(stage3.thermal_margin(f, {"minimum_operating_K": 270, "maximum_operating_K": 300}), 5)
        c = pd.DataFrame({"contact_available": [True, False, False, True], "hours": [1, 1, 2, 1]})
        self.assertEqual(stage3.communication_margin(c, 2), -1)

    def test_blank_profile_unknown_not_pass(self):
        profile = json.loads(Path(engine.__file__).with_name("mission_profile_template.json").read_text())
        summary, checks = stage3.assess(pd.DataFrame({"candidate_id": ["site"]}), profile, Path.cwd())
        self.assertEqual(summary.stage3_status.tolist(), ["unknown"])
        self.assertTrue(checks.status.eq("unknown").all())

    def profile(self):
        return {"schema": 1, "body": "Moon", "start_utc": "2020-01-01T00:00Z", "stop_utc": "2020-01-02T00:00Z",
                "crew_count": 1, "activities": ["test_fixture_only"], "equipment_configuration": {"id": "fixture"},
                "requirements_inventory_complete": True,
                "requirements": [{"id": "stock", "kind": "consumable", "mandatory": True,
                    "source": "fixture_not_operational", "reason": "unit test only"}],
                "candidate_inputs": {"site": {"stock": {"body": "Moon", "support": "candidate_validated", "basis": "modeled",
                    "start_utc": "2020-01-01T00:00Z", "stop_utc": "2020-01-02T00:00Z", "input_file": "stock.csv"}}}}

    def test_supplied_evidence_pass_fail_unknown_and_wrong_period(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); profile = self.profile(); candidates = pd.DataFrame({"candidate_id": ["site", "no_evidence"]})
            pd.DataFrame({"rate_kg_per_crew_day": [1], "recovery_fraction": [0], "available_kg": [2], "reserve_kg": [0]}).to_csv(root / "stock.csv", index=False)
            summary, _ = stage3.assess(candidates, profile, root)
            self.assertEqual(summary.stage3_status.tolist(), ["pass", "unknown"])
            pd.DataFrame({"rate_kg_per_crew_day": [1], "recovery_fraction": [0], "available_kg": [0], "reserve_kg": [0]}).to_csv(root / "stock.csv", index=False)
            summary, _ = stage3.assess(candidates, profile, root)
            self.assertEqual(summary.stage3_status.tolist(), ["fail", "unknown"])
            profile["candidate_inputs"]["site"]["stock"]["stop_utc"] = "2020-01-03T00:00Z"
            summary, _ = stage3.assess(candidates, profile, root)
            self.assertTrue(summary.stage3_status.eq("unknown").all())

    def test_mars_cannot_use_moon_candidates_and_zero_mandatory_cannot_pass(self):
        profile = self.profile(); profile["body"] = "Mars"
        self.assertTrue(stage3.profile_readiness(profile))
        profile = self.profile(); profile["requirements"][0]["mandatory"] = False
        summary, _ = stage3.assess(pd.DataFrame({"candidate_id": ["site"]}), profile, Path.cwd())
        self.assertEqual(summary.stage3_status.tolist(), ["unknown"])

    def test_terrain_free_power_is_unknown_and_missing_file_is_error(self):
        profile = self.profile()
        profile["requirements"][0]["kind"] = "power"
        item = profile["candidate_inputs"]["site"]["stock"]
        summary, checks = stage3.assess(pd.DataFrame({"candidate_id": ["site"]}), profile, Path.cwd())
        self.assertEqual(summary.stage3_status.tolist(), ["unknown"])
        self.assertIn("Terrain-aware", checks.reason.iloc[-1])
        profile["requirements"][0]["kind"] = "consumable"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                stage3.assess(pd.DataFrame({"candidate_id": ["site"]}), profile, Path(tmp))

    def test_known_failure_dominates_another_unknown_mandatory_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); profile = self.profile()
            profile["requirements"].append({"id": "missing", "kind": "capacity_demand", "mandatory": True,
                "source": "fixture", "reason": "explicitly missing second case"})
            pd.DataFrame({"rate_kg_per_crew_day": [1], "recovery_fraction": [0], "available_kg": [0], "reserve_kg": [0]}).to_csv(root / "stock.csv", index=False)
            summary, checks = stage3.assess(pd.DataFrame({"candidate_id": ["site"]}), profile, root)
            self.assertEqual(summary.stage3_status.tolist(), ["fail"])
            self.assertEqual(summary.mandatory_unknown.tolist(), [1])

    def test_capacity_quantity_and_unit_are_not_interchangeable(self):
        frame = pd.DataFrame({"capacity": [20], "demand": [3], "reserve": [2], "unit": ["unit_A"], "quantity": ["fixture_quantity"]})
        settings = {"unit": "unit_A", "quantity": "fixture_quantity"}
        value, _, unit = stage3.requirement_margin("capacity_demand", frame, settings, None, None, None)
        self.assertEqual((value, unit), (15, "unit_A"))
        settings["unit"] = "unit_B"
        with self.assertRaises(ValueError): stage3.requirement_margin("capacity_demand", frame, settings, None, None, None)


if __name__ == "__main__": unittest.main()
