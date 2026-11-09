import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import environment_engine
from evidence_rules import explain_checks


class ExplainedContextTests(unittest.TestCase):
    def test_signed_distance_uses_operator_and_preserves_input(self):
        frame=pd.DataFrame({'rule_id':['sun','slope','missing'],'operator':['ge','le','ge'],
                            'value':[.7,9.,np.nan],'limit':[.5,8.,.5]})
        before=frame.copy(deep=True);out=explain_checks(frame)
        assert_frame_equal(frame,before)
        self.assertAlmostEqual(out.comparison_filter_distance.iloc[0],.2)
        self.assertEqual(out.comparison_filter_distance.iloc[1],-1.)
        self.assertTrue(pd.isna(out.comparison_filter_distance.iloc[2]))
        self.assertTrue(out.distance_kind.str.contains('NOT_operating_margin').all())

    def test_unconfigured_requirement_does_not_receive_a_zero_distance(self):
        frame=pd.DataFrame({'rule_id':['optional_power'],'operator':[None],'value':[np.nan],'limit':[None]})
        out=explain_checks(frame)
        self.assertTrue(pd.isna(out.comparison_filter_distance.iloc[0]))


if __name__=='__main__':unittest.main()
