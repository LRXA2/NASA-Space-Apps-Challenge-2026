"""Validate every JSON file tracked by Git."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def tracked_json_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.json"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return [root / name.decode("utf-8") for name in result.stdout.split(b"\0") if name]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    failures: list[str] = []
    files = tracked_json_files(root)

    for path in files:
        try:
            with path.open("r", encoding="utf-8-sig") as handle:
                json.load(handle)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            failures.append(f"{path.relative_to(root)}: {error}")

    if failures:
        print("Invalid tracked JSON files:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(f"Validated {len(files)} tracked JSON files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

