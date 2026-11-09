"""Stage 3 configured operating-margin checks; no inferred mission/equipment defaults.

Applicability declarations are traceable user/model inputs, not certification.
Only complete declared mandatory checks permit operational preference scoring.
"""
import json
from numbers import Real

import numpy as np
import pandas as pd

from data_maintenance import checked_path

FAMILIES = ["site_and_period", "mission_and_crew", "equipment", "requirements_inventory",
            "consumables", "power", "thermal", "communications", "protection_and_ground_hazards"]


def numeric(value, name, minimum=0, maximum=None):
    if not isinstance(value, Real) or isinstance(value, (bool, np.bool_)) or not np.isfinite(value) or value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"Invalid {name}")
    return float(value)


def timestamp(value):
    t = pd.Timestamp(value)
    if pd.isna(t) or t.tzinfo is None:
        raise ValueError("Mission/evidence timestamps must be explicit timezone-aware UTC/offset times")
    return t.tz_convert("UTC")


def consumable_margin(crew, days, rate, recovery, available, reserve):
    crew = numeric(crew, "crew")
    if crew != int(crew): raise ValueError("Crew count must be an integer")
    days, rate = numeric(days, "duration", 1e-12), numeric(rate, "adopted consumption rate")
    recovery = numeric(recovery, "recovery fraction", 0, 1)
    demand = crew * days * rate * (1 - recovery)
    margin = numeric(available, "available stock") - numeric(reserve, "stock reserve") - demand
    return margin, demand


def intervals(frame, start, stop):
    if frame.empty: raise ValueError("No interval data")
    result = frame.copy()
    result["start_utc"] = [timestamp(t) for t in result.start_utc]
    result["stop_utc"] = [timestamp(t) for t in result.stop_utc]
    result = result.sort_values("start_utc").reset_index(drop=True)
    if (result.start_utc.iloc[0] != start or result.stop_utc.iloc[-1] != stop
            or not result.stop_utc.gt(result.start_utc).all()
            or not np.array_equal(result.start_utc.iloc[1:].to_numpy(), result.stop_utc.iloc[:-1].to_numpy())):
        raise ValueError("Intervals must cover the exact mission window without gaps/overlap")
    result["hours"] = (result.stop_utc - result.start_utc).dt.total_seconds() / 3600
    return result


def power_margin(frame, settings):
    capacity = numeric(settings["battery_usable_Wh"], "usable capacity", 1e-12)
    energy = numeric(settings["initial_energy_Wh"], "initial energy", 0, capacity)
    reserve = numeric(settings["reserve_Wh"], "energy reserve")
    charge = numeric(settings["charge_efficiency"], "charge efficiency", 1e-12, 1)
    discharge = numeric(settings["discharge_efficiency"], "discharge efficiency", 1e-12, 1)
    minimum, unserved = energy, 0.
    for item in frame.itertuples():
        generation = numeric(item.generation_W, "interval-mean generation")
        load = numeric(item.load_W, "interval-mean load")
        hours = numeric(item.hours, "interval hours", 1e-12)
        change = (generation - load) * hours
        trial = energy + (change * charge if change >= 0 else change / discharge)
        minimum = min(minimum, trial)
        unserved += max(0., -trial)
        energy = max(0., min(capacity, trial))
    return minimum - reserve, {"minimum_modelled_energy_Wh": max(0., minimum),
                              "minimum_unclamped_balance_Wh": minimum, "unserved_storage_energy_Wh": unserved}


def thermal_margin(frame, settings):
    low = numeric(settings["minimum_operating_K"], "minimum component limit", 1e-12)
    high = numeric(settings["maximum_operating_K"], "maximum component limit", low)
    lower = pd.to_numeric(frame.minimum_component_K, errors="raise").to_numpy(float)
    upper = pd.to_numeric(frame.maximum_component_K, errors="raise").to_numpy(float)
    if not np.isfinite([lower, upper]).all() or (lower > upper).any() or (lower <= 0).any():
        raise ValueError("Invalid component-response temperatures")
    return min(float(lower.min() - low), float(high - upper.max()))


def communication_margin(frame, allowed_hours):
    longest = current = 0.
    for item in frame.itertuples():
        if not (isinstance(item.contact_available, (bool, np.bool_)) or item.contact_available in {"True", "False"}):
            raise ValueError("Contact interval requires explicit Boolean availability")
        available = item.contact_available in {True, "True"}
        current = 0. if available else current + item.hours
        longest = max(longest, current)
    return numeric(allowed_hours, "maximum allowed outage hours") - longest


def profile_readiness(profile):
    if profile.get("schema") != 1:
        raise ValueError("Unsupported Stage 3 profile schema")
    missing = []
    for name in ["body", "start_utc", "stop_utc", "crew_count", "activities", "equipment_configuration"]:
        if profile.get(name) is None or profile.get(name) == [] or profile.get(name) == {}:
            missing.append(name)
    if profile.get("activities") is not None and (not isinstance(profile["activities"], list)
            or any(not isinstance(a, str) or not a.strip() for a in profile["activities"])):
        raise ValueError("Activities must be a list of named activities")
    if profile.get("equipment_configuration") is not None and not isinstance(profile["equipment_configuration"], dict):
        raise ValueError("Equipment configuration must be an explicit object")
    if profile.get("requirements") is not None and not isinstance(profile["requirements"], list):
        raise ValueError("Requirements must be a list")
    if profile.get("body") not in {None, "Moon"}:
        missing.append("applicable non-lunar candidate environmental evidence (current candidate source is Moon-only)")
    if profile.get("crew_count") is not None:
        c = numeric(profile["crew_count"], "crew count")
        if c != int(c): raise ValueError("Crew count must be integer")
    if profile.get("requirements_inventory_complete") is not True:
        missing.append("complete applicable requirements inventory declaration")
    if not profile.get("requirements"):
        missing.append("nonempty applicable requirements")
    if profile.get("start_utc") and profile.get("stop_utc"):
        if timestamp(profile["stop_utc"]) <= timestamp(profile["start_utc"]): raise ValueError("Invalid mission window")
    return missing


def requirement_margin(kind, frame, settings, start, stop, crew):
    if kind == "consumable":
        if len(frame) != 1: raise ValueError("Consumable evidence must have exactly one adopted rate/stock row")
        row = frame.iloc[0]
        return (*consumable_margin(crew, (stop - start).total_seconds() / 86400,
            row.rate_kg_per_crew_day, row.recovery_fraction, row.available_kg, row.reserve_kg), "kg")
    if kind in {"power", "thermal", "communications"}:
        frame = intervals(frame, start, stop)
    if kind == "power":
        value, details = power_margin(frame, settings)
        return value, json.dumps(details), "Wh"
    if kind == "thermal": return thermal_margin(frame, settings), "component-response envelope, NOT Diviner surface temperature", "K"
    if kind == "communications": return communication_margin(frame, settings["maximum_outage_hours"]), "terrain/relay/link-qualified interval model", "h"
    if kind == "capacity_demand":
        if len(frame) != 1: raise ValueError("One applicable capacity/demand row required")
        row = frame.iloc[0]
        if row.unit != settings["unit"] or row.quantity != settings["quantity"]:
            raise ValueError("Capacity/demand quantity or units do not match the requirement")
        return numeric(row.capacity, "capability") - numeric(row.reserve, "reserve") - numeric(row.demand, "demand"), row.demand, row.unit
    raise ValueError(f"Unsupported requirement model: {kind}")


def assess(candidates, profile, data_root, run=None):
    """Use actual supplied evidence only; malformed evidence fails, absent data is Unknown."""
    missing = profile_readiness(profile)
    checks, summaries = [], []
    requirements = profile.get("requirements") or []
    ids = [r["id"] for r in requirements]
    if len(set(ids)) != len(ids): raise ValueError("Duplicate operational requirement IDs")
    for rule in requirements:
        if type(rule.get("mandatory")) is not bool or not rule.get("source") or not rule.get("reason"):
            raise ValueError("Each requirement needs mandatory Boolean, source and applicability reason")
        if rule.get("kind") not in {"consumable", "power", "thermal", "communications", "capacity_demand"}:
            raise ValueError("Unsupported configured requirement kind")
    if requirements and not any(r["mandatory"] for r in requirements):
        missing = [*missing, "at least one declared mandatory requirement (empty gate cannot pass)"]
    for candidate in candidates.candidate_id:
        rows = []
        rows.append({"requirement": "mission_equipment_requirements_readiness", "mandatory": True,
                     "status": "unknown" if missing else "pass", "margin": np.nan, "unit": None,
                     "reason": "; ".join(missing) if missing else "User-declared complete profile; not certification"})
        if not requirements:
            rows.extend({"requirement": family, "mandatory": True, "status": "unknown", "margin": np.nan,
                         "unit": None, "reason": "Applicable requirement, mission configuration and evidence not supplied"} for family in FAMILIES)
        for rule in requirements:
            row = {"requirement": rule["id"], "mandatory": rule["mandatory"], "status": "unknown",
                   "margin": np.nan, "unit": None, "reason": "Missing applicable candidate/period evidence"}
            item = profile.get("candidate_inputs", {}).get(candidate, {}).get(rule["id"])
            if item and not missing:
                if (item.get("body") != profile["body"] or item.get("support") != "candidate_validated"
                        or item.get("basis") not in {"observed", "modeled"}
                        or timestamp(item["start_utc"]) != timestamp(profile["start_utc"])
                        or timestamp(item["stop_utc"]) != timestamp(profile["stop_utc"])):
                    row["reason"] = "Evidence body, period, support or observation/model basis is inapplicable"
                elif rule["kind"] in {"power", "communications"} and item.get("terrain_aware") is not True:
                    row["reason"] = "Terrain-aware generation/contact evidence is required; sphere geometry cannot pass"
                elif rule["kind"] in {"power", "communications"} and item.get("time_model") != "piecewise_constant":
                    row["reason"] = "Explicit piecewise-constant interval model required; sparse averages cannot imply continuity"
                elif rule["kind"] == "thermal" and item.get("quantity") != "component_response_temperature":
                    row["reason"] = "Surface radiometry cannot substitute for equipment-response temperature"
                else:
                    path = checked_path(data_root, item["input_file"])
                    if not path.is_file(): raise FileNotFoundError(f"Configured operational evidence file is missing: {path}")
                    if run: run.input(path)
                    frame = pd.read_csv(path)
                    margin, detail, unit = requirement_margin(rule["kind"], frame, rule.get("settings", {}),
                        timestamp(profile["start_utc"]), timestamp(profile["stop_utc"]), profile["crew_count"])
                    row.update(status="pass" if margin >= 0 else "fail", margin=margin, unit=unit,
                               reason=rule["reason"], source=item["input_file"], demand_or_detail=str(detail))
            rows.append(row)
        mandatory = [r["status"] for r in rows if r["mandatory"]]
        status = "fail" if "fail" in mandatory else "unknown" if "unknown" in mandatory else "pass"
        checks.extend({"candidate_id": candidate, **row} for row in rows)
        summaries.append({"candidate_id": candidate, "stage3_status": status,
            "mandatory_pass": mandatory.count("pass"), "mandatory_fail": mandatory.count("fail"),
            "mandatory_unknown": mandatory.count("unknown"), "assessment_basis": "configured preliminary model; not certification"})
    return pd.DataFrame(summaries), pd.DataFrame(checks)
