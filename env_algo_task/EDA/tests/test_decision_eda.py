from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "darrel stuff/EDA/shared"), str(ROOT / "darrel stuff/EDA/Moon/Stage3_Requirements")]
from decision_eda import (CONTEXT, assign_blocks, validate_observations, distinct_context, context_features,
                          thermal_features, complete_phase_table, block_coverage, sampled_condition_runs,
                          pairwise_spearman)
from decision_eda import spatial_blocks

P1 = "pcp_avg_tbol_pols_ls030_slon01_240"
P2 = "pcp_avg_tbol_pols_ls030_slon02_240"


def observations():
    frame = pd.DataFrame({"region": ["A", "A"], "source_product": [P1, P1], "clon": [1., 2.], "clat": [-85., -85.],
        "x_m": [1., 241.], "y_m": [1., 1.], "tbol": [100., 200.], "local_time_h": [23., 1.],
        "usable": [True, True], "valid_temperature": [True, True], "complete_common_cohort": [False, False]})
    for field in CONTEXT:
        frame[field] = [.2, .4]
    frame["permanent_shadow"] = 0.
    return frame


class DecisionEDATests(unittest.TestCase):
    def test_half_open_blocks_and_original_frame_preserved(self):
        frame = pd.DataFrame({"x_m": [-.1, 0., 1199.9, 1200.], "y_m": [0.] * 4})
        result = assign_blocks(frame, 1200)
        self.assertEqual(result.block_x.tolist(), [-1, 0, 0, 1])
        self.assertNotIn("block_x", frame)
        with self.assertRaises(ValueError):
            assign_blocks(frame, 0)

    def test_repeated_phases_do_not_reweight_static_context(self):
        frame = observations()
        repeat = frame.iloc[[0]].assign(source_product=P2)
        centers = distinct_context(pd.concat([frame, repeat], ignore_index=True))
        self.assertEqual(len(centers), 2)
        summary = context_features(centers, ["region"])
        self.assertAlmostEqual(summary.context_mean_solar_fraction.iloc[0], .3)
        repeat["solar_visibility"] = .9
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            distinct_context(pd.concat([frame, repeat], ignore_index=True))

    def test_circular_time_midnight_is_not_noon(self):
        frame = observations()
        result = thermal_features(frame, ["region", "source_product"], [P1])
        self.assertAlmostEqual(result.circular_mean_local_hour.iloc[0], 0., places=10)
        self.assertEqual(result.tbol_median_K.iloc[0], 150.)

    def test_empty_phase_keeps_context_but_not_fake_temperature(self):
        frame = observations()
        context = context_features(distinct_context(frame), ["region"])
        result = complete_phase_table(thermal_features(frame, ["region", "source_product"], [P1]),
                                      context, ["region"], [P1, P2], [P1])
        missing = result.loc[result.source_product.eq(P2)].iloc[0]
        self.assertEqual(missing.usable_rows, 0)
        self.assertTrue(np.isnan(missing.tbol_median_K))
        self.assertTrue(np.isnan(missing.paired_mean_solar_fraction))
        self.assertAlmostEqual(missing.context_mean_solar_fraction, .3)

    def test_all_unusable_rows_have_explicit_empty_measurements(self):
        frame = observations()
        frame["usable"] = False
        frame["valid_temperature"] = False
        frame["tbol"] = np.nan
        result = thermal_features(frame, ["region", "source_product"], [P1])
        self.assertEqual(result.observed_rows.iloc[0], 2)
        self.assertEqual(result.usable_rows.iloc[0], 0)
        self.assertTrue(np.isnan(result.tbol_median_K.iloc[0]))

    def test_spatial_grid_retains_unobserved_edge_blocks(self):
        result = spatial_blocks({"A": {"bounds_m": [-100, 0, 1300, 1200]}}, 1200)
        self.assertEqual(result.block_x.tolist(), [-1, 0, 1])
        self.assertEqual(result.left_m.tolist(), [-100, 0, 1200])
        self.assertEqual(result.right_m.tolist(), [0, 1200, 1300])

    def test_mixed_center_completeness_is_not_fixed_center_completeness(self):
        frame = observations()
        frame.loc[1, "source_product"] = P2
        frame = assign_blocks(frame, 1200)
        context = context_features(distinct_context(frame).pipe(assign_blocks, 1200), ["region", "block_x", "block_y"])
        features = thermal_features(frame, ["region", "block_x", "block_y", "source_product"], [P1, P2])
        table = complete_phase_table(features, context, ["region", "block_x", "block_y"], [P1, P2], [P1, P2])
        result = block_coverage(table, context, [P1, P2], [P1, P2]).iloc[0]
        self.assertTrue(result.all_common_products_have_some_center)
        self.assertTrue(result.mixed_centers_only_completeness)
        self.assertEqual(result.fixed_common_centers, 0)

    def test_sample_runs_are_spans_not_full_interval_durations(self):
        times = pd.date_range("2020-11-01", periods=3, freq="h", tz="UTC")
        row = sampled_condition_runs(times, [True, True, True]).iloc[0]
        self.assertEqual(row.sample_count, 3)
        self.assertEqual(row.first_to_last_sample_span_hours, 2.)
        self.assertTrue(row.left_censored and row.right_censored)

    def test_unknowns_and_timestamp_gaps_break_runs(self):
        times = pd.to_datetime(["2020-11-01T00:00Z", "2020-11-01T01:00Z", "2020-11-01T02:00Z", "2020-11-01T04:00Z"])
        result = sampled_condition_runs(times, [True, None, True, True])
        self.assertEqual(result.sample_count.tolist(), [1, 1, 1])
        self.assertTrue(result.left_censored.all())
        self.assertTrue(result.right_censored.all())
        with self.assertRaises(ValueError):
            sampled_condition_runs([times[0], times[0]], [True, True])

    def test_constant_correlation_stays_undefined(self):
        frame = pd.DataFrame({"region": ["A"] * 3, "a": [1., 2., 3.], "b": [2., 4., 6.], "c": [1.] * 3})
        result = pairwise_spearman(frame, ["a", "b", "c"], ["region"])
        self.assertEqual(result.loc[result.variable_b.eq("b"), "spearman_rho"].iloc[0], 1.)
        self.assertTrue(result.loc[result.variable_b.eq("c"), "spearman_rho"].isna().all())

    def test_bad_usable_flag_and_duplicate_center_fail(self):
        frame = observations()
        frame.loc[0, "tbol"] = -9999.
        with self.assertRaisesRegex(ValueError, "contradict"):
            validate_observations(frame)
        frame = observations()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_observations(pd.concat([frame, frame.iloc[[0]]], ignore_index=True))


if __name__ == "__main__":
    unittest.main()
