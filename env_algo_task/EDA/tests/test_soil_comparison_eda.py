"""Protect cross-mission units, independence and classification-only semantics."""
from pathlib import Path
import sys
import unittest
import numpy as np

STAGE = Path(__file__).resolve().parents[1]/'Moon/Stage3_Requirements'
sys.path.insert(0,str(STAGE))
from stage3_soil_comparison_eda import (sourcebook_profiles, html_chemical_profiles,
    maturity_category, clr, docx_tables, grain_catalog, CHEM)


class SoilComparisonTests(unittest.TestCase):
    def test_sourcebook_does_not_duplicate_regional_and_mission_averages(self):
        header='11 12 14 15a 15b 15c 15 16a 16b 16c 16 17a 17b 17c 17d 17 L16 L20 L24'
        text=header+'\n'+'\n'.join(f+' '+' '.join(['5']*19) for f in CHEM)
        frame=sourcebook_profiles(text)
        selected=frame[frame.aggregation.eq('published_mission_reference')]
        self.assertEqual(len(frame),19)
        self.assertEqual(len(selected),9)
        self.assertEqual(sum(selected.agency_group.eq('NASA')),6)
        self.assertEqual(sum(selected.agency_group.eq('non_NASA')),3)

    def test_incomplete_chemical_row_fails_clearly(self):
        text='11 12 14 15a 15b 15c 15 16a 16b 16c 16 17a 17b 17c 17d 17 L16 L20 L24\nFeO 5 6'
        with self.assertRaises(ValueError):sourcebook_profiles(text)

    def test_ce6_excludes_rock_and_trace_element_duplicates(self):
        header='<tr><th>Element (wt%)</th>'+''.join('<th>'+x+'</th>' for x in CHEM)+'</tr>'
        def row(name):return '<tr><td>'+name+'</td>'+''.join('<td>5</td>' for _ in CHEM)+'</tr>'
        html='<table>'+header+row('CE6A (soil)')+row('CE6B (soil)')+row('CE6R (basalt)')
        html+='<tr><td>Element(ug/g)</td></tr>'+row('CE6A (soil)')+'</table>'
        frame=html_chemical_profiles(html,'CE6')
        self.assertEqual(list(frame.profile_id),['CE6A','CE6B'])
        self.assertEqual(set(frame.unit),{'wt_percent'})

    def test_categories_have_explicit_boundaries_and_unknown(self):
        self.assertEqual(maturity_category(29.9),'immature')
        self.assertEqual(maturity_category(30),'submature')
        self.assertEqual(maturity_category(60),'submature')
        self.assertEqual(maturity_category(60.1),'mature')
        for value in [None,np.nan,-1]:self.assertEqual(maturity_category(value),'Unknown')

    def test_clr_is_scale_invariant_not_a_raw_percent_weighted_score(self):
        # Centring logarithms can leave machine-epsilon residuals at mathematical zero.
        np.testing.assert_allclose(clr([5,10,20]),clr([10,20,40]),atol=1e-14,rtol=1e-12)
        self.assertAlmostEqual(float(clr([5,10,20]).sum()),0)
        with self.assertRaises(ValueError):clr([0,10,20])

    def test_downloaded_grain_catalog_is_apollo_and_not_eighty_sites(self):
        source=STAGE.parents[2]/'data/reference/lunar_soil_comparison/ce5_supplement.docx'
        frame=grain_catalog(docx_tables(source))
        self.assertEqual(len(frame),80)
        self.assertEqual(frame.parent_sample_id.nunique(),23)
        self.assertEqual(frame.mission.nunique(),5)
        self.assertEqual(set(frame.agency_group),{'NASA'})
        self.assertEqual(int(frame.mean_phi.lt(4.33).sum()),47)


if __name__=='__main__':unittest.main()
