"""Download historical TerraClimate V1.1 regional monthly NetCDF subsets.

Requires requests, numpy and scipy. Without --download, only save a request plan.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np
import requests
from scipy.io import netcdf_file

HOST = "https://thredds.northwestknowledge.net/thredds/"
CATALOG = HOST + "catalog/TERRACLIMATE_ALL/data/catalog.xml"
VARIABLES = ("tmin", "tmax", "ppt", "ws", "srad")
AREAS = {
    "northern_arizona": (-112.5, 35.0, -111.0, 36.0),
    "lanzarote": (-13.95, 28.8, -13.35, 29.3),
    "atacama_san_pedro": (-68.6, -23.2, -67.8, -22.6),
}


def catalog_entries(xml: str) -> dict[str, str]:
    ns = "{http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0}"
    root = ET.fromstring(xml)
    if root.tag != ns + "catalog":
        raise ValueError("Unexpected THREDDS catalog")
    return {
        element.attrib["urlPath"]: element.findtext(ns + "date", default="")
        for element in root.iter(ns + "dataset") if "urlPath" in element.attrib
    }


def request_spec(variable: str, year: int, bounds: tuple[float, ...]) -> dict:
    west, south, east, north = bounds
    if not all(math.isfinite(x) for x in bounds) or not (
        -180 <= west < east <= 180 and -90 <= south < north <= 90
    ):
        raise ValueError("Box must satisfy -180 <= west < east <= 180 and -90 <= south < north <= 90")
    return {
        "url": HOST + f"ncss/grid/TERRACLIMATE_ALL/data/TerraClimate_{variable}_{year}.nc",
        "params": {"var": variable, "west": west, "south": south, "east": east,
                   "north": north, "time_start": f"{year}-01-01T00:00:00Z",
                   "time_end": f"{year}-12-31T23:59:59Z", "horizStride": 1,
                   "timeStride": 1, "accept": "netcdf"},
    }


def as_text(value: object) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def validate_netcdf(path: Path, variable: str, year: int, bounds: tuple[float, ...]) -> dict:
    """Inspect packed data without changing the downloaded file."""
    try:
        opened = netcdf_file(str(path), "r", mmap=False, maskandscale=False)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid classic NetCDF response: {error}") from error
    with opened as dataset:
        if as_text(getattr(dataset, "version", "")) != "V1.1":
            raise ValueError("Expected TerraClimate V1.1")
        data = dataset.variables[variable]
        # Publisher's text attribute shadows scipy's dimensions property.
        # Check its known encoding plus the actual array/axis sizes below.
        if data.dimensions not in (("time", "lat", "lon"), b"lon lat time"):
            raise ValueError("Unexpected variable dimensions")
        times = dataset.variables["time"]
        if as_text(times.units) != "days since 1900-01-01 00:00:00" or as_text(
            getattr(times, "calendar", "standard")
        ) not in {"gregorian", "standard"}:
            raise ValueError("Unexpected time encoding")
        dates = [datetime(1900, 1, 1) + timedelta(days=float(x)) for x in times[:]]
        if dates != [datetime(year, month, 1) for month in range(1, 13)]:
            raise ValueError("Expected all 12 requested monthly timestamps")
        west, south, east, north = bounds
        axes = [np.asarray(dataset.variables[name][:], dtype=float) for name in ("lat", "lon")]
        for axis, low, high in zip(axes, (south, west), (north, east)):
            if axis.ndim != 1 or not len(axis) or not np.isfinite(axis).all():
                raise ValueError("Invalid geographic coordinates")
            if len(axis) > 1 and not (np.allclose(np.diff(axis), 1 / 24) or
                                      np.allclose(np.diff(axis), -1 / 24)):
                raise ValueError("Unexpected coordinate spacing")
            if min(axis) < low - 1 / 24 or max(axis) > high + 1 / 24 or (
                abs(min(axis) - low) > 1 / 24 or abs(max(axis) - high) > 1 / 24
            ):
                raise ValueError("Subset does not cover the requested box")
        values = np.asarray(data[:])
        if values.shape != (12, len(axes[0]), len(axes[1])):
            raise ValueError("Unexpected subset shape")
        valid = np.isfinite(values) & (values != getattr(data, "_FillValue", -32768))
        if not valid.reshape(12, -1).any(axis=1).all():
            raise ValueError("Subset contains a month with no valid land cells")
        scale = float(getattr(data, "scale_factor", 1))
        offset = float(getattr(data, "add_offset", 0))
        if not math.isfinite(scale) or scale <= 0 or not math.isfinite(offset):
            raise ValueError("Invalid packing metadata")
        return {"version": "V1.1", "shape": list(values.shape), "units": as_text(data.units),
                "scale_factor": scale, "add_offset": offset,
                "valid_values": int(valid.sum()), "license": as_text(getattr(dataset, "license", ""))}


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def save_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def download(session: requests.Session, path: Path, source: dict, variable: str,
             year: int, bounds: tuple[float, ...], timeout: int, attempts: int) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = path.with_suffix(".nc.json")
    if path.exists():
        recorded = json.loads(receipt.read_text(encoding="utf-8")) if receipt.exists() else {}
        if recorded.get("source") != source or recorded.get("sha256") != digest(path):
            raise ValueError(f"Existing file/receipt mismatch; preserved: {path}")
        validate_netcdf(path, variable, year, bounds)
        return "verified_existing"
    partial = path.with_suffix(".nc.part")
    for attempt in range(attempts):
        try:
            with session.get(source["url"], params=source["params"], stream=True,
                             timeout=(20, timeout)) as response:
                response.raise_for_status()
                with partial.open("wb") as stream:
                    for chunk in response.iter_content(1024 * 1024):
                        stream.write(chunk)
            metadata = validate_netcdf(partial, variable, year, bounds)
            save_json(receipt, {"source": source, "sha256": digest(partial),
                               "bytes": partial.stat().st_size, "metadata": metadata,
                               "verified_utc": datetime.now(timezone.utc).isoformat()})
            partial.replace(path)
            return "downloaded"
        except (requests.RequestException, OSError, ValueError, KeyError) as error:
            if attempt + 1 == attempts:
                raise RuntimeError(f"Failed {path.name}: {error}") from error
            time.sleep(min(2 ** attempt, 10))
    raise RuntimeError("No download attempts")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--project-areas", action="store_true")
    selection.add_argument("--bbox", type=float, nargs=4, action="append",
                           metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    parser.add_argument("--start-year", type=int, default=2015)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--variables", choices=VARIABLES, nargs="+", default=list(VARIABLES))
    parser.add_argument("--output", type=Path, default=Path("data/raw/earth/terraclimate"))
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if not 1950 <= args.start_year <= args.end_year <= datetime.now().year:
        parser.error("Years must be ordered and between 1950 and the current year")
    if args.timeout < 1 or args.attempts < 1:
        parser.error("Timeout and attempts must be positive")
    areas = AREAS if args.project_areas else {
        f"region_{index:02d}": tuple(box) for index, box in enumerate(args.bbox, 1)}
    for bounds in areas.values():
        try:
            request_spec("tmin", args.start_year, bounds)
        except ValueError as error:
            parser.error(str(error))
    with requests.Session() as session:
        response = session.get(CATALOG, timeout=(20, args.timeout))
        response.raise_for_status()
        catalog = catalog_entries(response.text)
        jobs = []
        for name, bounds in areas.items():
            box_id = hashlib.sha256(json.dumps(bounds).encode()).hexdigest()[:12]
            for year in range(args.start_year, args.end_year + 1):
                for variable in dict.fromkeys(args.variables):
                    key = f"TERRACLIMATE_ALL/data/TerraClimate_{variable}_{year}.nc"
                    if key not in catalog:
                        raise ValueError(f"Requested source unavailable in catalog: {key}")
                    source = request_spec(variable, year, bounds)
                    source["catalog_modified"] = catalog[key]
                    jobs.append({"area": name, "bounds": bounds, "year": year,
                                 "variable": variable, "source": source,
                                 "path": f"subsets/{name}/{box_id}/TerraClimate_v1.1_{variable}_{year}.nc"})
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        manifests = args.output / "manifests"
        manifests.mkdir(parents=True, exist_ok=True)
        (manifests / f"{stamp}_catalog.xml").write_text(response.text, encoding="utf-8")
        record = {"catalog_url": CATALOG, "status": "planned", "jobs": jobs,
                  "timeout": args.timeout, "attempts": args.attempts,
                  "dataset": "https://www.climatologylab.org/terraclimate.html"}
        run_path = manifests / f"{stamp}_run.json"
        save_json(run_path, record)
        print(f"{len(jobs)} regional year-variable requests. Generated response sizes are not known in advance.", flush=True)
        print(f"Plan: {run_path}", flush=True)
        if not args.download:
            print("Inventory only. Add --download to fetch NetCDF subsets.")
            return 0
        record["status"] = "running"
        save_json(run_path, record)
        try:
            for index, job in enumerate(jobs, 1):
                print(f"[{index}/{len(jobs)}] {job['path']}", flush=True)
                job["status"] = download(session, args.output / job["path"], job["source"],
                                         job["variable"], job["year"], job["bounds"],
                                         args.timeout, args.attempts)
                save_json(run_path, record)
        except (Exception, KeyboardInterrupt) as error:
            record["status"] = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
            record["error"] = str(error)
            save_json(run_path, record)
            raise
        record["status"] = "complete"
        save_json(run_path, record)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (requests.RequestException, OSError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
