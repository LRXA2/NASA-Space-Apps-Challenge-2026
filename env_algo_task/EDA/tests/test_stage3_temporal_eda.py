"""Temporal aggregation contracts: missing support never means a quiet/safe period."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

import numpy as np
import pandas as pd

sys.path[:0] = [str(Path(__file__).resolve().parents[1]/"Moon/Stage3_Requirements"),
               str(Path(__file__).resolve().parents[1]/"shared")]
import stage3_temporal_eda as temporal


def daily_fixture():
    return pd.DataFrame({"series_id": ["fictional"]*3,
        "date": pd.to_datetime(["2024-01-01", "2024-01-03", "2024-03-01"], utc=True),
        "daily_median": [2., 10., np.nan], "daily_p95": [4., 20., np.nan], "daily_max": [7., 50., np.nan],
        "recorded_samples": [100, 1, 8], "valid_samples": [100, 1, 0], "valid_seconds": [np.nan]*3})


def uv_fixture():
    return pd.DataFrame({"nominal_date": [20030514.5]*65, "jdn": [2452774.]*65,
        "low_nm": np.arange(115, 180), "high_nm": np.arange(116, 181),
        "mode": [11]*65, "version": [18]*65, "irradiance": [2.]*65,
        "uncertainty": [.1]*65, "quality": [0]*65})


class TemporalTests(unittest.TestCase):
    def test_complete_uv_band_integral(self):
        r = temporal.uv_days(uv_fixture(), "FUV").iloc[0]
        self.assertEqual(r.daily_median, 130.)
        self.assertTrue(r.complete_spectrum)
        self.assertIn("mode11_v18", r.series_id)

    def test_filled_uv_bin_withholds_complete_band(self):
        f = uv_fixture(); f.loc[0, "quality"] = 2
        r = temporal.uv_days(f, "FUV").iloc[0]
        self.assertTrue(pd.isna(r.daily_median))
        self.assertEqual(r.valid_samples, 64)

    def test_missing_uv_bin_does_not_become_partial_band(self):
        self.assertTrue(pd.isna(temporal.uv_days(uv_fixture().iloc[:-1], "FUV").iloc[0].daily_median))

    def test_duplicate_uv_wavelength_rejected(self):
        f = uv_fixture()
        with self.assertRaises(ValueError):
            temporal.uv_days(pd.concat([f, f.iloc[:1]]), "FUV")

    def test_unknown_uv_quality_rejected(self):
        f = uv_fixture(); f.loc[0, "quality"] = 4
        with self.assertRaises(ValueError): temporal.uv_days(f, "FUV")

    def test_negative_uv_value_not_accepted(self):
        f = uv_fixture(); f.loc[0, "irradiance"] = -1
        self.assertTrue(pd.isna(temporal.uv_days(f, "FUV").iloc[0].daily_median))

    def test_cdf_fill_and_validity_mask(self):
        cdf = Mock()
        cdf.varget.return_value = np.array([-1.e31, -1, 0, 4, 11])
        cdf.varattsget.return_value = {"FILLVAL": -1.e31, "VALIDMIN": 0, "VALIDMAX": 10}
        value, _ = temporal.cdf_values(cdf, "fictional")
        np.testing.assert_array_equal(np.isfinite(value), [False, False, True, True, False])

    def test_cdf_vector_bounds(self):
        cdf = Mock()
        cdf.varget.return_value = np.array([[0, 1, 2], [0, -1.e31, 2]])
        cdf.varattsget.return_value = {"FILLVAL": -1.e31, "VALIDMIN": [-10]*3, "VALIDMAX": [10]*3}
        values, _ = temporal.cdf_values(cdf, "fictional")
        labels, _ = temporal.position_groups(values)
        self.assertEqual(labels[1], "unknown_position")

    def test_position_bins_are_explicit_geometry(self):
        groups, _ = temporal.position_groups(np.array([[1, 0, 0], [-5, 0, 0], [20, 0, 0], [.5, 0, 0]]))
        self.assertEqual(list(groups), ["SSE_x_nonnegative_1to5Rm", "SSE_x_negative_5to20Rm",
                                        "SSE_x_nonnegative_ge20Rm", "unknown_position"])

    def test_calendar_months_keep_empty_and_flagged_periods(self):
        f = temporal.period_summary(daily_fixture(), "M")
        self.assertEqual(list(f.period), ["2024-01", "2024-02", "2024-03"])
        self.assertEqual(list(f.expected_calendar_days), [31, 29, 31])
        self.assertEqual(list(f.valid_days), [2, 0, 0])
        self.assertTrue(pd.isna(f.iloc[1].median_of_daily_medians))
        self.assertEqual(f.iloc[2].recorded_samples, 8)
        self.assertEqual(f.iloc[2].valid_samples, 0)

    def test_daily_medians_not_pooled_record_statistics(self):
        r = temporal.period_summary(daily_fixture(), "M").iloc[0]
        self.assertEqual(r.median_of_daily_medians, 6.)
        self.assertEqual(r.maximum_observed_value, 50.)
        self.assertEqual(r.maximum_daily_p95, 20.)
        self.assertTrue(pd.isna(r.valid_time_fraction))

    def test_quarter_recomputed_from_days_not_monthly_medians(self):
        f = daily_fixture(); f.loc[2, "daily_median"] = 30.
        r = temporal.period_summary(f, "Q").iloc[0]
        self.assertEqual(r.period, "2024Q1")
        self.assertEqual(r.expected_calendar_days, 91)
        self.assertEqual(r.median_of_daily_medians, 10.)

    def test_goes_qualified_duration_not_full_day_assumed(self):
        f = daily_fixture(); f["valid_seconds"] = [300, 600, 0]
        r = temporal.period_summary(f, "M").iloc[0]
        self.assertEqual(r.valid_seconds, 900)
        self.assertAlmostEqual(r.valid_time_fraction, 900/(31*86400))

    def test_instruments_are_not_pooled(self):
        f = daily_fixture(); other = f.copy(); other["series_id"] = "different_platform"
        result = temporal.period_summary(pd.concat([f, other]), "M")
        self.assertEqual(len(result), 6)

    def test_duplicate_date_rejected(self):
        f = daily_fixture()
        with self.assertRaises(ValueError): temporal.period_summary(pd.concat([f, f.iloc[:1]]), "M")

    def test_cross_year_comparison_is_separate(self):
        f = temporal.period_summary(daily_fixture(), "M")
        f.loc[1, "median_of_daily_medians"] = 100
        other = f.copy(); other["year"] = 2025; other["median_of_daily_medians"] += 1000
        result = temporal.within_year_comparison(pd.concat([f, other]))
        self.assertEqual(list(result.loc[result.year.eq(2025)].observed_level_order_within_year.dropna()), [1., 2.])


if __name__ == "__main__": unittest.main()
