"""Historical time context cannot manufacture a candidate safety/seasonal forecast."""
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import environment_engine
import temporal_context


def fixtures():
    catalog, support, daily, monthly, quarterly = [], [], [], [], []
    for sid, environment, instrument, year in [("uv", "UV", "SORCE_SOLSTICE", 2020),
            ("plasma", "plasma", "ARTEMIS_THB", 2024), ("rad", "radiation", "GOES19", 2024)]:
        catalog.append(dict(series_id=sid, environment=environment, instrument=instrument,
            version="fictional", channel="fictional", unit="fixture units", position_group="fictional",
            validity_basis="synthetic software test only"))
        for day, value in [(1, 2.), (2, 4.)]:
            daily.append(dict(series_id=sid, date=f"{year}-01-{day:02d}T00:00:00+00:00",
                daily_median=value, daily_max=value*10, recorded_samples=100, valid_samples=50,
                valid_seconds=300 if sid == "rad" else np.nan))
        support.append(dict(series_id=sid, recorded_samples=200, valid_samples=100, recorded_dates=2,
            valid_dates=2, candidate_operational_conclusion="Unknown"))
        for frequency, collection, kind in [("M", monthly, "calendar_month"), ("Q", quarterly, "calendar_quarter")]:
            p = pd.Period(f"{year}-01", freq=frequency)
            days = ((p+1).start_time-p.start_time).days
            collection.append(dict(series_id=sid, period=str(p), year=year, period_kind=kind,
                period_start_utc=p.start_time.tz_localize("UTC").isoformat(),
                period_stop_exclusive_utc=(p+1).start_time.tz_localize("UTC").isoformat(),
                expected_calendar_days=days, recorded_days=2, valid_days=2, valid_day_fraction=2/days,
                recorded_samples=200, valid_samples=100, median_of_daily_medians=3.,
                p95_of_daily_medians=3.9, maximum_observed_value=40.,
                valid_seconds=600 if sid == "rad" else np.nan,
                valid_time_fraction=600/(days*86400) if sid == "rad" else np.nan))
    overlap = pd.DataFrame([dict(left="UV", right=r, span_overlap_days=0,
        simultaneous_correlation_performed=False) for r in ["radiation", "plasma"]])
    return {"temporal/"+name+".csv": pd.DataFrame(rows) for name, rows in [
        ("series_catalog", catalog), ("temporal_support", support), ("daily_context", daily),
        ("monthly_context", monthly), ("quarterly_context", quarterly), ("cross_dataset_overlap", overlap)]}


class TemporalContextTests(unittest.TestCase):
    def test_older_manifest_remains_optional(self):
        self.assertEqual(temporal_context.validate({}), [])

    def test_handling_pass_is_not_site_pass(self):
        checks = temporal_context.validate(fixtures())
        self.assertEqual([r[2] for r in checks], ["Passed", "Failed", "Unknown"])
        self.assertEqual([r[0] for r in checks], ["E14", "E15", "E16"])

    def test_missing_source_not_silently_skipped(self):
        f = fixtures(); del f["temporal/quarterly_context.csv"]
        with self.assertRaises(KeyError): temporal_context.validate(f)

    def test_candidate_relabelling_rejected(self):
        f = fixtures(); f["temporal/monthly_context.csv"]["candidate_id"] = "invented"
        with self.assertRaises(ValueError): temporal_context.validate(f)

    def test_calendar_quarters_not_lunar_seasons(self):
        f = fixtures(); f["temporal/quarterly_context.csv"]["period_kind"] = "lunar_winter"
        with self.assertRaises(ValueError): temporal_context.validate(f)

    def test_missing_evidence_not_converted_to_zero(self):
        f = fixtures(); f["temporal/monthly_context.csv"].loc[0, "valid_days"] = 0
        with self.assertRaises(ValueError): temporal_context.validate(f)

    def test_counts_must_agree_across_handoff(self):
        f = fixtures(); f["temporal/temporal_support.csv"].loc[0, "valid_samples"] += 1
        with self.assertRaises(ValueError): temporal_context.validate(f)

    def test_daily_statistics_must_match_summary(self):
        f = fixtures(); f["temporal/monthly_context.csv"].loc[0, "median_of_daily_medians"] = 100
        with self.assertRaises(ValueError): temporal_context.validate(f)

    def test_plasma_samples_not_continuous_coverage(self):
        f = fixtures(); f["temporal/monthly_context.csv"].loc[1, "valid_seconds"] = 10
        f["temporal/monthly_context.csv"].loc[1, "valid_time_fraction"] = 10/(31*86400)
        with self.assertRaises(ValueError): temporal_context.validate(f)

    def test_uv_overlap_change_requires_explicit_review(self):
        f = fixtures(); f["temporal/cross_dataset_overlap.csv"].loc[0, "span_overlap_days"] = 100
        with self.assertRaises(ValueError): temporal_context.validate(f)

    def test_unsupported_simultaneous_correlation_rejected(self):
        f = fixtures(); f["temporal/cross_dataset_overlap.csv"].loc[0, "simultaneous_correlation_performed"] = True
        with self.assertRaises(ValueError): temporal_context.validate(f)

    def test_no_historical_operational_pass(self):
        f = fixtures(); f["temporal/temporal_support.csv"].loc[0, "candidate_operational_conclusion"] = "Passed"
        with self.assertRaises(ValueError): temporal_context.validate(f)


if __name__ == "__main__": unittest.main()
