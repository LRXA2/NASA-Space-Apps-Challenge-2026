from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'darrel stuff/EDA'), str(ROOT)]
from terrain_followup_eda import (terrain_source_statistics, slope_classification_comparison,
    candidate_source_support, nominal_box_overlap, documented_nominal_bin_size, conditional_rank_relationship)


def terrain_pairs():
    return pd.DataFrame({'slope_deg': [4., 12., 4., np.nan], 'sdem_slope_deg': [12., 4., np.nan, 4.],
        'elevation_m': [1., 2., 3., 4.], 'sdem_elevation_m': [2., 4., 6., 8.],
        'sdem_local_std_m': [1., 2., np.nan, 4.], 'sdem_image_fraction': [1., 1., 0., 1.],
        'spot_count': [1., 0., 0., 1.], 'solar_visibility': [.8]*4, 'earth_visibility': [.8]*4,
        'candidate_id': ['a']*4})


class TerrainFollowupTests(unittest.TestCase):
    def test_source_disagreement_denominator_excludes_missing_pairs(self):
        result = slope_classification_comparison(terrain_pairs(), [10.])
        r = result.loc[(result.cohort=='finite_slope_pair') & (result.context=='all_pairs')].iloc[0]
        self.assertEqual(r.paired_cells, 2)
        self.assertEqual(r.lola_only_met, 1)
        self.assertEqual(r.sdem_only_met, 1)
        self.assertEqual(r.disagreement_fraction, 1)

    def test_quality_cohorts_do_not_invent_values(self):
        result = terrain_source_statistics(terrain_pairs())
        counts = result.loc[result.variable=='slope'].set_index('cohort').pair_count
        self.assertEqual(counts.to_dict(), {'finite_slope_pair':2,'complete_sdem_features':2,'complete_positive_lola':1})

    def test_empty_candidate_retains_unknown_measurements(self):
        result = candidate_source_support(terrain_pairs(), ['absent']).iloc[0]
        self.assertEqual(result.analysis_cells, 0)
        self.assertTrue(np.isnan(result.sdem_slope_median_deg))
        self.assertTrue(np.isnan(result.sdem_slope_above_fraction_of_finite))

    def test_exact_nominal_box_overlap_and_boundary(self):
        labels=np.array([[1,0],[1,0]]);known=np.ones_like(labels,dtype=bool)
        meta={'height':2,'width':2,'left_m':0.,'top_m':120.,'spacing_m':60.}
        r=nominal_box_overlap(30,60,1,labels,known,meta,60)
        self.assertEqual(r['component_overlap_fraction'],1)
        r=nominal_box_overlap(60,60,1,labels,known,meta,120)
        self.assertEqual(r['component_overlap_fraction'],.5)
        r=nominal_box_overlap(0,60,1,labels,known,meta,120)
        self.assertEqual(r['known_context_fraction'],.5)
        self.assertEqual(r['unknown_or_outside_fraction'],.5)

    def test_unknown_context_and_bad_sizes_fail_clearly(self):
        labels=np.array([[1,0]]);known=np.array([[True,False]])
        meta={'height':1,'width':2,'left_m':0.,'top_m':60.,'spacing_m':60.}
        r=nominal_box_overlap(60,30,1,labels,known,meta,120)
        self.assertEqual(r['component_overlap_fraction'],.25)
        self.assertEqual(r['unknown_or_outside_fraction'],.75)
        with self.assertRaises(ValueError):nominal_box_overlap(30,30,1,labels,known,meta,0)

    def test_label_resolution_requires_explicit_unique_statement(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'label.xml'
            p.write_text('<root><description>binned at 240 m resolution</description></root>')
            self.assertEqual(documented_nominal_bin_size(p),240)
            p.write_text('<root><description>filename_240</description></root>')
            with self.assertRaises(ValueError):documented_nominal_bin_size(p)

    def test_partial_rank_matches_independent_residual_calculation(self):
        rng=np.random.default_rng(5);n=90
        f=pd.DataFrame({'z':rng.normal(size=n),'p':rng.normal(size=n)})
        f['tbol']=2*f.z+.7*f.p+rng.normal(size=n)
        r=conditional_rank_relationship(f,'p',['z'])
        ranks=f.rank();X=np.column_stack([np.ones(n),ranks.z])
        a=ranks[['tbol','p']].to_numpy();e=a-X@np.linalg.lstsq(X,a,rcond=None)[0]
        self.assertEqual(r['status'],'descriptive')
        self.assertAlmostEqual(r['partial_rank_rho'],np.corrcoef(e.T)[0,1])

    def test_missing_rows_and_insufficient_samples_are_explicit(self):
        f=pd.DataFrame({'tbol':[1.,2.,np.nan],'p':[1.,2.,3.],'z':[2.,3.,4.]})
        r=conditional_rank_relationship(f,'p',['z'])
        self.assertEqual(r['complete_rows'],2)
        self.assertEqual(r['status'],'insufficient_rows')
        self.assertTrue(np.isnan(r['partial_rank_rho']))

    def test_collinear_and_constant_controls_not_silently_removed(self):
        rng=np.random.default_rng(2);f=pd.DataFrame(rng.normal(size=(40,3)),columns=['tbol','p','z'])
        f['z2']=f.z
        self.assertEqual(conditional_rank_relationship(f,'p',['z','z2'])['status'],'rank_deficient_or_ill_conditioned')
        f['constant']=1
        self.assertEqual(conditional_rank_relationship(f,'p',['constant'])['status'],'constant_control')

    def test_perfectly_explained_predictor_has_no_residual_correlation(self):
        rng=np.random.default_rng(2);f=pd.DataFrame({'p':np.arange(40),'tbol':rng.normal(size=40)})
        f['z']=f.p
        self.assertEqual(conditional_rank_relationship(f,'p',['z'])['status'],'no_residual_variation')

    def test_cyclic_control_basis_not_replaced_by_collinear_ranks(self):
        rng=np.random.default_rng(8);hour=np.linspace(2.1,2.5,80)
        f=pd.DataFrame({'tbol':rng.normal(size=80),'p':rng.normal(size=80),
                        's':np.sin(hour*np.pi/12),'c':np.cos(hour*np.pi/12)})
        self.assertEqual(conditional_rank_relationship(f,'p',['s','c'])['status'],'rank_deficient_or_ill_conditioned')
        self.assertEqual(conditional_rank_relationship(f,'p',['s','c'],raw_controls=['s','c'])['status'],'descriptive')


if __name__ == '__main__':
    unittest.main()
