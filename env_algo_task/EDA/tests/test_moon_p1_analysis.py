import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "darrel stuff/EDA/shared"), str(ROOT / "darrel stuff/EDA/Moon/Stage3_Requirements")]
from moon_p1_analysis import local_time_hours, sample_containing_pixels, temperature_summary
from notebooks.shared.processing import MOON_CRS


class MoonP1AnalysisTests(unittest.TestCase):
    def test_invalid_local_time_is_not_wrapped(self):
        values = local_time_hours([-9999, -1, 0, 12, 23.9997, 24, 25, np.nan])
        np.testing.assert_allclose(values, [np.nan, np.nan, 0, 12, 23.9997, 0, np.nan, np.nan], equal_nan=True)

    def test_native_sampling_masks_nodata_before_one_scale_decode(self):
        parent = ROOT / "darrel stuff/data/verification"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as directory:
            path = Path(directory) / "source.tif"
            raw = np.array([[-32768, 100], [200, 300]], dtype=np.int16)
            with rasterio.open(path, "w", driver="GTiff", width=2, height=2, count=1,
                               dtype="int16", crs=MOON_CRS, transform=from_origin(0, 20, 10, 10), nodata=-32768) as dst:
                dst.write(raw, 1)
                dst.scales, dst.offsets = (.01,), (.5,)
            centers = pd.DataFrame({"x_m": [5, 15, 15, 25], "y_m": [15, 15, 15, 15]})
            values, pixels, res = sample_containing_pixels(path, centers, (0, 0, 20, 20))
            np.testing.assert_allclose(values, [np.nan, 1.5, 1.5, np.nan], equal_nan=True)
            self.assertEqual(pixels[1], pixels[2])
            self.assertEqual(res, (10, 10))

    def test_summary_retains_distinct_native_centers_and_excludes_invalid(self):
        frame = pd.DataFrame({"region": ["a"] * 4, "clon": [1, 1, 2, 3], "clat": [-85] * 4,
            "tbol": [100., 200., 300., np.nan], "valid_temperature": [True, True, True, False],
            "local_time_h": [0., 1., np.nan, 2.]})
        result = temperature_summary(frame, ["region"])
        self.assertEqual(result.iloc[0].rows, 2)
        self.assertEqual(result.iloc[0].native_centers, 1)
        self.assertEqual(result.iloc[0].median_K, 150.)

    def test_fixed_cohort_missing_hours_stay_missing(self):
        notebook = ROOT / "darrel stuff/EDA/Moon/Thermal/Dar_001_temperature_local_time.ipynb"
        cells = json.loads(notebook.read_text(encoding="utf-8"))["cells"]
        source = next("".join(c["source"]) for c in cells if "def analyse_local_time(" in "".join(c["source"]))
        namespace = {"pd": pd, "np": np, "temperature_summary": temperature_summary, "local_time_hours": local_time_hours}
        exec(compile(source, str(notebook), "exec"), namespace)
        frame = pd.DataFrame({"region": ["a", "a", "b", "b"], "clon": [1, 2, 3, 4], "clat": [-85]*4,
            "source_product": ["p1", "p2", "p1", "p2"], "seasonal_ls_bin": [30]*4,
            "local_time_h": [0., 1., 0., 1.], "tbol": [100.]*4, "valid_temperature": [True]*4})
        coverage = pd.DataFrame({"region": ["a", "a", "b", "b"], "source_product": ["p1", "p2"]*2, "usable_rows": [1]*4})
        frame["ltim"] = frame.local_time_h
        _, summary, cohorts, common = namespace["analyse_local_time"](frame, coverage)
        self.assertEqual(common, ["p1", "p2"])
        self.assertTrue(cohorts.complete_centers.eq(0).all())
        self.assertTrue(summary.loc[summary.cohort.eq("complete_common"), "median_K"].isna().all())
        self.assertTrue(summary.loc[summary.local_time_bin_h.eq(23), "rows"].eq(0).all())

    def test_cohort_sensitivity_matches_product_selection(self):
        notebook = ROOT / "darrel stuff/EDA/Moon/Thermal/Dar_001_temperature_local_time.ipynb"
        cells = json.loads(notebook.read_text(encoding="utf-8"))["cells"]
        source = next("".join(c["source"]) for c in cells if "def analyse_local_time(" in "".join(c["source"]))
        namespace = {"pd": pd, "np": np, "temperature_summary": temperature_summary, "local_time_hours": local_time_hours}
        exec(compile(source, str(notebook), "exec"), namespace)
        frame = pd.DataFrame({"region": ["a"]*4 + ["b"]*2, "clon": [1,2,1,1,3,3], "clat": [-85]*6,
            "source_product": ["p1","p1","p2","p3","p1","p2"], "seasonal_ls_bin": [30]*6,
            "local_time_h": [0.]*6, "tbol": [100.,200.,150.,999.,110.,120.], "valid_temperature": [True]*6})
        coverage = frame.groupby(["region", "source_product"]).size().rename("usable_rows").reset_index()
        # Include the explicitly missing source product, as the real coverage table does.
        coverage = pd.concat([coverage, pd.DataFrame([{"region":"b","source_product":"p3","usable_rows":0}])],ignore_index=True)
        frame["ltim"] = frame.local_time_h
        _, summary, _, common = namespace["analyse_local_time"](frame, coverage)
        self.assertEqual(common, ["p1","p2"])
        first_hour = summary.loc[summary.region.eq("a") & summary.local_time_bin_h.eq(0)].set_index("cohort")
        self.assertEqual(first_hour.loc["available", "rows"], 4)
        self.assertEqual(first_hour.loc["common_available", "rows"], 3)
        self.assertEqual(first_hour.loc["common_available", "median_K"], 150.)
        self.assertEqual(first_hour.loc["complete_common", "median_K"], 125.)


if __name__ == "__main__":
    unittest.main()
