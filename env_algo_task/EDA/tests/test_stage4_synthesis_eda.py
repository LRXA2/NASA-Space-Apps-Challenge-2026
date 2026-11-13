from pathlib import Path
import sys
import unittest
import pandas as pd
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Moon/Stage3_Requirements'))
import stage4_synthesis_eda as s


def proposal():
    return pd.DataFrame([{'id':'X-G01','classification':'evidence_guard','title':'guard','required_inputs':'units',
        'decision_logic':'qualified evidence only','existing_rule_crosswalk':'E01','current_outcome':'Unknown',
        'limit_value':np.nan,'limit_state':'not_adopted','preference_weight':np.nan,'subject':'uv',
        'source_run':'frozen/run','proposal_table':'proposals.csv'}])


class SynthesisTests(unittest.TestCase):
    def test_compilation_is_unadopted_not_a_mission_evaluator(self):
        f=s.compile_proposals([proposal()],{'E01','E07','E13'}).iloc[0]
        self.assertFalse(f.loaded_by_pipeline);self.assertEqual(f.adoption_state,'proposed_unadopted')
        self.assertIn('NOT a site failure',f.failed_semantics)

    def test_duplicate_rules_are_not_silently_overwritten(self):
        with self.assertRaises(ValueError):s.compile_proposals([proposal(),proposal()],{'E01','E07','E13'})

    def test_adopted_limit_or_weight_is_rejected(self):
        for field in ['limit_value','preference_weight']:
            f=proposal();f.loc[0,field]=1
            with self.assertRaises(ValueError):s.compile_proposals([f],{'E01','E07','E13'})

    def test_unknown_existing_reference_is_rejected(self):
        with self.assertRaises(ValueError):s.compile_proposals([proposal()],{'E07','E13'})

    def test_guard_source_failure_is_not_an_operational_site_failure(self):
        f=s.compile_proposals([proposal()],{'E01','E07','E13'}).iloc[0]
        self.assertIn('not an operational pass',f.passed_semantics)
        self.assertEqual(f.current_outcome,'Unknown')

    def test_spec_examples_preserve_mandatory_eligibility_and_no_fourth_state(self):
        f=s.specification_examples().set_index('example_id')
        self.assertFalse(f.loc['mandatory_unknown_soft_favourable','preference_comparison_eligible'])
        self.assertFalse(f.loc['qualified_mandatory_exceedance','preference_comparison_eligible'])
        self.assertTrue(pd.isna(f.loc['unselected_inapplicable_requirement','specified_check_state']))
        self.assertEqual(set(f.specified_check_state.dropna()),{'Passed','Failed','Unknown'})

    def test_native_catalog_preserves_sensor_and_species_identity(self):
        f=pd.DataFrame({'field':['T','T'],'unit':['K','K'],'series_id':['probeA','probeB'],'position':['upper','lower']})
        self.assertEqual(len(s.native_catalog('hfe','sensors.csv',f,'run')),2)

    def test_outline_routes_cover_27_factors_without_terrestrial_weather_substitution(self):
        self.assertEqual(len(s.FACTOR_SUBJECTS),27)
        self.assertEqual(s.FACTOR_SUBJECTS[4],['operations'])


if __name__=='__main__':unittest.main()
