"""New context must never create candidate safety passes or fake continuity."""
import copy
from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import environment_engine
from evidence_rules import radiation_refresh_checks, evidence_use_checks


def radiation_frames():
    daily = pd.DataFrame([dict(platform=19, date="2024-01-01", version="a", sensor=s, channel=0,
                              lower_energy_keV=1000, upper_energy_keV=2000,
                              qualified_bins=s, recorded_bins=288) for s in [0,1]])
    return {
        "radiation_goes/goes_daily_directional_support.csv": daily,
        "radiation_goes/goes_platform_support.csv": pd.DataFrame([dict(platform=19, missing_dates=0,
            qualified_bins=1, recorded_bins=576)]),
        "radiation_crater/crater_support_summary.csv": pd.DataFrame([dict(missing_dates=0, partial_record_days=0)]),
        "radiation_primary/primary_sample_coverage.csv": pd.DataFrame([dict(source_records=100, sampled_records=10)]),
    }


class RadiationEvidenceTests(unittest.TestCase):
    def test_missing_identity_columns_cannot_pass(self):
        f = radiation_frames(); f["radiation_goes/goes_daily_directional_support.csv"].drop(columns="version", inplace=True)
        with self.assertRaises(KeyError):
            radiation_refresh_checks(f)

    def test_nonfinite_sample_counts_cannot_pass(self):
        f = radiation_frames(); f["radiation_primary/primary_sample_coverage.csv"]["source_records"] = float("nan")
        with self.assertRaisesRegex(ValueError, "counts"):
            radiation_refresh_checks(f)

    def test_old_configuration_needs_no_new_context(self):
        self.assertEqual(radiation_refresh_checks({}), [])

    def test_partial_new_context_fails_clearly(self):
        with self.assertRaises(KeyError):
            radiation_refresh_checks({"radiation_goes/goes_platform_support.csv": pd.DataFrame()})

    def test_quality_gaps_cannot_be_continuous_history(self):
        rows = {r[1]: r for r in radiation_refresh_checks(radiation_frames())}
        self.assertEqual(rows["radiation_coverage_to_continuous_mission_history"][2], "Failed")
        self.assertEqual(rows["primary_sample_to_full_event_census"][2], "Failed")
        self.assertEqual(rows["radiation_instrument_identity_preserved"][2], "Passed")
        self.assertIn("not hardware protection", rows["radiation_instrument_identity_preserved"][-1])

    def test_full_count_still_needs_quality_and_mission_applicability(self):
        frames = radiation_frames()
        frames["radiation_primary/primary_sample_coverage.csv"]["sampled_records"] = 100
        rows = {r[1]: r for r in radiation_refresh_checks(frames)}
        self.assertEqual(rows["primary_sample_to_full_event_census"][2], "Unknown")

    def test_duplicate_versions_are_not_summed(self):
        f = radiation_frames(); key = "radiation_goes/goes_daily_directional_support.csv"
        f[key] = pd.concat([f[key], f[key].assign(version="b")])
        with self.assertRaisesRegex(ValueError, "versions"):
            radiation_refresh_checks(f)

    def test_summary_cannot_disagree_with_measured_rows(self):
        f = radiation_frames(); f["radiation_goes/goes_platform_support.csv"]["qualified_bins"] = 999
        with self.assertRaisesRegex(ValueError, "totals"):
            radiation_refresh_checks(f)

    def test_impossible_sample_count_is_not_suppressed(self):
        f = radiation_frames(); f["radiation_primary/primary_sample_coverage.csv"]["sampled_records"] = 101
        with self.assertRaisesRegex(ValueError, "counts"):
            radiation_refresh_checks(f)

    def test_no_candidate_relabelling(self):
        f = radiation_frames(); f["radiation_goes/goes_platform_support.csv"]["candidate_id"] = "fictional"
        with self.assertRaisesRegex(ValueError, "candidate"):
            radiation_refresh_checks(f)

    def test_all_operational_conclusions_stay_unknown(self):
        f = radiation_frames()
        f.update({
            "dated_thermal/dated_thermal_support.csv": pd.DataFrame({"strict_rows": [0]}),
            "apollo/primary_resource_changes.csv": pd.DataFrame({"actual_remaining": [.4],
                "reported_actual_redline": [.4], "historical_remaining_minus_source_redline": [0.]}),
            "geometry/reference_observers.csv": pd.DataFrame({"region": ["test"]}),
            "geometry/terrain_geometry_summary.csv": pd.DataFrame({"region": ["test"]}),
        })
        result = evidence_use_checks(f)
        self.assertEqual(len(result), 11)
        self.assertTrue(result.candidate_operational_conclusion_from_these_sources.eq("Unknown").all())
        self.assertTrue(result.assessment_domain.eq("evidence_use_NOT_site_safety").all())


if __name__ == "__main__":
    unittest.main()
