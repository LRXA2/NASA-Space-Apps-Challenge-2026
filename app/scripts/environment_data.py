"""Turn the environment scorer's output into the app's scenario records.

Reads compact output, or detailed output (compact columns plus *_coverage and *_details), which adds
each hard gate's value, threshold, verdict and reason.

Standard library only, so the same code runs in the export and in the browser (Pyodide)
when a user uploads their own scorer input. Values are copied, never recomputed.
"""

from __future__ import annotations

import json
import math
import re

ASSESSMENTS = ("operations", "survival")
STATUSES = ("Pass", "Fail", "Unknown")
FIELDS = ("status", "fail_reason")

# eda IDs -> (display name, terrain region source ID or None). From env_algo_task/env_pipeline/README.md.
# Confirmed by Darrel (team blocker D3, 2026-11-14): only eda_001-eda_007 have terrain.
ARTEMIS = {
    "eda_001": ("Leibnitz Beta Plateau", "A3CLR22_10_Leibnitz_Beta_Plateau"),
    "eda_002": ("Malapert Massif", "A3CLR22_11_Malapert_Massif"),
    "eda_003": ("de Gerlache–Kocher Massif", "A3CLR22_12_deGerlache_Kocher_Massif"),
    "eda_004": ("Haworth", "A3CLR22_2_Haworth"),
    "eda_005": ("Faustini Rim A", "A3CLR22_3_Faustini_Rim_A"),
    "eda_006": ("de Gerlache Rim 2", "A3CLR22_4_deGerlache_Rim_2"),
    "eda_007": ("Connecting Ridge Extension", "A3CLR22_5_Connecting_Ridge_Extension"),
    "eda_008": ("Peak Near Shackleton", None),
    "eda_009": ("Connecting Ridge", None),
    "eda_010": ("de Gerlache Rim 1", None),
    "eda_011": ("Nobile Rim 1", None),
    "eda_012": ("Nobile Rim 2", None),
    "eda_013": ("Amundsen Rim", None),
    "eda_014": ("Peak near Cabeus B", None),
    "eda_015": ("Mons Mouton Plateau", None),
    "eda_016": ("Mons Mouton", None),
    "eda_017": ("Slater Plain", None),
}
EVIDENCE = {
    "measured_maps": "Four map values (Sun, Earth and sky visibility, permanent shadow) come from LOLA maps. "
    "Every other input is a test assumption.",
    "assumed": "Every input is an assumed value with no measured footprint.",
    "apollo": "Combines Apollo mission records, models and test assumptions.",
    "uploaded": "Values supplied by the user, not checked against any measurement.",
}
DOMAIN_LABELS = {
    "solar_illumination": "Solar illumination",
    "plasma_charging": "Plasma charging",
    "earth_visibility": "Earth visibility",
    "uv": "UV",
}
TEST_PREFIXES = ("synthetic_", "dummy_")
APOLLO = re.compile(r"^apollo_(\d+)_(.+?)(?:_assumed)?$")


class EnvironmentDataError(ValueError):
    """An environment file the app refuses to publish."""


def domain_label(name: str) -> str:
    return DOMAIN_LABELS.get(name, name.replace("_", " ").capitalize())


def _score(text: str | None, where: str) -> float | None:
    """A 0-100 score, or None when the source leaves it blank. Zero stays zero."""
    if text is None or text.strip() == "":
        return None
    try:
        value = float(text)
    except ValueError as error:
        raise EnvironmentDataError(f"{where} is not a number: {text!r}") from error
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise EnvironmentDataError(f"{where} is outside 0-100: {text!r}")
    return value


def check_columns(columns: list[str]) -> dict[str, list[str]]:
    """Return each assessment's domain names, read by prefix. Reject the old single-score format."""
    if "final_habitability_score" in columns or "hard_gate_status" in columns:
        raise EnvironmentDataError(
            "This is the scorer's old single-score format (final_habitability_score). "
            "Rerun env_pipeline.py with --compact to get Operations and Survival scores."
        )
    required = ["ID"] + [f"{a}_{field}" for a in ASSESSMENTS for field in (*FIELDS, "score")]
    missing = [name for name in required if name not in columns]
    if missing:
        raise EnvironmentDataError(f"The environment file is missing columns: {', '.join(missing)}")
    domains = {}
    known = set(required)
    for assessment in ASSESSMENTS:
        pattern = re.compile(rf"^{assessment}_(.+)_score$")
        domains[assessment] = [m.group(1) for name in columns if (m := pattern.match(name))]
        known.update(f"{assessment}_{d}_score" for d in domains[assessment])
    unknown = [name for name in columns if name not in known and not name.endswith(("_coverage", "_details"))]
    if unknown:
        raise EnvironmentDataError(f"Unrecognised environment columns: {', '.join(unknown)}")
    return domains


def scenario_kind(scenario_id: str) -> str | None:
    """artemis, apollo, or None for test rows the app never shows. Unknown IDs are refused."""
    if scenario_id in ARTEMIS:
        return "artemis"
    if APOLLO.match(scenario_id):
        return "apollo"
    if scenario_id.startswith(TEST_PREFIXES):
        return None
    raise EnvironmentDataError(f"Unknown environment ID {scenario_id!r}: not eda_001-eda_017, Apollo or a test row")


# The scorer writes gate verdicts as Passed/Failed; the app shows Pass/Fail (Darrel, D2).
GATE_STATUS = {"Passed": "Pass", "Failed": "Fail", "Unknown": "Unknown"}
OPERATORS = {"above_threshold": "above", "ge": "above", "below_threshold": "below", "le": "below", "between": "between"}


def _number(value: object, where: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise EnvironmentDataError(f"{where} is not a finite number: {value!r}")
    return float(value)


def column_label(column: str) -> str:
    return column.replace("_", " ").capitalize()


def gate(entry: object, where: str) -> dict:
    """One hard-gate check, copied from the scorer's hard_gate_details. Nothing is recomputed."""
    if not isinstance(entry, dict) or not isinstance(entry.get("condition"), dict):
        raise EnvironmentDataError(f"{where}: a hard gate entry is not an object with a condition")
    condition = entry["condition"]
    operator = OPERATORS.get(condition.get("operator"))
    status = GATE_STATUS.get(entry.get("status"))
    if operator is None or status is None:
        raise EnvironmentDataError(
            f"{where}: unrecognised gate operator {condition.get('operator')!r} or status {entry.get('status')!r}"
        )
    column = str(entry.get("column", ""))
    if not column:
        raise EnvironmentDataError(f"{where}: a hard gate entry has no column")
    here = f"{where} {column}"
    threshold = _number(condition.get("threshold"), f"{here} threshold")
    configured = _number(entry.get("configured_threshold"), f"{here} configured_threshold")
    record = {
        "domain": str(entry.get("domain", "")),
        "domain_label": domain_label(str(entry.get("domain", ""))),
        "column": column,
        "label": column_label(column),
        "unit": str(entry.get("unit", "")),
        "value": _number(entry.get("value"), f"{here} value"),
        "operator": operator,
        "threshold": threshold,
        "lower": _number(condition.get("lower"), f"{here} lower"),
        "upper": _number(condition.get("upper"), f"{here} upper"),
        # Set only when the scorer capped the threshold to a shorter time window.
        "configured_threshold": configured if configured is not None and configured != threshold else None,
        "window_hours": _number(entry.get("window_duration_hours"), f"{here} window_duration_hours"),
        "status": status,
        "reason": str(entry.get("reason", "")).strip(),
        "rationale": str(condition.get("rationale", "")).strip(),
    }
    if operator == "between" and (record["lower"] is None or record["upper"] is None):
        raise EnvironmentDataError(f"{here}: a between gate needs lower and upper bounds")
    if operator != "between" and threshold is None:
        raise EnvironmentDataError(f"{here}: an {operator} gate needs a threshold")
    return record


def gates(row: dict[str, str], name: str) -> list[dict] | None:
    """The assessment's hard-gate checks from detailed output, or None for compact output."""
    text = row.get(f"{name}_details")
    if text is None:
        return None
    where = f"{row['ID']} {name}_details"
    try:
        details = json.loads(text) if text.strip() else {}
        raw = details.get("hard_gate_details") if isinstance(details, dict) else None
        entries = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError as error:
        raise EnvironmentDataError(f"{where} is not valid JSON: {error}") from error
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise EnvironmentDataError(f"{where}: hard_gate_details is not a list")
    return [gate(entry, where) for entry in entries]


def assessment(row: dict[str, str], name: str, domains: list[str]) -> dict:
    where = f"{row['ID']} {name}"
    status = row[f"{name}_status"]
    if status not in STATUSES:
        raise EnvironmentDataError(f"{where}_status must be one of {', '.join(STATUSES)}, got {status!r}")
    score = _score(row[f"{name}_score"], f"{where}_score")
    reason = row[f"{name}_fail_reason"].strip()
    return {
        "status": status,
        "score": score,
        "fail_reasons": [part.strip() for part in reason.split(" | ") if part.strip()],
        "domains": [
            {"name": d, "label": domain_label(d), "score": _score(row[f"{name}_{d}_score"], f"{where}_{d}_score")}
            for d in domains
        ],
        # None: compact output, so per-check evidence is not available. []: detailed output with no gates.
        "gates": gates(row, name),
        "coverage": (row.get(f"{name}_coverage") or "").strip() or None,
    }


def scenario(row: dict[str, str], domains: dict[str, list[str]], kind: str) -> dict:
    scenario_id = row["ID"]
    if kind == "artemis":
        name, terrain = ARTEMIS[scenario_id]
        evidence = "measured_maps" if terrain else "assumed"
    elif kind == "apollo":
        match = APOLLO.match(scenario_id)
        site = match.group(2).replace("_", " ").title()
        name, terrain, evidence = f"Apollo {match.group(1)} · {site}", None, "apollo"
    else:
        name, terrain, evidence = scenario_id, None, "uploaded"
    return {
        "id": scenario_id,
        "kind": kind,
        "name": name,
        "terrain_region": terrain,
        "evidence": evidence,
        **{a: assessment(row, a, domains[a]) for a in ASSESSMENTS},
    }


def scenarios_from_rows(columns: list[str], rows: list[dict[str, str]], *, uploaded: bool = False) -> list[dict]:
    """Normalise compact or detailed scorer rows. Uploaded rows keep every ID and are labelled as user-supplied."""
    domains = check_columns(columns)
    ids = [row.get("ID", "") for row in rows]
    if not rows:
        raise EnvironmentDataError("The environment file has no rows")
    if any(not scenario_id for scenario_id in ids) or len(set(ids)) != len(ids):
        raise EnvironmentDataError("Every environment row needs a unique ID")
    result = []
    for row in rows:
        kind = "uploaded" if uploaded else scenario_kind(row["ID"])
        if kind is not None:
            result.append(scenario(row, domains, kind))
    return result
