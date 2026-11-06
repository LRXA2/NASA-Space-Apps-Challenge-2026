"""Inventory/download the environmental datasets and required Moon EDA support.

Reuses the existing downloaders, their manifests and verification behavior:
  * TerraClimate v1.1, 2015-2024, five variables, original three Earth sites.
  * The same climate collection for Death Valley and Wadi Rum.
  * Diviner south-polar seasonal tables and their source labels only.
  * Ten south-polar 2016 illumination/visibility GeoTIFFs only.

Inventory only by default. Add --download for data transfers, or --dry-run
to print commands without network access or filesystem writes. No processing,
Excel conversion, OSM or Mars downloads are performed. The default also restores
the original seven SDEM regions, six LOLA maps and documented illumination units
needed by the Moon EDA. Existing verified files are reused by the original handlers.

Run from the project root with the project's Python 3.12 environment:
  python "darrel stuff/download_script/download_environmental.py" --dry-run
  python "darrel stuff/download_script/download_environmental.py"
  python "darrel stuff/download_script/download_environmental.py" --download
  python "darrel stuff/download_script/download_environmental.py" --restore-moon-support --download

Default output: darrel stuff/data, created if missing before running downloaders.
The original download scripts are reused without modification.

Child dependencies: requests, beautifulsoup4, numpy, scipy.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


DATASETS = ("earth-climate", "earth-climate-expansion", "lunar-temperature", "lunar-illumination")
SCRIPT_DIRECTORY = Path(__file__).resolve().parents[2] / "download scripts"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data"


def build_commands(output: Path, datasets: list[str], *, download: bool = False,
                   timeout: int = 120, attempts: int = 3) -> list[tuple[str, list[str]]]:
    """Build a fixed P1-only plan; do not import children, write files or use the network."""
    if not datasets or len(datasets) != len(set(datasets)) or not set(datasets) <= set(DATASETS):
        raise ValueError("Select unique datasets from the four P1 entries")
    if type(timeout) is not int or timeout < 1 or type(attempts) is not int or attempts < 1:
        raise ValueError("Timeout and attempts must be positive integers")
    output = output.expanduser().resolve()
    climate = ["--start-year", "2015", "--end-year", "2024",
               "--variables", "tmin", "tmax", "ppt", "ws", "srad"]
    jobs = {
        "earth-climate": (
            "download_terraclimate.py", ["--project-areas", *climate],
            output / "earth/terraclimate", "--attempts"),
        "earth-climate-expansion": (
            "download_terraclimate.py",
            ["--bbox", "-117.1", "36.0", "-116.6", "36.5",
             "--bbox", "35.2", "29.4", "35.65", "29.8", *climate],
            output / "earth/environment_expansion/20261030/terraclimate", "--attempts"),
        "lunar-temperature": (
            "download_diviner_south_polar.py", ["--collections", "seasonal"],
            output / "moon/diviner", "--attempts"),
        "lunar-illumination": (
            "download_lunar_illumination_2016.py", ["--hemisphere", "south", "--skip-img"],
            output / "moon/illumination_2016", "--retries"),
    }
    commands = []
    for name in datasets:
        script, selection, destination, retry_flag = jobs[name]
        command = [sys.executable, str(SCRIPT_DIRECTORY / script), *selection,
                   "--output", str(destination), "--timeout", str(timeout), retry_flag, str(attempts)]
        if download:
            command.append("--download")
        commands.append((name, command))
    return commands


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--datasets", choices=DATASETS, nargs="+", default=None,
                        help="Restrict to selected P1 entries (default: all four plus required Moon support)")
    parser.add_argument("--restore-moon-support", action="store_true",
                        help="Restore only Moon support, or add support to an explicit --datasets selection")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Data root, created if missing (default: darrel stuff/data)")
    parser.add_argument("--download", action="store_true", help="Transfer source files; default is inventory only")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan only, without network or writes")
    parser.add_argument("--timeout", type=int, default=120, help="Child HTTP read timeout in seconds")
    parser.add_argument("--attempts", type=int, default=3, help="Child transfer attempts per source URL")
    args = parser.parse_args(argv)
    selected = args.datasets if args.datasets is not None else ([] if args.restore_moon_support else list(DATASETS))
    try:
        commands = build_commands(args.output, selected, download=args.download,
                                  timeout=args.timeout, attempts=args.attempts) if selected else []
        if args.restore_moon_support or args.datasets is None:
            if args.timeout < 1 or args.attempts < 1:
                raise ValueError("Timeout and attempts must be positive integers")
            command = [sys.executable, str(Path(__file__).resolve().with_name("download_moon_support.py")),
                       "--output", str(args.output.expanduser().resolve()),
                       "--timeout", str(args.timeout), "--attempts", str(args.attempts)]
            if args.download:
                command.append("--download")
            commands.append(("moon-support", command))
    except ValueError as error:
        parser.error(str(error))
    # Check all required child scripts before any inventory or data transfer starts.
    for _, command in commands:
        if not Path(command[1]).is_file():
            parser.error(f"Required downloader is missing: {command[1]}")
    mode = "download" if args.download else "inventory only"
    print(f"Environmental scope: {', '.join(name for name, _ in commands)} ({mode}).", flush=True)
    for name, command in commands:
        print(f"\n{name}:\n  {subprocess.list2cmdline(command)}", flush=True)
    if args.dry_run:
        print("\nDry run only: no network requests, manifests or datasets written.")
        return 0
    output = args.output.expanduser().resolve()
    try:
        # Reuse an existing directory; create it and any missing parents otherwise.
        output.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        print(f"Unable to create data directory {output}: {error}", file=sys.stderr)
        return 1
    print("\nRunning sequentially. Each downloader retains its own manifests and resume/verification rules.", flush=True)
    try:
        for name, command in commands:
            print(f"\nStarting {name}...", flush=True)
            subprocess.run(command, check=True)
    except subprocess.CalledProcessError as error:
        print(f"Stopped: {name} failed with exit code {error.returncode}; remaining entries were not run.", file=sys.stderr)
        return error.returncode if error.returncode > 0 else 1
    except OSError as error:
        print(f"Unable to start {name}: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted. Rerun with the same options to reuse existing downloads/partials.", file=sys.stderr)
        return 130
    print(f"\nAll selected environmental {mode} jobs completed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
