"""Score an uploaded environment CSV with Darrel's unmodified scorer, then normalise it for the app.

Runs in Pyodide (the browser upload) and in CPython (tests). It needs env_pipeline.py, config.yml
and environment_data.py on sys.path / in `folder`. It writes only to a temporary directory.
"""

from __future__ import annotations

import csv
import io
import json
import tempfile
from pathlib import Path

import yaml

import env_pipeline
from environment_data import EnvironmentDataError, scenarios_from_rows

# The errors env_pipeline's own command line turns into a readable message.
SCORER_ERRORS = (ValueError, OSError, csv.Error, yaml.YAMLError)


def score(csv_text: str, folder: str) -> str:
    """Return JSON: {"ok": true, "csv": <scorer output>, "scenarios": [...]} or {"ok": false, "error": "..."}."""
    config = Path(folder) / "config.yml"
    with tempfile.TemporaryDirectory() as work:
        source, output = Path(work) / "upload.csv", Path(work) / "results.csv"
        source.write_text(csv_text, encoding="utf-8", newline="")
        try:
            # Detailed output: the compact columns plus each hard gate's value, threshold and verdict.
            env_pipeline.run(source, output, config, overwrite=True, compact=False)
        except SCORER_ERRORS as error:
            return json.dumps({"ok": False, "error": f"Environmental pipeline error: {error}"})
        text = output.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    rows = list(reader)
    try:
        scenarios = scenarios_from_rows(list(reader.fieldnames or []), rows, uploaded=True)
    except EnvironmentDataError as error:
        return json.dumps({"ok": False, "error": str(error)})
    return json.dumps({"ok": True, "csv": text, "scenarios": scenarios}, ensure_ascii=False)
