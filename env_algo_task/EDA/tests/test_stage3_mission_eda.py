import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "shared"), str(Path(__file__).resolve().parents[1] / "Moon/Stage3_Requirements")]
import stage3_mission_eda as eda


class Stage3EDAContracts(unittest.TestCase):
    def resource(self):
        return pd.DataFrame([dict(mission="synthetic", eva=1, crew_role="CDR", resource="Oxygen",
            actual_initial=2., actual_consumed=1.5, actual_remaining=.5,
            predicted_consumed=1.2, predicted_remaining=.8, reported_actual_redline=.4)])

    def test_resource_changes_preserve_input_and_are_not_gates(self):
        frame=self.resource();before=frame.copy(deep=True)
        result=eda.resource_changes(frame)
        assert_frame_equal(frame,before)
        self.assertAlmostEqual(result.historical_remaining_minus_source_redline.iloc[0],.1)
        self.assertAlmostEqual(result.consumption_ratio_actual_to_predicted.iloc[0],1.25)
        self.assertNotIn("status",result)

    def test_duplicate_resource_identity_fails(self):
        with self.assertRaises(ValueError):eda.resource_changes(pd.concat([self.resource()]*2))

    def test_broken_source_balance_fails(self):
        frame=self.resource();frame.loc[0,"actual_remaining"]=1
        with self.assertRaises(ValueError):eda.resource_changes(frame)

    def test_missing_prediction_stays_missing(self):
        f=pd.DataFrame([dict(mission="synthetic",eva=1,crew_role="CDR",resource="Power",
                            actual_remaining_percent=20.,predicted_remaining_percent=np.nan)])
        r=eda.percentage_changes(f)
        self.assertTrue(pd.isna(r.actual_minus_predicted_remaining_pp.iloc[0]))
        self.assertFalse(r.prediction_supported.iloc[0])

    def test_out_of_domain_percent_fails(self):
        f=pd.DataFrame([dict(mission="synthetic",eva=1,crew_role="CDR",resource="Power",
                            actual_remaining_percent=120.,predicted_remaining_percent=20.)])
        with self.assertRaises(ValueError):eda.percentage_changes(f)

    def test_reference_unit_conversion_and_duration_are_explicit(self):
        r=eda.reference_exposures(pd.DataFrame({"effective_dose_cSv_year":[1.]}),days=[365.25])
        self.assertEqual(r.reference_mSv.iloc[0],10.)
        self.assertIn("assumed steady",r.basis.iloc[0])

    def test_invalid_dose_or_duration_rejected(self):
        with self.assertRaises(ValueError):eda.reference_exposures(pd.DataFrame({"effective_dose_cSv_year":[-1.]}))
        with self.assertRaises(ValueError):eda.reference_exposures(pd.DataFrame({"effective_dose_cSv_year":[1.]}),days=[0])

    def test_geometry_flagged_and_nonpositive_temperature_not_approved(self):
        from pyproj import Transformer
        lon,lat=Transformer.from_crs(eda.MOON_CRS,eda.MOON_GEOGRAPHIC,always_xy=True).transform(70000,120000)
        f=pd.DataFrame(dict(clon=[lon]*3,clat=[lat]*3,tb=[100.,110.,-100.],qca=[0]*3,qge=[0,12,0],qmi=[0]*3,cloctime=[24.,12.,6.]))
        r=eda.thermal_quality(f,[65000,110000,81000,126000])
        self.assertEqual(r.strict_quality.tolist(),[True,False,False])
        self.assertEqual(r.download_policy_diagnostic.tolist(),[True,True,False])
        self.assertEqual(r.local_hour.iloc[0],0)

    def test_hazard_principles_do_not_issue_eligibility(self):
        f=eda.hazard_evidence()
        self.assertGreaterEqual(len(f),10)
        self.assertTrue(f.current_site_operational_status.str.startswith("Unknown").all())
        self.assertTrue(f.risk_weight_or_threshold.eq("not adopted").all())

    def test_goes_lut_failure_cannot_be_zero_exposure_or_valid_flux(self):
        import netCDF4 as nc
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"synthetic.nc"
            with nc.Dataset(p,"w") as d:
                for k,n in [("time",1),("sensor",1),("channel",1)]:d.createDimension(k,n)
                t=d.createVariable("time","f8",("time",));t.units="seconds since 2000-01-01";t[:]=0
                f=d.createVariable("AvgDiffProtonFlux","f8",("time","sensor","channel"));f.units="protons/(cm^2 sr keV s)";f[:]=5
                for k,value in [("DiffValidL1bSamplesInAvg",300),("DiffDQFdtcSum",0),("DiffDQFoobSum",0),("DiffDQFerrSum",0)]:
                    v=d.createVariable(k,"f8",("time","sensor","channel"));v[:]=value
                for k,value in [("DiffProtonLowerEnergy",1),("DiffProtonUpperEnergy",2)]:
                    v=d.createVariable(k,"f8",("sensor","channel"));v[:]=value
                d.createVariable("ExpectedLUTNotFound","i4").assignValue(0)
            r=eda.goes_observations(p)
            self.assertFalse(r.strict_quality.iloc[0])
            self.assertEqual(r.flux.iloc[0],5)

    def test_diviner_documented_label_typo_requires_complete_numbered_schema(self):
        names=["date","utc"]+[f"value{i}" for i in range(3,34)]
        with tempfile.TemporaryDirectory() as folder:
            table=Path(folder)/"synthetic.tab";label=Path(folder)/"synthetic.lbl"
            row=','.join(['"01-Jan-2024"','"00:00:00.000"']+['1']*31)
            table.write_bytes(b''.join((s.ljust(340)+'\r\n').encode() for s in ['# header']*4+[row]))
            blocks=[]
            for i,name in enumerate(names,1):
                opening="COLUM" if i==17 else "COLUMN"
                blocks.append(f"OBJECT = {opening}\nCOLUMN_NUMBER = {i}\nNAME = {name}\nEND_OBJECT = COLUMN\n")
            text='^TABLE = ("synthetic.tab",5)\nRECORD_BYTES = 342\nFILE_RECORDS = 5\n'+''.join(blocks)
            label.write_text(text)
            result=eda.read_diviner_query(table,label)
            self.assertEqual(len(result),1)
            self.assertEqual(result.attrs["source_label_COLUM_openings"],1)
            self.assertEqual(result.timestamp.iloc[0],pd.Timestamp("2024-01-01",tz="UTC"))
            label.write_text(text.replace("COLUMN_NUMBER = 17\n","COLUMN_NUMBER = 16\n"))
            with self.assertRaises(ValueError):eda.read_diviner_query(table,label)


if __name__=="__main__":unittest.main()
