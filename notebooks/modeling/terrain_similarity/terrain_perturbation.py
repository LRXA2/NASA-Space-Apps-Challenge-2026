"""Controlled physical transformations for terrain-embedding diagnostics."""
import numpy as np


def rescale_terrain(physical: np.ndarray, factor: float) -> np.ndarray:
    """Scale vertical relief on NCHW elevation/slope/local-SD tensors.

    Horizontal spacing stays fixed. Height and local SD scale linearly;
    slope angles follow atan(factor * tan(original angle)). No fitted
    normalization is performed here, and input arrays are never modified.
    """
    if type(factor) not in {int, float} or not np.isfinite(factor) or factor <= 0:
        raise ValueError('Vertical scale factor must be finite and positive')
    if (physical.ndim != 4 or physical.shape[1] != 3 or not physical.size
            or physical.shape[2] != physical.shape[3]):
        raise ValueError('Expected nonempty NCHW square patches with three physical channels')
    if (not np.isfinite(physical).all() or (physical[:, 1] < 0).any()
            or (physical[:, 1] >= 90).any() or (physical[:, 2] < 0).any()):
        raise ValueError('Expected finite terrain, slopes in [0, 90), and nonnegative local SD')
    result = physical.astype(np.float64, copy=True)
    if factor != 1:
        result[:, 0] *= factor
        result[:, 1] = np.degrees(np.arctan(factor * np.tan(np.radians(result[:, 1]))))
        result[:, 2] *= factor
    if not np.isfinite(result).all() or np.abs(result).max() > np.finfo(np.float32).max:
        raise ValueError('Scaled terrain exceeds finite float32 range')
    return result.astype(np.float32)
