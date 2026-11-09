"""Annual-scale orbital radiation context; counters/flux are never crew dose."""
from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from stage3_mission_eda import ROOT, LOCAL, external_input, goes_observations, save_figure
from environment_workflow import LocalRun
from decision_eda import accepted_input
from research_p1_readers import read_pds4
from stage3_expanded_eda import goes_daily

CONFIG = Path(__file__).with_name("stage3_annual_config.json")


def missing_dates(dates):
    dates = pd.DatetimeIndex(sorted(pd.to_datetime(dates).unique()))
    return pd.date_range(dates.min(), dates.max(), freq="D").difference(dates)


def crater_day(label, expected_date, *, chunk_rows=100_000):
    if not isinstance(chunk_rows, int) or isinstance(chunk_rows, bool) or chunk_rows < 1:
        raise ValueError("CRaTER chunk size must be a positive integer")
    fields=["TIME", "BIASCMD", "CALLOW", "CALHIGH", "GOOD", "REJECT", "TOTAL"]
    fields += [f"PROCDFLAG {i}" for i in range(1,7)]
    frame=read_pds4(label, columns=fields, chunk_rows=chunk_rows)
    frame["timestamp"]=pd.to_datetime(frame.TIME, utc=True)
    if frame.timestamp.duplicated().any() or not frame.timestamp.is_monotonic_increasing:
        raise ValueError("Duplicate or unordered CRaTER record times")
    if not frame.timestamp.dt.strftime("%Y-%m-%d").eq(expected_date).all():
        raise ValueError("Source dates do not match selected CRaTER day")
    gaps=frame.timestamp.diff().dt.total_seconds()
    if gaps.dropna().le(0).any():
        raise ValueError("Invalid CRaTER cadence")
    normal=frame.BIASCMD.eq(1)&frame.CALLOW.eq(0)&frame.CALHIGH.eq(0)
    normal &= frame[[f"PROCDFLAG {i}" for i in range(1,7)]].eq(1).all(axis=1)
    counters=frame[["GOOD", "REJECT", "TOTAL"]]
    physical=np.isfinite(counters).all(axis=1)&counters.ge(0).all(axis=1)
    supported=frame.loc[normal&physical].set_index("timestamp")
    hourly=supported[["GOOD", "REJECT", "TOTAL"]].resample("1h").median()
    hourly["supported_records"]=supported.GOOD.resample("1h").size()
    hourly=hourly.reset_index()
    row={"date":expected_date, "records":len(frame), "selected_state_records":int(normal.sum()),
        "supported_nonnegative_counter_records":len(supported), "cadence_gaps_over_1_01s":int(gaps.gt(1.01).sum()),
        "negative_or_missing_counter_rows":int((~physical).sum()),
        "selected_state_good_median":supported.GOOD.median(),
        "selected_state_good_p95":supported.GOOD.quantile(.95),
        "selected_state_good_max":supported.GOOD.max(),
        "scope":"per SEC record counters; selected configuration states, not local dose or complete instrument validation"}
    return row, hourly


def execute(notebook, sample=False):
    config=json.loads(CONFIG.read_text(encoding="utf-8"))
    if config["schema"] != 1:
        raise ValueError("Unsupported annual radiation selection")
    days=config["crater_days"]
    if not sample and (pd.Timestamp(days[-1]["date"])-pd.Timestamp(days[0]["date"])).days < 365:
        raise ValueError("Annual minimum time-span requirement not met")
    if sample:
        days=[days[0], days[-1]]
    suffix="_sample" if sample else ""
    with LocalRun(ROOT, "analysis/stage3_annual_radiation"+suffix, config, notebook) as run:
        for p in [CONFIG, Path(__file__), ROOT/"darrel stuff/EDA/Moon/Stage3_Requirements/stage3_expanded_eda.py",
                  ROOT/"darrel stuff/EDA/Moon/Stage3_Requirements/stage3_mission_eda.py", ROOT/"outline.md",
                  ROOT/"darrel stuff/data/verification/stage3_expansion/annual_freeze_acquisition_snapshot.json"]:
            run.input(p)
        daily, hourly=[], []
        for i, day in enumerate(days):
            paths=[external_input(run, config, item) for item in day["files"]]
            label=next(p for p in paths if p.suffix.lower()==".xml")
            row, h=crater_day(label, day["date"])
            daily.append(row);hourly.append(h)
            if i % 25 == 0:
                print("CRaTER completed days:", i+1, "/", len(days), flush=True)
        frame=pd.DataFrame(daily)
        if frame.date.duplicated().any():
            raise ValueError("Multiple versions/days need explicit selection")
        frame.to_csv(run.path("crater_daily_state_and_counter_context.csv"),index=False)
        pd.concat(hourly,ignore_index=True).to_csv(run.path("crater_supported_hourly_medians.csv.gz"),index=False,compression="gzip")
        missing=missing_dates(frame.date)
        pd.DataFrame({"missing_calendar_date":missing}).to_csv(run.path("crater_missing_calendar_dates.csv"),index=False)
        reference=LOCAL/"data/processed/analysis"/config["goes_reference_run"]
        combined=pd.read_csv(accepted_input(run, reference, "daily_directional_channel_support.csv"))
        additions=[]
        files=config["goes_additional_files"][:2] if sample else config["goes_additional_files"]
        for item in files:
            path=external_input(run, config, item)
            observations=goes_observations(path)
            dates=observations.timestamp.dt.strftime("%Y-%m-%d").unique()
            if len(dates) != 1 or len(observations) != 7488:
                raise ValueError("Unexpected GOES daily dimensions/date")
            additions.append(goes_daily(observations).assign(date=dates[0],source_file=item["relative_path"]))
        if additions:
            combined=pd.concat([combined,*additions],ignore_index=True)
        if combined.duplicated(["date","sensor","channel"]).any():
            raise ValueError("GOES version/satellite identity conflict")
        if not sample and (pd.to_datetime(combined.date).max()-pd.to_datetime(combined.date).min()).days < 365:
            raise ValueError("GOES minimum annual span not met")
        combined.to_csv(run.path("extended_goes_daily_directional_channel_support.csv"),index=False)
        go_missing=missing_dates(combined.date)
        pd.DataFrame({"missing_calendar_date":go_missing}).to_csv(run.path("goes_missing_calendar_dates.csv"),index=False)
        groups=combined.groupby(["sensor","channel","lower_energy_keV","upper_energy_keV"]).agg(
            completed_days=("date","size"), days_any_qualified=("qualified_bins",lambda x:x.gt(0).sum()),
            complete_qualified_days=("qualified_bins",lambda x:x.eq(288).sum()),
            qualified_bins=("qualified_bins","sum"), recorded_bins=("recorded_bins","sum"),
            maximum_supported_flux=("qualified_max_flux","max")).reset_index()
        groups.to_csv(run.path("extended_goes_energy_direction_support.csv"),index=False)
        fig, axes=plt.subplots(2,1,figsize=(12,7),layout="constrained")
        axes[0].scatter(pd.to_datetime(frame.date), frame.selected_state_good_median, s=8)
        axes[0].set(ylabel="Median GOOD counter / SEC record",title="Completed CRaTER dates; no dose or SPE classification")
        fraction=combined.groupby("date").qualified_bins.sum()/7488
        axes[1].scatter(pd.to_datetime(fraction.index),fraction,s=8)
        axes[1].set(ylabel="Qualified channel/time fraction",xlabel="UTC date",title="GOES-16: date span and quality support are different")
        save_figure(run,fig,"annual_radiation_context_and_quality")
        findings={"sample":sample, "crater_completed_days":len(frame), "crater_date_start":frame.date.min(),
            "crater_date_end":frame.date.max(), "crater_calendar_span_days":(pd.Timestamp(frame.date.max())-pd.Timestamp(frame.date.min())).days+1,
            "crater_missing_calendar_dates":len(missing),"crater_records":int(frame.records.sum()),
            "crater_selected_state_records":int(frame.selected_state_records.sum()),
            "goes_completed_days":int(combined.date.nunique()), "goes_date_start":combined.date.min(),"goes_date_end":combined.date.max(),
            "goes_missing_calendar_dates":len(go_missing),"goes_qualified_bins":int(combined.qualified_bins.sum()),
            "goes_recorded_bins":int(combined.recorded_bins.sum()),
            "holds":["Annual minimum means stated calendar/date coverage; gaps and quality exclusions remain explicit",
                "Two dense years are not available in this frozen acquisition; isolated later dates do not fill the gap",
                "Orbital counters/flux are not lunar crew dose or independently verified events",
                "No hard exposure cutoff or protection adequacy was inferred"]}
        run.path("findings.json").write_text(json.dumps(findings,indent=2),encoding="utf-8")
        print(json.dumps(findings,indent=2));folder=run.directory
    return folder, findings
