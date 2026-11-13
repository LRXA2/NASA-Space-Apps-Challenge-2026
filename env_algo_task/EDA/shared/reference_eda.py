"""Read and summarize local reference experiments; no mission capability defaults."""
from datetime import datetime, timedelta
from hashlib import sha256
import io
from pathlib import Path, PurePosixPath
import re
import zipfile

import numpy as np
import pandas as pd
from scipy.io import loadmat

from research_p1_readers import NS, pds4_definition, read_pds4

# Transcribed from the README associated with each cell, not operating limits.
STOP_V = {5: 2.7, 6: 2.5, 7: 2.2, 18: 2.5, 33: 2.0, 34: 2.2, 36: 2.7,
          38: 2.2, 39: 2.5, 40: 2.7}
for _start in [25, 29, 41, 45, 49, 53]:
    STOP_V.update(dict(zip(range(_start, _start + 4), [2.0, 2.2, 2.5, 2.7])))


def checked_member(package, item, limit):
    name = PurePosixPath(item.filename)
    if name.is_absolute() or ".." in name.parts or "\\" in item.filename:
        raise ValueError("Unsafe archive member name")
    if item.is_dir() or item.file_size > limit:
        raise ValueError("Unexpected archive member type/size")
    payload = package.read(item)  # ZipFile checks CRC; nothing is extracted.
    if len(payload) != item.file_size:
        raise ValueError("Truncated archive member")
    return payload


def iter_battery_cells(archive, inventory, documents, cell_limit=None):
    """Yield unique cell histories; record identical re-packaging, reject conflicts."""
    if cell_limit is not None and (type(cell_limit) is not int or cell_limit < 1):
        raise ValueError("Cell limit must be positive or None")
    seen, yielded = {}, 0
    with zipfile.ZipFile(archive) as outer:
        nested = sorted(i.filename for i in outer.infolist() if i.filename.lower().endswith(".zip"))
        if not nested:
            raise ValueError("Expected nested battery packages")
        for member in nested:
            payload = checked_member(outer, outer.getinfo(member), 128 * 1024**2)
            with zipfile.ZipFile(io.BytesIO(payload)) as inner:
                if sum(i.file_size for i in inner.infolist()) > 128 * 1024**2:
                    raise ValueError("Nested package exceeds bounded uncompressed size")
                protocols = {}
                for info in inner.infolist():
                    if "readme" not in info.filename.lower():
                        continue
                    text = checked_member(inner, info, 128 * 1024).decode("utf-8").replace("\r", "")
                    key = sha256(text.encode()).hexdigest()
                    documents[key] = {"text": text, "protocol_description": text.split("Files:")[0].strip()}
                    for cell in set(re.findall(r"\bB\d{4}(?=\.mat\b)", text, flags=re.I)):
                        if cell.upper() in protocols and protocols[cell.upper()] != key:
                            raise ValueError("Ambiguous cell README")
                        protocols[cell.upper()] = key
                for info in sorted(inner.infolist(), key=lambda i: i.filename):
                    if not info.filename.lower().endswith(".mat"):
                        continue
                    cell = Path(info.filename).stem.upper()
                    if not re.fullmatch(r"B\d{4}", cell) or cell not in protocols or int(cell[1:]) not in STOP_V:
                        raise ValueError(f"Unreviewed battery identity/protocol: {cell}")
                    raw = checked_member(inner, info, 64 * 1024**2)
                    digest = sha256(raw).hexdigest()
                    if cell in seen and seen[cell] != digest:
                        raise ValueError(f"Different histories share cell ID {cell}; explicit reconciliation needed")
                    duplicate = cell in seen
                    inventory.append({"cell_id": cell, "outer_member": member, "inner_member": info.filename,
                                      "bytes": len(raw), "sha256": digest, "duplicate_history": duplicate,
                                      "protocol_id": protocols[cell]})
                    if duplicate:
                        continue
                    seen[cell] = digest
                    content = loadmat(io.BytesIO(raw), simplify_cells=True)
                    if cell not in content or set(content[cell]) != {"cycle"}:
                        raise ValueError(f"Unexpected MATLAB schema for {cell}")
                    records = content[cell]["cycle"]
                    records = [records] if isinstance(records, dict) else list(records)
                    yield {"cell_id": cell, "protocol_id": protocols[cell], "mat_sha256": digest,
                           "documented_stop_voltage_V": STOP_V[int(cell[1:])]}, records
                    yielded += 1
                    if cell_limit is not None and yielded >= cell_limit:
                        return


def real_scalar(value):
    a = np.asarray(value)
    if a.size == 0:
        return np.nan
    if a.size != 1 or np.iscomplexobj(a):
        raise ValueError("Expected one real scalar, not a spectrum/vector/complex value")
    return float(a.reshape(-1)[0])


def matlab_start(value):
    a = np.asarray(value, dtype=float).reshape(-1)
    if len(a) != 6 or not np.isfinite(a).all() or not np.equal(a[:5], np.floor(a[:5])).all():
        raise ValueError("Invalid MATLAB date vector")
    return (datetime(*(int(x) for x in a[:5])) + timedelta(seconds=float(a[5]))).isoformat()


def impedance_estimate(value, name):
    """Preserve complex source fit estimates; never coerce them into resistances."""
    a = np.asarray(value).reshape(-1)
    result = {name + "_ohm": np.nan, name + "_source_real_ohm": np.nan,
              name + "_source_imag_ohm": np.nan, name + "_estimate_status": "missing"}
    if not len(a):
        return result
    if len(a) != 1:
        raise ValueError("Unexpected vector where an impedance fit scalar is documented")
    z = complex(a[0])
    result[name + "_source_real_ohm"], result[name + "_source_imag_ohm"] = z.real, z.imag
    result[name + "_estimate_status"] = ("nonfinite" if not np.isfinite(z) else
                                          "complex_estimate" if z.imag != 0 else "real_scalar")
    if result[name + "_estimate_status"] == "real_scalar":
        result[name + "_ohm"] = z.real
    return result


def trace_summary(data):
    """Observed trace integrals; never bridge missing endpoints or sort time."""
    result = {"observed_discharge_Ah": np.nan, "observed_discharge_Wh": np.nan,
              "trace_span_s": np.nan, "finite_interval_fraction": np.nan,
              "integration_status": "missing_or_mismatched_vectors"}
    keys = ["Time", "Voltage_measured", "Current_measured", "Temperature_measured"]
    arrays = {key: np.asarray(data.get(key, []), dtype=float).reshape(-1) for key in keys}
    lengths = {key: len(value) for key, value in arrays.items()}
    result.update({key + "_samples": count for key, count in lengths.items()})
    if len(set(lengths.values())) != 1 or lengths["Time"] < 2:
        return result
    time, voltage, current, temperature = (arrays[key] for key in keys)
    dt = np.diff(time)
    finite = np.isfinite(time) & np.isfinite(voltage) & np.isfinite(current)
    valid = finite[:-1] & finite[1:] & (dt > 0)
    result.update({"nonpositive_time_steps": int(np.sum(np.isfinite(dt) & (dt <= 0))),
                   "invalid_trace_samples": int((~finite).sum()),
                   "missing_temperature_samples": int((~np.isfinite(temperature)).sum()),
                   "finite_interval_fraction": float(valid.mean()),
                   "trace_span_s": float(time[-1] - time[0]) if np.isfinite(time[[0, -1]]).all() else np.nan,
                   "median_positive_time_step_s": float(np.median(dt[dt > 0])) if np.any(dt > 0) else np.nan,
                   "maximum_positive_time_step_s": float(dt[dt > 0].max()) if np.any(dt > 0) else np.nan,
                   "voltage_min_V": float(np.nanmin(voltage)) if np.isfinite(voltage).any() else np.nan,
                   "voltage_max_V": float(np.nanmax(voltage)) if np.isfinite(voltage).any() else np.nan,
                   "current_min_A": float(np.nanmin(current)) if np.isfinite(current).any() else np.nan,
                   "current_max_A": float(np.nanmax(current)) if np.isfinite(current).any() else np.nan,
                   "temperature_max_C": float(np.nanmax(temperature)) if np.isfinite(temperature).any() else np.nan,
                   "temperature_min_C": float(np.nanmin(temperature)) if np.isfinite(temperature).any() else np.nan})
    if valid.any():
        discharge = np.maximum(-current, 0)
        result["observed_discharge_Ah"] = float(np.sum((discharge[:-1][valid] + discharge[1:][valid]) * dt[valid] / 2) / 3600)
        power = discharge * voltage
        result["observed_discharge_Wh"] = float(np.sum((power[:-1][valid] + power[1:][valid]) * dt[valid] / 2) / 3600)
        result["integration_status"] = "all_intervals" if valid.all() else "partial_observed_intervals"
    else:
        result["integration_status"] = "no_valid_intervals"
    return result


def battery_record_summary(info, records):
    rows, discharge_index = [], 0
    for index, record in enumerate(records, 1):
        mode = str(record["type"])
        if mode not in {"charge", "discharge", "impedance"}:
            raise ValueError(f"Unexpected battery mode {mode}")
        discharge_index += mode == "discharge"
        data = record["data"]
        row = {**info, "record_index": index, "mode": mode,
               "discharge_index": discharge_index if mode == "discharge" else np.nan,
               "ambient_temperature_C": real_scalar(record["ambient_temperature"]),
               "recorded_start_naive": matlab_start(record["time"]),
               "recorded_fields": ";".join(sorted(data)),
               "reported_capacity_Ah": real_scalar(data.get("Capacity", [])),
               "reported_capacity_source_size": int(np.asarray(data.get("Capacity", [])).size)}
        row.update(impedance_estimate(data.get("Re", []), "Re"))
        row.update(impedance_estimate(data.get("Rct", []), "Rct"))
        if mode in {"charge", "discharge"}:
            row.update(trace_summary(data))
            row["peak_temperature_minus_ambient_C"] = row.get("temperature_max_C", np.nan) - row["ambient_temperature_C"]
        else:
            row["integration_status"] = "not_time_series"
            for name in ["Battery_impedance", "Rectified_Impedance", "Rectified_impedance"]:
                if name in data:
                    values = np.asarray(data[name]).reshape(-1)
                    row[name + "_samples"] = len(values)
                    row[name + "_nonfinite"] = int((~np.isfinite(values)).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def relative_capacity(discharge):
    result = discharge.sort_values(["cell_id", "record_index"]).copy()
    valid = result.reported_capacity_Ah.where(result.reported_capacity_Ah.gt(0) & np.isfinite(result.reported_capacity_Ah))
    result["first_positive_reported_capacity_Ah"] = valid.groupby(result.cell_id).transform("first")
    result["relative_reported_capacity"] = result.reported_capacity_Ah / result.first_positive_reported_capacity_Ah
    return result


SOIL_RUNS = {
    11: (1, "cone", "adjacent north trench end"),
    12: (2, "cone", "trench bottom"),
    13: (3, "cone", "rover tracks"),
    14: (4, "cone", "adjacent rover tracks"),
    15: (5, "plate", "trench bottom"),
    16: (6, "plate", "outside trench; documented edge collapse"),
}


def soil_table(label):
    """Reuse the existing label-driven reader; retain raw source values/row order."""
    root, table, fields = pds4_definition(label)
    expected = {"LOAD": "Newton", "STRESS": "Newton/cm^2", "PENETRATION_DEPTH": "Centimeter"}
    units = {f.findtext("p:name", namespaces=NS): f.findtext("p:unit", namespaces=NS) for f in fields}
    if any(units.get(key) != value for key, value in expected.items()):
        raise ValueError("Unreviewed soil units")
    suffix = int(label.stem.rsplit("_", 1)[1])
    if suffix not in SOIL_RUNS:
        raise ValueError("Unexpected soil run")
    frame = read_pds4(label)
    run, geometry, location = SOIL_RUNS[suffix]
    raw = label.with_suffix(".tab").read_bytes().splitlines()
    if len(raw) != len(frame):
        raise ValueError("Soil source row mismatch")
    frame["raw_record"] = [r.decode("ascii") for r in raw]
    frame["source_label"] = label.name
    frame["source_row"] = np.arange(1, len(frame) + 1)
    frame["run"] = run
    frame["geometry"] = geometry
    frame["location_context"] = location
    frame["documented_depth_limitation"] = run >= 3
    frame["documented_trench_collapse"] = run == 6
    frame["label_start_utc"] = root.findtext(".//p:start_date_time", namespaces=NS)
    frame["stress_kPa"] = frame.STRESS * 10
    frame["nominal_area_cm2"] = 3.22 if geometry == "cone" else 2.54 * 12.7
    valid = frame.LOAD.gt(0) & frame.STRESS.gt(0)
    frame["implied_area_cm2"] = (frame.LOAD / frame.STRESS).where(valid)
    frame["stress_minus_force_over_area_N_cm2"] = frame.STRESS - frame.LOAD / frame.nominal_area_cm2
    frame["cone_depth_correction_cm"] = frame.CORRECTION - frame.PENETRATION_DEPTH if "CORRECTION" in frame else np.nan
    metadata = [{"run": run, "field": key, "unit": value} for key, value in units.items()]
    return frame, metadata
