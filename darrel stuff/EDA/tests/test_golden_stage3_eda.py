from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import golden_stage3_eda as golden


class GoldenEDATests(unittest.TestCase):
    def test_all_stage3_inputs_and_p1_project_contracts_have_mapping(self):
        self.assertEqual(len(golden.GOLDEN), 9)
        mapped = set(" ".join(v[0] for v in golden.GOLDEN.values()).split())
        self.assertTrue({"M01", "M02", "M04", "M07", "M08", "M10", "C01"} <= mapped)

    def test_cyclic_basis_wrap_and_ls_holdout(self):
        f = pd.DataFrame({"region": "r", "cohort": "available",
                          "local_time_bin_h": [0, 6, 12, 18] * 6,
                          "seasonal_ls_bin": np.repeat([30, 90, 150, 210, 270, 330], 4),
                          "rows": 1})
        x = golden.seasonal_design(f); f["median_K"] = x @ np.array([200, 10, 20, 4, 8])
        result = golden.cyclic_validation(f)
        self.assertEqual(len(result), 6)
        self.assertTrue(result.train_bins.eq(20).all()); self.assertTrue(result.test_bins.eq(4).all())
        self.assertTrue((result.cyclic_mae_K < 1e-10).all())
        shifted = f.copy(); shifted.local_time_bin_h += 24
        np.testing.assert_allclose(golden.seasonal_design(f), golden.seasonal_design(shifted), atol=1e-14)

    def test_empty_fold_is_explicitly_insufficient(self):
        f = pd.DataFrame({"region": ["r"], "cohort": ["complete_common"], "local_time_bin_h": [0],
                          "seasonal_ls_bin": [30], "rows": [0], "median_K": [np.nan]})
        result = golden.cyclic_validation(f)
        self.assertEqual(result.status.tolist(), ["insufficient_support"])
        self.assertTrue(result.cyclic_mae_K.isna().all())


if __name__ == "__main__": unittest.main()
