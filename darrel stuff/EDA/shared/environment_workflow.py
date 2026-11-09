"""Local paths/provenance for the environmental notebook ports.

Scientific processing stays in the original notebook code and shared helpers.
Only the Run root and notebook location are adapted to Darrel's workspace.
"""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data_maintenance import atomic_text, cleanup_failed_run

from notebooks.shared.processing import Run, sha256


class LocalRun(Run):
    """Keep the existing Run contracts, writing only to darrel stuff/data/processed."""

    def __init__(self, project_root: Path, stage: str, config: dict, notebook: str):
        self.project_root = project_root.resolve()
        local_root = self.project_root / "darrel stuff"
        notebook_path = (local_root / "EDA" / notebook).resolve()
        if not notebook_path.is_relative_to((local_root / "EDA").resolve()):
            raise ValueError("Notebook must remain inside darrel stuff/EDA")
        super().__init__(local_root, stage, config, notebook)
        self.notebook = notebook_path

    def input(self, path: Path) -> None:
        # Original helpers and source notebooks remain read-only outside Darrel's folder.
        path = path.resolve()
        key = str(path.relative_to(self.project_root))
        if key not in self.record["inputs"]:
            stat = path.stat()
            self.record["inputs"][key] = {
                "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": sha256(path)}

    def __enter__(self):
        super().__enter__()
        self.input(Path(__file__))
        self.save()
        return self

    def save(self):
        atomic_text(self.directory / "provenance.json",
                    json.dumps(self.record, indent=2, default=str))

    def __exit__(self, exc_type, exc, traceback):
        result = super().__exit__(exc_type, exc, traceback)
        if exc_type is not None and self.record["stage"].startswith("analysis/"):
            try:
                cleanup_failed_run(self.directory, self.root / "data")
            except (OSError, ValueError) as error:
                print(f"Failed-run cleanup incomplete; failure evidence retained: {error}", file=sys.stderr)
        return result


def latest_completed_run(project_root: Path, stage: str, run_id: str | None = None) -> Path:
    """Select an explicit run, or the latest completed local run; never use another data root."""
    root = (project_root / "darrel stuff/data/processed").resolve()
    folder = (root / stage).resolve()
    if not folder.is_relative_to(root):
        raise ValueError("Stage escapes the local processed-data directory")
    if run_id is not None:
        candidates = [(folder / run_id).resolve()]
        if not candidates[0].is_relative_to(folder):
            raise ValueError("Run ID escapes its stage")
    else:
        candidates = sorted(folder.iterdir(), reverse=True) if folder.is_dir() else []
    for candidate in candidates:
        manifest = candidate / "provenance.json"
        if not manifest.is_file():
            continue
        record = json.loads(manifest.read_text(encoding="utf-8"))
        if record["status"] == "complete":
            if record["stage"] != stage:
                raise ValueError(f"Unexpected stage in {manifest}")
            print(f"Accepted local {stage} run: {candidate.name}")
            return candidate
    raise FileNotFoundError(
        f"No completed local {stage} run at {folder}. Run its preprocessing notebook first; "
        "partial/failed runs and the original project's data are not substituted.")


def select_climate_manifest(base: Path, expected: set[tuple]) -> tuple[Path, list[dict]]:
    """Use a completed download with the original exact areas, years, variables and bounds."""
    compatible = []
    for path in sorted((base / "manifests").glob("*_run.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        jobs = record.get("jobs", [])
        actual = {(job["area"], job["year"], job["variable"], tuple(job["bounds"])) for job in jobs}
        if record["status"] == "complete" and actual == expected and len(jobs) == len(expected):
            compatible.append((path, jobs))
    if not compatible:
        raise FileNotFoundError(f"No complete exact-selection climate download manifest under {base}")
    return compatible[-1]
