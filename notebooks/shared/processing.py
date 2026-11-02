"""Shared, tested processing operations; importing this module writes nothing."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import platform
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from affine import Affine
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.merge import merge
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import reproject, transform_bounds, transform_geom
from rasterio.windows import Window, from_bounds
from rasterio.windows import bounds as window_bounds
from rasterio.windows import transform as window_transform
from scipy.ndimage import minimum_filter, uniform_filter
from shapely.geometry import box
from shapely.ops import unary_union

AREAS = {
    "northern_arizona": {"bbox": (-112.5, 35, -111, 36), "crs": "EPSG:32612"},
    "lanzarote": {"bbox": (-13.95, 28.8, -13.35, 29.3), "crs": "EPSG:32628"},
    "atacama_san_pedro": {"bbox": (-68.6, -23.2, -67.8, -22.6), "crs": "EPSG:32719"},
}
# Match the SDEM's polar standard-parallel convention, not the k=1 variant.
MOON_CRS = "+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +R=1737400 +units=m +no_defs"
MOON_GEOGRAPHIC = "+proj=longlat +R=1737400 +no_defs"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_output(root: Path, path: Path) -> Path:
    target = path.resolve()
    base = (root / "data/processed").resolve()
    if not base.is_relative_to(root.resolve()) or not target.is_relative_to(base):
        raise ValueError("Output must remain within project data/processed")
    if target.is_relative_to((root / "data/raw").resolve()):
        raise ValueError("Raw data is read-only")
    return target


class Run:
    """Own an isolated output run and its completion/failure provenance."""

    def __init__(self, root: Path, stage: str, config: dict, notebook: str):
        self.root = root
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        self.directory = safe_output(root, root / "data/processed" / stage / (stamp + "_" + uuid.uuid4().hex[:6]))
        self.record = {"stage": stage, "config": config, "status": "running", "inputs": {},
                       "started_utc": stamp, "python": platform.python_version(),
                       "packages": {name: importlib.metadata.version(name) for name in
                                    ("numpy", "pandas", "scipy", "rasterio", "pyproj", "shapely", "osmium")}}
        self.notebook = root / "notebooks" / notebook

    def __enter__(self):
        self.directory.mkdir(parents=True, exist_ok=False)
        self.input(self.notebook)
        self.input(Path(__file__))
        self.save()
        return self

    def path(self, relative: str) -> Path:
        result = safe_output(self.root, self.directory / relative)
        if not result.is_relative_to(self.directory):
            raise ValueError("Output escapes current run")
        result.parent.mkdir(parents=True, exist_ok=True)
        return result

    def input(self, path: Path) -> None:
        path = path.resolve()
        key = str(path.relative_to(self.root.resolve()))
        if key not in self.record["inputs"]:
            stat = path.stat()
            self.record["inputs"][key] = {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns,
                                          "sha256": sha256(path)}

    def save(self) -> None:
        temporary = self.directory / "provenance.json.tmp"
        temporary.write_text(json.dumps(self.record, indent=2, default=str), encoding="utf-8")
        temporary.replace(self.directory / "provenance.json")

    def __exit__(self, exc_type, exc, traceback):
        self.record["status"] = "complete" if exc_type is None else "failed"
        if exc is not None:
            self.record["error"] = repr(exc)
        self.record["outputs"] = [
            {"path": str(p.relative_to(self.directory)), "bytes": p.stat().st_size, "sha256": sha256(p)}
            for p in sorted(self.directory.rglob("*")) if p.is_file() and p.name != "provenance.json"
        ]
        self.record["finished_utc"] = datetime.now(UTC).isoformat()
        self.save()
        return False


@dataclass(frozen=True)
class Grid:
    crs: CRS | str
    transform: Affine
    width: int
    height: int

    def __post_init__(self):
        if self.width < 1 or self.height < 1 or self.width * self.height > 150_000_000:
            raise ValueError("Invalid grid or more than 150 million cells")


def make_grid(bounds, crs, resolution: float) -> Grid:
    if not math.isfinite(resolution) or resolution <= 0:
        raise ValueError("Resolution must be positive")
    west, south, east, north = bounds
    west, south = math.floor(west / resolution) * resolution, math.floor(south / resolution) * resolution
    east, north = math.ceil(east / resolution) * resolution, math.ceil(north / resolution) * resolution
    grid = Grid(crs, from_origin(west, north, resolution, resolution),
                round((east - west) / resolution), round((north - south) / resolution))
    if grid.width * grid.height > 30_000_000:
        raise ValueError("Analysis grid exceeds 30 million cells; reduce AOI or increase spacing")
    return grid


def pad_grid(grid: Grid, cells: int) -> Grid:
    """Expand on the existing lattice so trimming preserves the original grid exactly."""
    if not isinstance(cells, int) or cells < 0:
        raise ValueError("Padding must be a nonnegative integer")
    return Grid(grid.crs, grid.transform * Affine.translation(-cells, -cells),
                grid.width + 2 * cells, grid.height + 2 * cells)


def rectangular_coverage(grid: Grid, bounds: tuple[float, float, float, float]) -> np.ndarray:
    """Fraction of each pixel inside same-CRS rectangular source bounds; no extrapolation."""
    west, south, east, north = bounds
    transform = grid.transform
    if (not all(math.isfinite(v) for v in bounds) or west >= east or south >= north
            or transform.a <= 0 or transform.e >= 0 or transform.b != 0 or transform.d != 0):
        raise ValueError('Expected ordered finite bounds and a north-up unrotated grid')
    left = transform.c + np.arange(grid.width) * transform.a
    top = transform.f + np.arange(grid.height) * transform.e
    x_fraction = np.clip(np.minimum(left + transform.a, east) - np.maximum(left, west),
                         0, transform.a) / transform.a
    y_fraction = np.clip(np.minimum(top, north) - np.maximum(top + transform.e, south),
                         0, -transform.e) / -transform.e
    return (y_fraction[:, None] * x_fraction[None, :]).astype('float32')


def select_covering_tiles(bounds_by_name: dict, bounds) -> list[str]:
    """Select intersecting actual footprints and reject incomplete rectangular coverage."""
    target = box(*bounds)
    selected = sorted(name for name, footprint in bounds_by_name.items()
                      if box(*footprint).intersection(target).area > 0)
    if not selected or not unary_union([box(*bounds_by_name[name]) for name in selected]).buffer(1e-10).covers(target):
        raise ValueError(f"Available source tile footprints do not cover processing bounds {bounds}")
    return selected


def bbox_polygon(bounds) -> dict:
    west, south, east, north = bounds
    # Densify before projection so UTM edges follow the geographic rectangle.
    xs, ys = np.linspace(west, east, 41), np.linspace(south, north, 41)
    points = [(x, south) for x in xs] + [(east, y) for y in ys]
    points += [(x, north) for x in xs[::-1]] + [(west, y) for y in ys[::-1]]
    return {"type": "Polygon", "coordinates": [points + [points[0]]]}


def roi_mask(grid: Grid, bounds, source_crs="EPSG:4326") -> np.ndarray:
    geom = transform_geom(source_crs, grid.crs, bbox_polygon(bounds))
    return geometry_mask([geom], (grid.height, grid.width), grid.transform, invert=True)


def warp(path: Path, grid: Grid, resampling=Resampling.bilinear) -> np.ndarray:
    with rasterio.open(path) as source:
        if source.crs is None or source.count != 1:
            raise ValueError(f"Expected georeferenced single-band raster: {path}")
        with WarpedVRT(source, crs=grid.crs, transform=grid.transform, width=grid.width,
                       height=grid.height, dtype="float32", nodata=np.nan,
                       resampling=resampling) as vrt:
            raw = vrt.read(1, masked=True).filled(np.nan).astype("float32")
        return raw * source.scales[0] + source.offsets[0]


def mosaic_elevation(paths: list[Path], output: Path) -> None:
    """Merge native neighbors before interpolation so kernels span tile seams."""
    if not paths:
        raise ValueError("No elevation tiles")
    reference = None
    for path in paths:
        with rasterio.open(path) as src:
            properties = (src.crs, src.res, src.count)
            if src.scales != (1.0,) or src.offsets != (0.0,) or src.count != 1:
                raise ValueError("Elevation mosaic requires unpacked single-band tiles")
            if reference is not None and properties != reference:
                raise ValueError("Mosaic input grid/CRS mismatch")
            reference = properties
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp.tif")
    merge(paths, nodata=np.nan, dtype="float32", dst_path=temporary, mem_limit=128,
          dst_kwds={"compress": "deflate", "tiled": True, "blockxsize": 256,
                    "blockysize": 256, "BIGTIFF": "IF_SAFER"})
    temporary.replace(output)


def write_raster(path: Path, values: np.ndarray, grid: Grid, units: str, **tags) -> None:
    if values.shape != (grid.height, grid.width):
        raise ValueError("Array/grid shape mismatch")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.tif")
    with rasterio.open(temporary, "w", driver="GTiff", height=grid.height, width=grid.width,
                       count=1, dtype="float32", crs=grid.crs, transform=grid.transform,
                       nodata=np.nan, compress="deflate", tiled=True, BIGTIFF="IF_SAFER") as dst:
        dst.write(values.astype("float32"), 1)
        dst.set_band_unit(1, units)
        dst.update_tags(**{k: str(v) for k, v in tags.items()})
    temporary.replace(path)


def terrain(elevation: np.ndarray, spacing: float, window: int = 11, *,
            output_mask: np.ndarray | None = None) -> dict[str, np.ndarray]:
    """Physical derivatives on an unrotated square metric grid, without filling gaps."""
    if spacing <= 0 or window < 3 or window % 2 != 1:
        raise ValueError("Positive spacing and odd window >=3 required")
    z = np.asarray(elevation, dtype="float64")
    valid = np.isfinite(z)
    if not valid.any():
        raise ValueError("No valid elevation")
    safe = np.where(valid, z, 0)
    support = minimum_filter(valid.astype("uint8"), size=3, mode="constant", cval=0).astype(bool)
    dy, dx = np.gradient(safe, spacing)
    slope = np.degrees(np.arctan(np.hypot(dx, dy)))
    curvature = (np.roll(safe, 1, 0) + np.roll(safe, -1, 0) + np.roll(safe, 1, 1)
                 + np.roll(safe, -1, 1) - 4 * safe) / spacing ** 2
    full = minimum_filter(valid.astype("uint8"), size=window, mode="constant", cval=0).astype(bool)
    mean = uniform_filter(safe, size=window, mode="constant")
    variance = uniform_filter(safe * safe, size=window, mode="constant") - mean * mean
    roughness = np.sqrt(np.maximum(variance, 0))
    slope[~support] = np.nan
    curvature[~support] = np.nan
    roughness[~full] = np.nan
    reference = valid
    if output_mask is not None:
        if output_mask.shape != z.shape or output_mask.dtype != np.dtype(bool):
            raise ValueError("Output mask must be boolean and match the elevation shape")
        reference = valid & output_mask
        if not reference.any():
            raise ValueError("No valid elevation within the output mask")
    result = {"relative_elevation_m": z - np.median(z[reference]), "slope_deg": slope,
              "laplacian_per_m": curvature, "local_elevation_std_m": roughness}
    if output_mask is not None:
        for values in result.values():
            values[~output_mask] = np.nan
    return result


def mosaic_landcover(paths: list[Path], output: Path, bounds) -> None:
    """Crop adjacent native class tiles before aggregating across source seams."""
    if not paths or len(set(paths)) != len(paths):
        raise ValueError('Expected distinct land-cover tiles')
    reference = None
    origin = None
    footprints = {}
    for path in paths:
        with rasterio.open(path) as src:
            transform = src.transform
            properties = (src.crs, src.res)
            if (src.crs is None or src.count != 1 or src.dtypes != ('uint8',)
                    or src.nodata != 0 or src.scales != (1.,) or src.offsets != (0.,)
                    or transform.b != 0 or transform.d != 0 or transform.a <= 0 or transform.e >= 0):
                raise ValueError('Expected north-up unscaled uint8 class tiles with nodata=0')
            if reference is None:
                reference = properties
                origin = transform
            elif properties != reference:
                raise ValueError('Land-cover mosaic grid/CRS mismatch')
            assert origin is not None
            offsets = ((transform.c - origin.c) / transform.a,
                       (transform.f - origin.f) / transform.e)
            if any(abs(value - round(value)) > 1e-6 for value in offsets):
                raise ValueError('Land-cover tiles must be aligned on one native lattice')
            footprints[str(path)] = tuple(src.bounds)
    assert reference is not None and origin is not None
    selected = select_covering_tiles(footprints, bounds)
    window = from_bounds(left=bounds[0], bottom=bounds[1], right=bounds[2], top=bounds[3], transform=origin)
    left, top = math.floor(window.col_off), math.floor(window.row_off)
    right = math.ceil(window.col_off + window.width)
    bottom = math.ceil(window.row_off + window.height)
    crop = Window.from_slices((top, bottom), (left, right), boundless=True)
    aligned_bounds = window_bounds(crop, origin)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.tmp.tif')
    merge([Path(name) for name in selected], bounds=aligned_bounds, nodata=0, dtype='uint8',
          resampling=Resampling.nearest, dst_path=temporary, mem_limit=128,
          dst_kwds={'compress': 'deflate', 'tiled': True, 'blockxsize': 256, 'blockysize': 256,
                    'BIGTIFF': 'IF_SAFER'})
    temporary.replace(output)


def landcover_fractions(path: Path, grid: Grid) -> dict[str, np.ndarray]:
    """Area-weighted binary classes in bounded windows; never average class codes."""
    codes = {"built_fraction": 50, "crop_fraction": 40, "water_fraction": 80, "bare_sparse_fraction": 60}
    result = {name: np.full((grid.height, grid.width), np.nan, dtype="float32")
              for name in (*codes, "source_coverage")}
    with rasterio.open(path) as src:
        for row in range(0, grid.height, 256):
            for col in range(0, grid.width, 256):
                win = Window.from_slices((row, min(row + 256, grid.height)), (col, min(col + 256, grid.width)))
                dst_transform = window_transform(win, grid.transform)
                bounds = window_bounds(win, grid.transform)
                geographic = transform_bounds(grid.crs, src.crs, *bounds, densify_pts=21)
                raw_window = from_bounds(left=geographic[0], bottom=geographic[1], right=geographic[2], top=geographic[3], transform=src.transform)
                left, top = math.floor(raw_window.col_off) - 2, math.floor(raw_window.row_off) - 2
                right = math.ceil(raw_window.col_off + raw_window.width) + 2
                bottom = math.ceil(raw_window.row_off + raw_window.height) + 2
                source_window = Window.from_slices((top, bottom), (left, right), boundless=True)
                raw = src.read(1, window=source_window, boundless=True, masked=True)
                known = ~np.ma.getmaskarray(raw) & np.isin(raw.data, [10,20,30,40,50,60,70,80,90,95,100])
                for name, output_values in result.items():
                    data = known.astype("float32") if name == "source_coverage" else np.where(
                        known, (raw.data == codes[name]).astype("float32"), np.nan)
                    destination = np.full((int(win.height), int(win.width)), np.nan, dtype="float32")
                    reproject(data, destination, src_transform=src.window_transform(source_window),
                              src_crs=src.crs, src_nodata=np.nan, dst_transform=dst_transform,
                              dst_crs=grid.crs, dst_nodata=np.nan, resampling=Resampling.average)
                    output_values[row:row + int(win.height), col:col + int(win.width)] = destination
    return result


def crop_native(source_path: Path, target: Path, bounds, bounds_crs, *,
                fallback_crs: CRS | str | None = None, crs_evidence: str | None = None) -> dict:
    """Crop on the original pixel grid and decode scales only after masking."""
    with rasterio.open(source_path) as src:
        inferred = src.crs is None
        if inferred and (fallback_crs is None or not crs_evidence):
            raise ValueError(f"Missing CRS for {source_path}; a documented fallback is required")
        effective_crs = src.crs if src.crs is not None else CRS.from_user_input(fallback_crs)
        evidence = crs_evidence if inferred else "embedded source CRS"
        projected = (bounds if CRS.from_user_input(bounds_crs) == effective_crs else
                     transform_bounds(bounds_crs, effective_crs, *bounds, densify_pts=21))
        window = from_bounds(left=projected[0], bottom=projected[1], right=projected[2], top=projected[3], transform=src.transform)
        col, row = math.floor(window.col_off), math.floor(window.row_off)
        right, bottom = math.ceil(window.col_off + window.width), math.ceil(window.row_off + window.height)
        window = Window.from_slices((row, bottom), (col, right), boundless=True).intersection(
            Window.from_slices((0, src.height), (0, src.width)))
        raw = src.read(1, window=window, masked=True).astype("float32").filled(np.nan)
        decoded = raw * src.scales[0] + src.offsets[0]
        grid = Grid(effective_crs, src.window_transform(window), int(window.width), int(window.height))
        write_raster(target, decoded, grid, src.units[0] or "source_units_unconfirmed",
                     source=source_path.name, source_scale=src.scales[0], source_offset=src.offsets[0],
                     crs_inferred=inferred, crs_evidence=evidence)
        return {"source": str(source_path), "resolution": src.res, "scale": src.scales[0],
                "offset": src.offsets[0], "source_units": src.units[0], "valid_fraction": float(np.isfinite(decoded).mean()),
                "crs": effective_crs.to_wkt(), "crs_inferred": inferred,
                "crs_evidence": evidence, "tags": src.tags()}


def decode_packed(raw, fill_values, scale: float, offset: float) -> np.ndarray:
    data = np.asarray(raw, dtype="float64").copy()
    valid = np.isfinite(data)
    for fill in fill_values:
        valid &= data != fill
    data = data * scale + offset
    data[~valid] = np.nan
    return data


def diviner_chunks(label_path: Path, chunk_rows: int = 100_000):
    ns = {"p": "http://pds.nasa.gov/pds4/pds/v1"}
    root = ET.parse(label_path).getroot()
    table = root.find(".//p:Table_Character", ns)
    if table is None:
        raise ValueError("Missing PDS table definition")
    filename = root.findtext(".//p:File/p:file_name", namespaces=ns)
    if not filename or Path(filename).name != filename:
        raise ValueError("Invalid PDS table filename")
    path = label_path.parent / filename
    offset = int(table.findtext("p:offset", namespaces=ns) or "0")
    count = int(table.findtext("p:records", namespaces=ns) or "0")
    length = int(table.findtext(".//p:record_length", namespaces=ns) or "0")
    if path.stat().st_size != offset + count * length:
        raise ValueError("PDS table size disagrees with XML")
    fields = []
    for field in table.findall(".//p:Field_Character", ns):
        name = field.findtext("p:name", namespaces=ns)
        start = int(field.findtext("p:field_location", namespaces=ns) or "0") - 1
        width = int(field.findtext("p:field_length", namespaces=ns) or "0")
        missing = [float(x.text) for x in field.findall("p:Special_Constants/*", ns) if x.text]
        fields.append((name, start, width, missing))
    if not {"clon", "clat", "tbol", "ltim"}.issubset({f[0] for f in fields}):
        raise ValueError("Missing required Diviner fields")
    with path.open("rb") as stream:
        stream.seek(offset)
        for start_row in range(0, count, chunk_rows):
            rows = min(chunk_rows, count - start_row)
            block = stream.read(rows * length)
            if len(block) != rows * length:
                raise ValueError("Truncated PDS table")
            columns = {}
            for name, start, width, missing in fields:
                view = np.ndarray((rows,), dtype=f"S{width}", buffer=block, offset=start, strides=(length,))
                columns[name] = decode_packed(view.astype(float), missing, 1, 0)
            yield pd.DataFrame(columns)
