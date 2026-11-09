"""Incremental annual-context refresh at the required late acquisition cutoff."""
from pathlib import Path
import json

import matplotlib.pyplot as plt
import pandas as pd

from stage3_annual_radiation_eda import crater_day, missing_dates
from stage3_mission_eda import ROOT, LOCAL, external_input, goes_observations, save_figure
from stage3_expanded_eda import goes_daily
from environment_workflow import LocalRun
from decision_eda import accepted_input

CONFIG=Path(__file__).with_name("stage3_refresh_config.json")


def execute(notebook, sample=False):
    config=json.loads(CONFIG.read_text(encoding="utf-8"))
    if config["schema"] != 1:
        raise ValueError("Unsupported late refresh configuration")
    suffix="_sample" if sample else ""
    with LocalRun(ROOT,"analysis/stage3_late_radiation_refresh"+suffix,config,notebook) as run:
        for p in [CONFIG,Path(__file__),ROOT/config["final_recheck"],
                  ROOT/"darrel stuff/EDA/Moon/Stage3_Requirements/stage3_annual_radiation_eda.py",
                  ROOT/"darrel stuff/EDA/Moon/Stage3_Requirements/stage3_expanded_eda.py",ROOT/"darrel stuff/EDA/Moon/Stage3_Requirements/stage3_mission_eda.py"]:
            run.input(p)
        reference=LOCAL/"data/processed/analysis"/config["annual_reference_run"]
        old=pd.read_csv(accepted_input(run,reference,"crater_daily_state_and_counter_context.csv"))
        old_goes=pd.read_csv(accepted_input(run,reference,"extended_goes_daily_directional_channel_support.csv"))
        rows=[]
        days=config["crater_days"][:1] if sample else config["crater_days"]
        for i,day in enumerate(days):
            paths=[external_input(run,config,f) for f in day["files"]]
            row,_=crater_day(next(p for p in paths if p.suffix.lower()==".xml"),day["date"])
            rows.append(row)
            if i%10==0:print("Late CRaTER completed:",i+1,"/",len(days),flush=True)
        new=pd.DataFrame(rows)
        if set(old.date)&set(new.date):
            raise ValueError("Refresh would duplicate/replace prior CRaTER days")
        combined=pd.concat([old,new],ignore_index=True).sort_values("date")
        combined.to_csv(run.path("refreshed_crater_daily_context.csv"),index=False)
        additions=[]
        files=config["goes_files"][:1] if sample else config["goes_files"]
        for item in files:
            observations=goes_observations(external_input(run,config,item))
            dates=observations.timestamp.dt.strftime("%Y-%m-%d").unique()
            if len(dates)!=1 or len(observations)!=7488:
                raise ValueError("Changed late GOES support")
            additions.append(goes_daily(observations).assign(date=dates[0],source_file=item["relative_path"]))
        goes=pd.concat([old_goes,*additions],ignore_index=True)
        if goes.duplicated(["date","sensor","channel"]).any():
            raise ValueError("Refresh would duplicate GOES identities")
        goes.to_csv(run.path("refreshed_goes_daily_directional_support.csv"),index=False)
        pd.DataFrame({"missing_calendar_date":missing_dates(combined.date)}).to_csv(run.path("refreshed_crater_missing_dates.csv"),index=False)
        pd.DataFrame({"missing_calendar_date":missing_dates(goes.date)}).to_csv(run.path("refreshed_goes_missing_dates.csv"),index=False)
        summary=goes.groupby(["sensor","channel","lower_energy_keV","upper_energy_keV"]).agg(
            completed_days=("date","size"),days_with_qualified_bins=("qualified_bins",lambda x:x.gt(0).sum()),
            complete_qualified_days=("qualified_bins",lambda x:x.eq(288).sum()),qualified_bins=("qualified_bins","sum"),
            recorded_bins=("recorded_bins","sum")).reset_index()
        summary.to_csv(run.path("refreshed_goes_energy_direction_support.csv"),index=False)
        fig,axes=plt.subplots(2,1,figsize=(12,7),layout="constrained")
        axes[0].scatter(pd.to_datetime(combined.date),combined.selected_state_good_median,s=7,label="accepted annual context")
        axes[0].scatter(pd.to_datetime(new.date),new.selected_state_good_median,s=10,label="late completed additions")
        axes[0].set(ylabel="Median GOOD counter / SEC record",title="CRaTER counters, not lunar crew dose");axes[0].legend()
        fraction=goes.groupby("date").qualified_bins.sum()/7488
        axes[1].scatter(pd.to_datetime(fraction.index),fraction,s=7)
        axes[1].set(ylabel="Qualified channel/time fraction",xlabel="UTC date",title="GOES-16: gaps and quality exclusions remain")
        save_figure(run,fig,"late_refreshed_annual_context")
        findings={"sample":sample,"cutoff_utc":config["cutoff_utc"],"added_crater_days":len(new),"added_goes_days":len(files),
            "crater_completed_days":len(combined),"crater_start":combined.date.min(),"crater_end":combined.date.max(),
            "crater_records":int(combined.records.sum()),"crater_selected_state_records":int(combined.selected_state_records.sum()),
            "crater_missing_calendar_dates":len(missing_dates(combined.date)),
            "goes_completed_days":int(goes.date.nunique()),"goes_start":goes.date.min(),"goes_end":goes.date.max(),
            "goes_missing_calendar_dates":len(missing_dates(goes.date)),
            "goes_qualified_bins":int(goes.qualified_bins.sum()),"goes_recorded_bins":int(goes.recorded_bins.sum()),
            "holds":["Frozen late cutoff; subsequently arriving files are not automatically claimed as analyzed",
                "Two dense years still unavailable; isolated later dates do not establish two-year support",
                "Counters/flux and sampled peaks are not crew dose, certified storms or safety passes"]}
        run.path("findings.json").write_text(json.dumps(findings,indent=2),encoding="utf-8")
        print(json.dumps(findings,indent=2));folder=run.directory
    return folder,findings
