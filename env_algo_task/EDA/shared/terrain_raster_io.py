"""Bounded raster I/O for notebook 05, preserving its native support policy."""
import math
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import Window, from_bounds

from notebooks.shared.processing import Grid, warp


def raster_windows(width, height, tile_size=512):
    if not isinstance(tile_size, int) or tile_size < 1:
        raise ValueError("Tile size must be a positive integer")
    for row in range(0, height, tile_size):
        for col in range(0, width, tile_size):
            yield Window(col, row, min(tile_size, width-col), min(tile_size, height-row))


def image_supported_grid(elevation_path, mask_path, grid, workdir, *, tile_size=512):
    """Native nearest-count support, then average to the unchanged analysis grid.

    Keep native elevation/support on temporary disk instead of retaining multiple
    full 5 m arrays in RAM. Zero support remains a valid fraction observation;
    unsupported elevations remain NaN. No missing-data filling is performed.
    """
    workdir = Path(workdir).resolve()
    if not workdir.is_dir():
        raise FileNotFoundError(workdir)
    with rasterio.Env(GDAL_CACHEMAX=32*1024**2), TemporaryDirectory(
            prefix="terrain_work_", dir=workdir) as temporary:
        intermediate = Path(temporary) / "native_support.tif"
        with rasterio.open(elevation_path) as src:
            if src.crs is None or src.count != 1:
                raise ValueError("Expected georeferenced single-band elevation")
            with rasterio.open(intermediate, "w", driver="GTiff", width=src.width,
                               height=src.height, count=2, dtype="float32", crs=src.crs,
                               transform=src.transform, nodata=np.nan, tiled=True,
                               compress="deflate", BIGTIFF="IF_SAFER") as dst:
                for window in raster_windows(src.width, src.height, tile_size):
                    heights = src.read(1, window=window, masked=True).astype("float32").filled(np.nan)
                    heights = heights * src.scales[0] + src.offsets[0]
                    tile_grid = Grid(src.crs, src.window_transform(window),
                                     int(window.width), int(window.height))
                    counts = warp(mask_path, tile_grid, resampling=Resampling.nearest)
                    supported = np.isfinite(heights) & np.isfinite(counts) & (counts > 0)
                    heights[~supported] = np.nan
                    dst.write(heights, 1, window=window)
                    dst.write(supported.astype("float32"), 2, window=window)
        elevation = np.full((grid.height, grid.width), np.nan, dtype="float32")
        fraction = np.full_like(elevation, np.nan)
        with rasterio.open(intermediate) as src:
            for band, destination in ((1, elevation), (2, fraction)):
                reproject(rasterio.band(src, band), destination, src_transform=src.transform,
                          src_crs=src.crs, src_nodata=np.nan, dst_transform=grid.transform,
                          dst_crs=grid.crs, dst_nodata=np.nan, resampling=Resampling.average,
                          warp_mem_limit=32)
        return elevation, fraction


def crop_native_windowed(source_path, target, bounds, bounds_crs, *,
                         fallback_crs=None, crs_evidence=None, tile_size=512):
    """Same native crop/scale/metadata as crop_native, with bounded tile reads."""
    target = Path(target)
    with rasterio.Env(GDAL_CACHEMAX=32*1024**2), rasterio.open(source_path) as src:
        inferred = src.crs is None
        if inferred and (fallback_crs is None or not crs_evidence):
            raise ValueError(f"Missing CRS for {source_path}; a documented fallback is required")
        effective_crs = src.crs if src.crs is not None else CRS.from_user_input(fallback_crs)
        evidence = crs_evidence if inferred else "embedded source CRS"
        projected = (bounds if CRS.from_user_input(bounds_crs) == effective_crs else
                     transform_bounds(bounds_crs, effective_crs, *bounds, densify_pts=21))
        window = from_bounds(*projected, transform=src.transform)
        col, row = math.floor(window.col_off), math.floor(window.row_off)
        right = math.ceil(window.col_off + window.width)
        bottom = math.ceil(window.row_off + window.height)
        window = Window(col, row, right-col, bottom-row).intersection(
            Window(0, 0, src.width, src.height))
        grid = Grid(effective_crs, src.window_transform(window), int(window.width), int(window.height))
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp.tif")
        valid = 0
        with rasterio.open(temporary, "w", driver="GTiff", width=grid.width, height=grid.height,
                           count=1, dtype="float32", crs=grid.crs, transform=grid.transform,
                           nodata=np.nan, compress="deflate", tiled=True, BIGTIFF="IF_SAFER") as dst:
            for tile in raster_windows(grid.width, grid.height, tile_size):
                source_window = Window(window.col_off+tile.col_off, window.row_off+tile.row_off,
                                       tile.width, tile.height)
                raw = src.read(1, window=source_window, masked=True).astype("float32").filled(np.nan)
                decoded = raw * src.scales[0] + src.offsets[0]
                valid += int(np.isfinite(decoded).sum())
                dst.write(decoded.astype("float32"), 1, window=tile)
            dst.set_band_unit(1, src.units[0] or "source_units_unconfirmed")
            dst.update_tags(source=source_path.name, source_scale=str(src.scales[0]),
                            source_offset=str(src.offsets[0]), crs_inferred=str(inferred),
                            crs_evidence=evidence)
        temporary.replace(target)
        return {"source": str(source_path), "resolution": src.res, "scale": src.scales[0],
                "offset": src.offsets[0], "source_units": src.units[0],
                "valid_fraction": valid/(grid.width*grid.height),
                "crs": effective_crs.to_wkt(), "crs_inferred": inferred,
                "crs_evidence": evidence, "tags": src.tags()}
