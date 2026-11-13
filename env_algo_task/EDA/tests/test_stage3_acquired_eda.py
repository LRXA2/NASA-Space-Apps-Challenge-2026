"""New-cohort data semantics; no changes to existing protected tests."""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'Moon/Stage3_Requirements')]
import stage3_acquired_eda as a


class AcquiredTests(unittest.TestCase):
    def test_complete_one_nm_band_and_conservative_error(self):
        w=np.arange(115.5,180);x=np.ones(65)*2;e=np.ones(65)*.1
        value,error,n=a.see_band(w,x,e)
        self.assertEqual(value,130);self.assertAlmostEqual(error,13);self.assertEqual(n,65)

    def test_zero_or_negative_flux_is_not_a_quiet_day(self):
        for bad in [0,-1,np.nan]:
            w=np.arange(115.5,180);x=np.ones(65);x[2]=bad
            value,error,n=a.see_band(w,x,np.ones(65))
            self.assertTrue(np.isnan(value));self.assertTrue(np.isnan(error));self.assertEqual(n,64)

    def test_masked_bin_is_not_filled(self):
        x=np.ma.array(np.ones(65),mask=[True]+[False]*64)
        self.assertTrue(np.isnan(a.see_band(np.arange(115.5,180),x,np.ones(65))[0]))

    def test_changed_or_incomplete_band_grid_fails(self):
        for w in [np.arange(115.5,179),np.arange(115,180)]:
            with self.assertRaises(ValueError):a.see_band(w,np.ones(len(w)),np.ones(len(w)))

    def test_negative_uncertainty_withholds_band(self):
        error=np.ones(65);error[0]=-1
        self.assertTrue(np.isnan(a.see_band(np.arange(115.5,180),np.ones(65),error)[0]))

    def test_daily_median_is_record_weighted_and_missing_preserved(self):
        f=a.daily_rows('x',pd.to_datetime(['2024-01-01','2024-01-01','2024-01-02'],utc=True),[1,9,np.nan])
        self.assertEqual(f.daily_median.iloc[0],5)
        self.assertTrue(np.isnan(f.daily_median.iloc[1]))
        self.assertEqual(f.valid_samples.tolist(),[2,0])
        self.assertTrue(f.valid_seconds.isna().all())

    def test_daily_missing_timestamp_fails(self):
        with self.assertRaises(ValueError):a.daily_rows('x',pd.to_datetime(['NaT'],utc=True),[1])

    def test_pds_series_dates_use_the_same_daily_contract(self):
        f=a.daily_rows('x',pd.Series(pd.to_datetime(['2024-01-01'],utc=True)),[2])
        self.assertEqual(f.daily_median.iloc[0],2)

    def test_monthly_edge_selection_does_not_depend_on_values(self):
        entries=[{'url':'u'+str(i),'relative_path':f'v_202401{d:02d}.cdf'} for i,d in enumerate([1,2,31])]
        self.assertEqual(a.monthly_edges(entries),[entries[0],entries[2]])

    def test_species_are_not_pooled_for_selection(self):
        entries=[{'url':s+str(d),'relative_path':f'nms_{s}_1_201401{d:02d}_120000.csv'} for s in ['ar','he'] for d in [1,2,31]]
        self.assertEqual(len(a.monthly_edges(entries,True)),4)

    def test_sample_does_not_duplicate_single_file(self):
        entry={'url':'one'}
        self.assertEqual(a.bounded([entry],True),[entry])

    def test_file_boundary_context_does_not_create_duplicate_day(self):
        times=pd.DatetimeIndex(pd.to_datetime(['2024-01-01T23:59:59Z','2024-01-02T00:00:00Z','2024-01-03T00:00:00Z']))
        self.assertEqual(a.nominal_day(times,'thb_l2_esa_20240102_v01.cdf').tolist(),[False,True,False])

    def test_ambiguous_clock_samples_are_not_double_weighted(self):
        t=pd.to_datetime(['2024-01-02','2024-01-01','2024-01-01',None],utc=True)
        self.assertEqual(a.unique_clock(t).tolist(),[True,False,False,False])

    def test_binary_group_offsets_and_big_endian(self):
        label='''<Product_Observational><Table_Binary><offset>0</offset><records>2</records><Record_Binary>
        <record_length>10</record_length><Field_Binary><name>LAT</name><data_type>IEEE754MSBDouble</data_type><field_location>1</field_location><field_length>8</field_length></Field_Binary>
        <Group_Field_Binary><repetitions>2</repetitions><groups>0</groups><group_location>9</group_location><group_length>2</group_length>
        <Field_Binary><name>COUNTS</name><data_type>UnsignedByte</data_type><field_location>1</field_location><field_length>1</field_length></Field_Binary>
        </Group_Field_Binary></Record_Binary></Table_Binary></Product_Observational>'''
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'label.xml';p.write_text(label);dt,offset,n=a.binary_layout(p)
        self.assertEqual(dt.itemsize,10);self.assertEqual(n,2);self.assertEqual(offset,0)
        raw=np.array([(30,[1,2]),(-80,[3,4])],dtype=dt)
        self.assertEqual(raw['LAT'].tolist(),[30,-80]);self.assertEqual(raw['COUNTS'].sum(axis=1).tolist(),[3,7])

    def test_unknown_binary_field_type_is_not_silently_guessed(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'label.xml';p.write_text('<P><Table_Binary><offset>0</offset><records>2</records><Record_Binary><record_length>4</record_length><Field_Binary><name>x</name><field_location>1</field_location><field_length>4</field_length><data_type>Unknown</data_type></Field_Binary></Record_Binary></Table_Binary></P>')
            with self.assertRaises(KeyError):a.binary_layout(p)

    def test_lunar_projection_not_earth_geometry(self):
        masks=a.regional_masks([0,180],[-89,-89],{'near':[0,0,100,40000]})
        self.assertEqual(masks['near'].tolist(),[True,False])

    def test_empty_numeric_support_is_nan_not_zero(self):
        r=a.describe([np.nan,np.inf])
        self.assertEqual(r['valid'],0);self.assertTrue(np.isnan(r['median']))


if __name__=='__main__':unittest.main()
