import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "shared"), str(Path(__file__).resolve().parents[1] / "Moon/Stage3_Requirements")]
import stage3_annual_radiation_eda as eda


class AnnualRadiationContracts(unittest.TestCase):
    def frame(self):
        f=pd.DataFrame({'TIME':['2024-01-01T00:00:00','2024-01-01T00:00:01','2024-01-01T00:00:02'],
                        'BIASCMD':[1,1,0],'CALLOW':[0,0,0],'CALHIGH':[0,0,0],
                        'GOOD':[5.,-1.,99.],'REJECT':[1.,1.,1.],'TOTAL':[6.,0.,100.]})
        for i in range(1,7):f[f'PROCDFLAG {i}']=1
        return f

    def test_missing_dates_do_not_count_as_zero_measurements(self):
        missing=eda.missing_dates(['2024-01-01','2024-01-04','2024-01-04'])
        self.assertEqual(list(missing.strftime('%Y-%m-%d')),['2024-01-02','2024-01-03'])

    def test_state_and_counter_validity_remain_separate(self):
        with patch.object(eda,'read_pds4',return_value=self.frame()):row,h=eda.crater_day(Path('synthetic.xml'),'2024-01-01')
        self.assertEqual(row['records'],3)
        self.assertEqual(row['selected_state_records'],2)
        self.assertEqual(row['supported_nonnegative_counter_records'],1)
        self.assertEqual(row['negative_or_missing_counter_rows'],1)
        self.assertEqual(row['selected_state_good_median'],5.)
        self.assertEqual(h.supported_records.sum(),1)
        self.assertNotIn('dose',row)

    def test_wrong_selected_day_rejected(self):
        with patch.object(eda,'read_pds4',return_value=self.frame()):
            with self.assertRaises(ValueError):eda.crater_day(Path('synthetic.xml'),'2024-01-02')

    def test_duplicate_record_time_rejected(self):
        frame=self.frame();frame.loc[1,'TIME']=frame.TIME.iloc[0]
        with patch.object(eda,'read_pds4',return_value=frame):
            with self.assertRaises(ValueError):eda.crater_day(Path('synthetic.xml'),'2024-01-01')


if __name__=='__main__':unittest.main()
