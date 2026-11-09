"""Instrument-separated radiation EDA on the last checked acquisition snapshot."""
from pathlib import Path
import argparse
import json
import sys

sys.path[:0] = [str(Path(__file__).resolve().parents[2] / "shared"), str(Path(__file__).resolve().parents[3]), str(Path(__file__).resolve().parents[4])]
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from environment_workflow import LocalRun
from stage3_mission_eda import ROOT, LOCAL, external_input, goes_observations, save_figure
from stage3_expanded_eda import goes_daily
from stage3_annual_radiation_eda import crater_day, missing_dates
from research_p1_readers import pds4_definition, NS, pds4_chunks
from decision_eda import accepted_input

CONFIG = Path(__file__).with_name("stage3_radiation_refresh_config.json")
NOTEBOOK = "Moon/Stage3_Requirements/Dar_041_multiyear_radiation_quality.ipynb"


def input_csv(run, relative_run, name):
    return pd.read_csv(accepted_input(run, LOCAL/"data/processed/analysis"/relative_run, name))


def platform_summary(daily):
    keys = ["platform", "version", "sensor", "channel", "lower_energy_keV", "upper_energy_keV"]
    if daily.duplicated(["platform", "date", "sensor", "channel"]).any():
        raise ValueError("Duplicate platform/date/direction/channel; resolve product versions first")
    return daily.groupby(keys, dropna=False).agg(
        days=("date", "size"), recorded_bins=("recorded_bins", "sum"),
        qualified_bins=("qualified_bins", "sum"),
        complete_qualified_channel_days=("qualified_bins", lambda x: int(x.eq(288).sum())),
        qualified_max_flux=("qualified_max_flux", "max")).reset_index()


def goes(run, config, sample):
    files = config["goes_files"]
    if sample:
        groups = {}
        for item in files:
            groups.setdefault((item["platform"], item["version"]), []).append(item)
        files = [item for group in groups.values() for item in [group[0], group[-1]]]
        files = list({x["relative_path"]: x for x in files}.values())
    rows = []
    for i, item in enumerate(files):
        observations = goes_observations(external_input(run, config, item))
        if (len(observations) != 7488 or observations.timestamp.nunique() != 288
                or observations.sensor.nunique() != 2 or observations.channel.nunique() != 13
                or not observations.timestamp.dt.strftime("%Y-%m-%d").eq(item["date"]).all()
                or not np.isfinite(observations[["lower_energy_keV", "upper_energy_keV"]]).all().all()):
            raise ValueError("Changed GOES daily schema, date or energy support")
        result = goes_daily(observations)
        if len(result) != 26:
            raise ValueError("Missing GOES energy/direction group")
        rows.append(result.assign(platform=item["platform"], version=item["version"],
                                  date=item["date"], source_file=item["relative_path"]))
        if i % 100 == 0:
            print("GOES files:", i+1, "/", len(files), flush=True)
    daily = pd.concat(rows, ignore_index=True)
    platform_summary(daily).to_csv(run.path("goes_energy_direction_version_support.csv"), index=False)
    daily.to_csv(run.path("goes_daily_directional_support.csv"), index=False)
    monthly = daily.assign(month=daily.date.str[:7]).groupby(
        ["platform", "version", "month", "sensor", "channel", "lower_energy_keV", "upper_energy_keV"],
        dropna=False).agg(recorded_bins=("recorded_bins", "sum"), qualified_bins=("qualified_bins", "sum"),
                          qualified_max_flux=("qualified_max_flux", "max")).reset_index()
    monthly.to_csv(run.path("goes_monthly_support.csv"), index=False)
    gaps, overview = [], []
    for platform, part in daily.groupby("platform"):
        missing = missing_dates(part.date)
        gaps += [{"platform": platform, "missing_date": str(d.date())} for d in missing]
        overview.append({"platform": platform, "dates": part.date.nunique(), "start": part.date.min(),
                         "end": part.date.max(), "versions": ";".join(sorted(part.version.unique())),
                         "missing_dates": len(missing), "recorded_bins": int(part.recorded_bins.sum()),
                         "qualified_bins": int(part.qualified_bins.sum()),
                         "complete_qualified_channel_days": int(part.qualified_bins.eq(288).sum()),
                         "days_no_qualified_bins": int(part.groupby("date").qualified_bins.sum().eq(0).sum())})
    pd.DataFrame(gaps, columns=["platform", "missing_date"]).to_csv(run.path("goes_missing_dates.csv"), index=False)
    overview = pd.DataFrame(overview)
    overview.to_csv(run.path("goes_platform_support.csv"), index=False)
    accepted = daily.loc[daily.qualified_bins.gt(0)].copy()
    accepted["descriptive_peak_order"] = accepted.groupby(
        ["platform", "version", "sensor", "channel", "lower_energy_keV", "upper_energy_keV"],
        dropna=False).qualified_max_flux.rank(method="min", ascending=False)
    accepted.loc[accepted.descriptive_peak_order.le(5)].to_csv(run.path("goes_qualified_peak_days.csv"), index=False)
    fig, ax = plt.subplots(figsize=(12, 4), layout="constrained")
    for platform, part in daily.groupby("platform"):
        fraction = part.groupby("date").qualified_bins.sum()/7488
        ax.scatter(pd.to_datetime(fraction.index), fraction, s=6, label="GOES-"+platform)
    ax.set(ylabel="Qualified channel/time fraction", title="Platforms separate; missing/flagged bins are not zero radiation")
    ax.legend(); save_figure(run, fig, "goes_quality_coverage")
    return {"files": len(files), "platforms": overview.to_dict("records"),
            "scope": "Directional differential proton flux, not lunar dose; peak ranks are descriptive, not certified events"}


def crater(run, config, sample):
    old = input_csv(run, config["crater_baseline"], "refreshed_crater_daily_context.csv")
    selection = {d["date"]: d for d in config["crater_days"]}
    if not set(old.date) <= set(selection):
        raise ValueError("Baseline dates disappeared from selected acquisition snapshot")
    additions = [d for date, d in sorted(selection.items()) if date not in set(old.date)]
    if sample:
        additions = [additions[0], additions[len(additions)//2], additions[-1]]
    rows = []
    for i, day in enumerate(additions):
        paths = [external_input(run, config, item) for item in day["files"]]
        # Smaller fixed-width parsing batches reduce transient string arrays;
        # every record/date and the existing daily statistics remain included.
        row, _ = crater_day(next(p for p in paths if p.suffix.lower() == ".xml"),
                            day["date"], chunk_rows=4096)
        rows.append(row)
        if i % 25 == 0:
            print("New CRaTER SEC days:", i+1, "/", len(additions), flush=True)
    added = pd.DataFrame(rows)
    combined = pd.concat([old, added], ignore_index=True).sort_values("date")
    if combined.date.duplicated().any():
        raise ValueError("Duplicate secondary dates")
    combined.to_csv(run.path("crater_daily_context.csv"), index=False)
    added.to_csv(run.path("crater_new_daily_context.csv"), index=False)
    pd.DataFrame({"missing_date": missing_dates(combined.date)}).to_csv(run.path("crater_missing_dates.csv"), index=False)
    combined.assign(month=combined.date.str[:7]).groupby("month").agg(
        dates=("date", "size"), records=("records", "sum"),
        selected_state_records=("selected_state_records", "sum"),
        supported_counter_records=("supported_nonnegative_counter_records", "sum"),
        invalid_counter_records=("negative_or_missing_counter_rows", "sum")).reset_index().to_csv(
            run.path("crater_monthly_support.csv"), index=False)
    fig, ax = plt.subplots(figsize=(12, 4), layout="constrained")
    ax.scatter(pd.to_datetime(combined.date), combined.selected_state_good_median, s=6)
    ax.set(ylabel="Selected-state GOOD median / SEC record", title="Orbital counter variability, not crew dose or event classification")
    save_figure(run, fig, "crater_counter_context")
    result = {"reused_baseline_days": len(old), "new_days": len(added), "days": len(combined),
              "start": combined.date.min(), "end": combined.date.max(),
              "records": int(combined.records.sum()),
              "selected_state_records": int(combined.selected_state_records.sum()),
              "supported_counter_records": int(combined.supported_nonnegative_counter_records.sum()),
              "invalid_counter_records": int(combined.negative_or_missing_counter_rows.sum()),
              "missing_dates": len(missing_dates(combined.date)),
              "partial_record_days": int(combined.records.ne(86400).sum()),
              "intraday_gaps": int(combined.cadence_gaps_over_1_01s.sum()),
              "scope": "Raw SEC counters in selected instrument states; not LET, transported dose or hazard limits"}
    pd.DataFrame([result]).to_csv(run.path("crater_support_summary.csv"), index=False)
    return result


def sample_record_indices(records, count):
    """Distributed contiguous blocks limit random disk I/O; not random sampling."""
    n = min(records, count)
    if records <= 0 or n <= 0:
        raise ValueError("Positive sample/source count required")
    if n < 32 or records < 2*n:
        return np.unique(np.linspace(0, records-1, n, dtype=np.int64))
    edges = np.linspace(0, records, 33, dtype=np.int64)
    widths = np.full(32, n//32, dtype=np.int64)
    widths[:n % 32] += 1
    starts = edges[:-1] + (np.diff(edges)-widths)//2
    starts[0], starts[-1] = 0, records-widths[-1]
    indices = np.concatenate([np.arange(start, start+width) for start, width in zip(starts, widths)])
    if len(indices) != n or len(np.unique(indices)) != n:
        raise ValueError("Invalid block sampling plan")
    return indices


def primary_sample(label, table_path, count=20000):
    """Deterministic distributed-block sample, not event-rate or random sampling."""
    root, table, fields = pds4_definition(label)
    areas = [area for area in root if table in list(area)]
    if len(areas) != 1 or areas[0].findtext("p:File/p:file_name", namespaces=NS) != table_path.name:
        raise ValueError("Primary label/table identity mismatch")
    if not table.tag.endswith("Table_Character"):
        raise ValueError("Expected fixed-width primary table")
    records = int(table.findtext("p:records", namespaces=NS))
    length = int(table.findtext(".//p:record_length", namespaces=NS))
    offset = int(table.findtext("p:offset", namespaces=NS))
    if table_path.stat().st_size != offset + records*length or records <= 0 or count <= 0:
        raise ValueError("Primary table size/count mismatch")
    indices = sample_record_indices(records, count)
    cuts = np.r_[0, np.flatnonzero(np.diff(indices) != 1)+1, len(indices)]
    blocks = []
    with table_path.open("rb") as stream:
        for a, b in zip(cuts[:-1], cuts[1:]):
            stream.seek(offset+int(indices[a])*length)
            block = stream.read(int(b-a)*length)
            if len(block) != (b-a)*length:
                raise ValueError("Truncated primary sample block")
            blocks.append(block)
    packed = b"".join(blocks)
    frame, units = {}, {}
    required = {"TIME", "DQI"} | {f"{field} Item {d}" for field in ["ENERGY", "LET", "MAXSIGFLAGS", "GTLLDFLAGS"] for d in range(1,7)}
    for field in fields:
        name = field.findtext("p:name", namespaces=NS)
        if name not in required:
            continue
        if field.find("p:scaling_factor", NS) is not None or field.find("p:value_offset", NS) is not None:
            raise ValueError("Unexpected primary calibration transform")
        start = int(field.findtext("p:field_location", namespaces=NS))-1
        width = int(field.findtext("p:field_length", namespaces=NS))
        if start < 0 or start+width > length:
            raise ValueError("Field outside primary record")
        text = pd.Series(np.ndarray((len(indices),), dtype=f"S{width}", buffer=packed,
                                    offset=start, strides=(length,)).astype(str)).str.strip().str.strip('"')
        if name == "TIME":
            frame[name] = text
        else:
            numeric = pd.to_numeric(text.replace("", np.nan), errors="raise")
            for constant in field.findall("p:Special_Constants/*", NS):
                if constant.tag.split("}")[-1].endswith("constant"):
                    numeric = numeric.mask(numeric.eq(float(constant.text)))
            frame[name] = numeric
        units[name] = field.findtext("p:unit", namespaces=NS)
    if set(frame) != required:
        raise ValueError("Missing primary fields")
    for d in range(1,7):
        if units[f"ENERGY Item {d}"] != "keV" or units[f"LET Item {d}"] != "keV/micron":
            raise ValueError("Unexpected deposited energy/LET units")
    result = pd.DataFrame(frame)
    result["source_record_index"] = indices
    return result, records


def primary(run, config, sample):
    days = config["primary_days"]
    if sample:
        days = [days[0], days[len(days)//2], days[-1]]
    coverage, summaries, dqi = [], [], []
    for i, day in enumerate(days):
        paths = [external_input(run, config, f) for f in day["files"]]
        label = next(p for p in paths if p.suffix.lower() == ".xml")
        tab = next(p for p in paths if p.suffix.lower() == ".tab")
        frame, total = primary_sample(label, tab, config["primary_sample_records_per_day"])
        timestamps = pd.to_datetime(frame.TIME, utc=True)
        if not timestamps.dt.strftime("%Y-%m-%d").eq(day["date"]).all() or not timestamps.is_monotonic_increasing:
            raise ValueError("Primary sample date/order mismatch")
        # Compare several sampled positions against the established sequential reader.
        first = next(pds4_chunks(label, columns=["TIME", "DQI", "LET Item 1"], chunk_rows=4))
        for name in first.columns:
            a, b = frame[name].iloc[0], first[name].iloc[0]
            if not (a == b or (pd.isna(a) and pd.isna(b))):
                raise ValueError("Sample decoding disagrees with established reader")
        coverage.append({"date": day["date"], "source_records": total, "sampled_records": len(frame),
                         "sample_start": timestamps.min(), "sample_end": timestamps.max(),
                         "sampling": "distributed_contiguous_record_blocks_including_endpoints_not_random_or_complete_day"})
        for value, n in frame.DQI.value_counts(dropna=False).items():
            dqi.append({"date": day["date"], "DQI": value, "sampled_records": int(n),
                        "quality_interpretation": "DQI semantics not adopted; not certified qualified"})
        for detector in range(1,7):
            energy, let = frame[f"ENERGY Item {detector}"], frame[f"LET Item {detector}"]
            diagnostic = (np.isfinite(energy)&np.isfinite(let)&energy.gt(0)&let.gt(0)
                          &frame[f"MAXSIGFLAGS Item {detector}"].eq(0)&frame[f"GTLLDFLAGS Item {detector}"].eq(1))
            x = let.loc[diagnostic]
            summaries.append({"date": day["date"], "detector": detector, "sampled_records": len(frame),
                              "diagnostic_selected_records": int(diagnostic.sum()),
                              "sampled_LET_median": x.median(), "sampled_LET_p95": x.quantile(.95),
                              "sampled_LET_max": x.max(), "unit": "keV/micron in silicon",
                              "scope": "flag-selected sample diagnostic, not full quality qualification, spectrum, event rate or crew dose"})
        print("Primary sampled days:", i+1, "/", len(days), flush=True)
    pd.DataFrame(coverage).to_csv(run.path("primary_sample_coverage.csv"), index=False)
    pd.DataFrame(summaries).to_csv(run.path("primary_sample_LET_diagnostics.csv"), index=False)
    pd.DataFrame(dqi).to_csv(run.path("primary_sample_DQI_context.csv"), index=False)
    return {"days": len(days), "source_records": sum(x["source_records"] for x in coverage),
            "sampled_records": sum(x["sampled_records"] for x in coverage),
            "scope": "Sparse monthly days and deterministic distributed-block samples; DQI response not qualified, no event census or dose"}


def thermal(run, config, sample):
    parts = [input_csv(run, source, "dated_thermal_support.csv") for source in config["thermal_runs"]]
    combined = pd.concat(parts, ignore_index=True)
    if combined.job_id.duplicated().any():
        raise ValueError("Thermal history contains repeated query jobs")
    combined.to_csv(run.path("dated_thermal_support.csv"), index=False)
    flags = pd.concat([input_csv(run, source, "dated_thermal_quality_flags.csv") for source in config["thermal_runs"]], ignore_index=True)
    flags.to_csv(run.path("dated_thermal_quality_flags.csv"), index=False)
    return {"query_products": len(combined), "regions": combined.region.nunique(),
            "query_rows": int(combined.rows.sum()), "strict_rows": int(combined.strict_rows.sum()),
            "scope": "Combined checked query cohorts; query overlaps not removed or claimed independent"}


def execute(kind, sample=False):
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if config["schema"] != 1:
        raise ValueError("Unsupported radiation refresh configuration")
    processors = {"goes": goes, "crater": crater, "primary": primary, "thermal": thermal}
    if kind not in processors:
        raise ValueError("Unknown analysis kind")
    stage = "analysis/stage3_radiation_refresh_"+kind+("_sample" if sample else "")
    with LocalRun(ROOT, stage, config, NOTEBOOK) as run:
        for path in [CONFIG, Path(__file__), Path(__file__).with_name("stage3_mission_eda.py"),
                     Path(__file__).with_name("stage3_expanded_eda.py"),
                     Path(__file__).with_name("stage3_annual_radiation_eda.py"),
                     LOCAL / "EDA/shared/research_p1_readers.py"]:
            run.input(path)
        findings = processors[kind](run, config, sample)
        findings.update(sample=sample, acquisition_cutoff_utc=config["acquisition_cutoff_utc"],
                        no_new_safety_cutoffs=True, candidate_operational_conclusion="Unknown")
        run.path("findings.json").write_text(json.dumps(findings, indent=2, default=int), encoding="utf-8")
        folder = run.directory
    print(json.dumps(findings, indent=2, default=int), flush=True)
    return folder, findings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["goes", "crater", "primary", "thermal"])
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()
    print(execute(args.kind, args.sample)[0])
