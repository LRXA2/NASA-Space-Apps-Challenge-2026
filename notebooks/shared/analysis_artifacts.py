"""Separate reusable notebook data from disposable presentation exports."""
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from notebooks.shared.inspection import file_hash

PRESENTATION_SUFFIXES = frozenset({'.png', '.pdf', '.svg', '.html', '.md'})


def rebase_links(text: str, source: Path, destination: Path, moved: dict[Path, Path]) -> str:
    """Keep local Markdown and HTML links valid when a report changes directory."""
    def replace(match: re.Match[str]) -> str:
        url = match.group(2)
        parts = urlsplit(url)
        if parts.scheme or parts.netloc or not parts.path or parts.path.startswith('/'):
            return match.group(0)
        target = (source.parent / unquote(parts.path)).resolve()
        target = moved.get(target, target)
        relative = Path(os.path.relpath(target, destination.parent)).as_posix()
        updated = urlunsplit(('', '', quote(relative, safe='/'), parts.query, parts.fragment))
        return match.group(1) + updated + match.group(3)

    text = re.sub(r'(\]\()([^\s)]+)(\))', replace, text)
    return re.sub(r'((?:href|src)=[\"\'])([^\"\']+)([\"\'])', replace, text)


def _reject_links(path: Path, root: Path) -> None:
    for item in (path, *path.parents):
        if item.exists() and (item.is_symlink() or
                             getattr(item.lstat(), 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError(f'Linked paths are not supported: {item}')
        if item == root:
            break


def publish_analysis(root: Path, data_dir: Path, *, manifest_name: str = 'provenance.json') -> Path:
    """Publish exports last; only reusable data is required by the completed manifest.

    Call after the notebook's last display and its completion marker. A failed publication leaves status
    ``publishing`` rather than claiming a completed data run. Existing export
    directories are rejected before any changes, so previous results survive.
    """
    root = root.absolute()
    data_dir = data_dir.absolute()
    parent = root / 'data/processed/analysis'
    if data_dir.parent != parent or data_dir.name in ('', '.', '..'):
        raise ValueError('Expected one run directly under data/processed/analysis')
    if Path(manifest_name).name != manifest_name:
        raise ValueError('Manifest must be a filename within the run')
    report_dir = root / 'reports/analysis' / data_dir.name
    _reject_links(data_dir, root)
    _reject_links(report_dir, root)
    if report_dir.exists():
        raise FileExistsError(report_dir)
    files = sorted(p for p in data_dir.rglob('*') if p.is_file())
    for path in data_dir.rglob('*'):
        _reject_links(path, root)
    moved = {p.resolve(): report_dir / p.relative_to(data_dir)
             for p in files if p.suffix.lower() in PRESENTATION_SUFFIXES}
    manifest_path = data_dir / manifest_name
    record: dict[str, Any] = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    if record.get('status') not in {'publishing', 'complete'}:
        raise ValueError('Analysis must finish before publishing its outputs')
    key = 'outputs_sha256' if 'outputs_sha256' in record else 'outputs'
    list_schema = isinstance(record.get(key), list)
    record['status'] = 'publishing'
    manifest_path.write_text(json.dumps(record, indent=2), encoding='utf-8')
    report_dir.mkdir(parents=True, exist_ok=False)
    for source, destination in moved.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix.lower() in {'.md', '.html'}:
            content = rebase_links(source.read_text(encoding='utf-8'), source, destination, moved)
            destination.write_text(content, encoding='utf-8')
            source.unlink()
        else:
            source.rename(destination)
    data_files = sorted(p for p in data_dir.rglob('*') if p.is_file() and p != manifest_path)
    record[key] = ([{'path': p.relative_to(data_dir).as_posix(), 'bytes': p.stat().st_size, 'sha256': file_hash(p)}
                    for p in data_files] if list_schema else
                   {p.relative_to(data_dir).as_posix(): file_hash(p) for p in data_files})
    record['status'] = 'complete'
    record['optional_reports'] = report_dir.relative_to(root).as_posix()
    completed_manifest = json.dumps(record, indent=2).encode('utf-8')
    exports = {p.relative_to(report_dir).as_posix(): file_hash(p)
               for p in sorted(report_dir.rglob('*')) if p.is_file()}
    (report_dir / 'provenance.json').write_text(json.dumps({
        'data_manifest': manifest_path.relative_to(root).as_posix(),
        'data_manifest_sha256': hashlib.sha256(completed_manifest).hexdigest(), 'outputs': exports,
    }, indent=2), encoding='utf-8')
    manifest_path.write_bytes(completed_manifest)
    return report_dir
