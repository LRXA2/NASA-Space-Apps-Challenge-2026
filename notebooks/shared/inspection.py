"""Small, read-only inspection operations shared by the decision notebooks."""
import hashlib
import html
import json
from pathlib import Path

import numpy as np


def complete_blocks(mask: np.ndarray, side: int) -> np.ndarray:
    """Return eligible nonoverlapping squares, anchored at upper-left; omit edge remainders."""
    if mask.ndim != 2 or mask.dtype != np.bool_:
        raise ValueError('mask must be a two-dimensional boolean array')
    if isinstance(side, bool) or not isinstance(side, int) or side < 1:
        raise ValueError('side must be a positive integer')
    rows, cols = mask.shape[0] // side, mask.shape[1] // side
    return np.asarray(mask[:rows * side, :cols * side].reshape(rows, side, cols, side).all(axis=(1, 3)))


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_run(run: Path) -> dict[str, str]:
    """Return expected hashes; callers verify only the outputs they actually consume."""
    record = json.loads((run / 'provenance.json').read_text())
    if record['status'] != 'complete':
        raise ValueError(f'Incomplete run: {run}')
    # Runs recorded on Windows store backslash paths; normalize so they verify on any OS.
    return {str((run / item['path'].replace('\\', '/')).resolve()): item['sha256']
            for item in record['outputs']}


def check_input(path: Path, expected: dict[str, str], evidence: dict[str, str]) -> Path:
    key = str(path.resolve())
    digest = file_hash(path)
    if key not in expected or digest != expected[key]:
        raise ValueError(f'Unregistered or changed run output: {path}')
    evidence[key] = digest
    return path


def bar_svg(labels: list[str], values: list[float], title: str, unit: str) -> str:
    """A labelled zero-based horizontal chart; values must be finite and nonnegative."""
    if len(labels) != len(values) or not all(np.isfinite(v) and v >= 0 for v in values):
        raise ValueError('Bar labels/values must align and values must be finite and nonnegative')
    maximum = max(values, default=0) or 1
    parts = [(f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{90 + 30 * len(labels)}" '
             f'role="img"><rect width="100%" height="100%" fill="white"/>'
             f'<text x="12" y="25" font-size="18">{html.escape(title)}</text>'
             f'<text x="12" y="48" font-size="12">{html.escape(unit)}; bars start at zero</text>')]
    for i, (label, value) in enumerate(zip(labels, values, strict=True)):
        y = 70 + 30 * i
        parts.append(f'<text x="12" y="{y+15}" font-size="12">{html.escape(label)}</text>'
                     f'<rect x="420" y="{y}" width="{450 * value / maximum}" height="20" fill="#24758a"/>'
                     f'<text x="{430 + 450 * value / maximum}" y="{y+15}" font-size="12">{value:.3g}</text>')
    return ''.join(parts) + '</svg>'
