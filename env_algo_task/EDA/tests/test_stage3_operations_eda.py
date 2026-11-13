from pathlib import Path
import sys
import unittest
import json
import hashlib
import pandas as pd
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Moon/Stage3_Requirements'))
import stage3_operations_eda as o


def resource():
    return pd.DataFrame({'mission':['test'],'eva':[1],'crew_role':['CDR'],'resource':['Oxygen'],
        'actual_initial':[10.],'actual_consumed':[6.],'actual_remaining':[4.],'predicted_consumed':[4.],
        'predicted_remaining':[6.],'reported_actual_redline':[1.],
        'actual_duration_min':[120.],'planned_duration_min':[100.]})


class OperationsTests(unittest.TestCase):
    def test_duration_rate_product_matches_total_ratio(self):
        f=o.duration_rate_decomposition(resource()).iloc[0]
        self.assertAlmostEqual(f.mean_rate_ratio,1.25);self.assertAlmostEqual(f.duration_ratio_actual_to_planned,1.2)
        self.assertAlmostEqual(f.consumption_ratio_actual_to_predicted,1.5);self.assertAlmostEqual(f.ratio_identity_residual,0.)

    def test_invalid_duration_is_not_defaulted(self):
        f=resource();f.loc[0,'actual_duration_min']=0
        with self.assertRaises(ValueError):o.duration_rate_decomposition(f)

    def test_undefined_planned_rate_stays_unknown(self):
        f=resource();f.loc[0,'predicted_consumed']=0
        result=o.duration_rate_decomposition(f).iloc[0]
        self.assertFalse(result.decomposition_supported);self.assertTrue(np.isnan(result.mean_rate_ratio))

    def test_page_hash_and_source_version_are_required(self):
        text='Calibrated source information '*8
        case={'id':'x','file':'x.pdf','pages':[1],'check_terms':['calibrated']}
        doc={'file':'x.pdf','source_sha256':'good','pages':[{'pdf_page':1,'text':text,'text_characters':len(text),'text_sha256':hashlib.sha256(text.encode()).hexdigest()}]}
        with self.assertRaises(ValueError):o.case_rows([case],{'documents':[doc]},{'x.pdf':'wrong'})
        doc['pages'][0]['text_sha256']='wrong'
        with self.assertRaises(ValueError):o.case_rows([case],{'documents':[doc]},{'x.pdf':'good'})

    def test_ligatures_and_ocr_spacing_do_not_execute_or_change_source(self):
        self.assertEqual(o.normalized('Ther mal \ufb01lter'),o.normalized('thermal filter'))

    def test_no_historical_values_or_mission_profile_is_adopted(self):
        f=o.proposals();self.assertTrue(f.current_outcome.eq('Unknown').all())
        self.assertTrue(f.limit_value.isna().all());self.assertTrue(f.preference_weight.isna().all())


if __name__=='__main__':unittest.main()
