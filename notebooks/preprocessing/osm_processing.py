"""Streaming OSM geometry selection for explicitly bounded support zones."""
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import osmium
from osmium.geom import WKBFactory
from shapely.geometry import Point, box, mapping
from shapely import wkb
from shapely.errors import GEOSException


class SupportFeatures(osmium.SimpleHandler):
    def __init__(self, bounds):
        super().__init__()
        self.zone = box(*bounds)
        self.factory = WKBFactory()
        self.features = {}
        self.counts = Counter()
        self.source = ""

    def keep(self, obj, kind, identifier, geometry, category):
        if geometry.is_empty or not geometry.is_valid:
            self.counts["invalid_geometry"] += 1
            return
        if not geometry.intersects(self.zone):
            return
        clipped = geometry.intersection(self.zone)
        key = f"{kind}/{identifier}"
        previous = self.features.get(key)
        if previous:
            self.counts["duplicates"] += 1
            if previous["properties"]["version"] >= obj.version:
                return
        self.features[key] = {"type": "Feature", "id": key, "geometry": mapping(clipped),
                              "properties": {"osm_type": kind, "osm_id": str(identifier),
                                             "version": obj.version, "category": category,
                                             "source": self.source, "tags": dict(obj.tags)}}

    def node(self, node):
        if not any(k in node.tags for k in ("place", "amenity", "aeroway", "public_transport")):
            return
        if not node.location.valid():
            self.counts["missing_node_location"] += 1
            return
        self.keep(node, "node", node.id, Point(node.location.lon, node.location.lat), "point")

    def way(self, way):
        if not any(k in way.tags for k in ("highway", "railway")):
            return
        try:
            geometry = wkb.loads(self.factory.create_linestring(way), hex=True)
            self.keep(way, "way", way.id, geometry, "transport")
        except (RuntimeError, GEOSException):
            self.counts["incomplete_or_invalid_way"] += 1

    def area(self, area):
        if not any(k in area.tags for k in ("building", "amenity", "aeroway", "place")):
            return
        try:
            geometry = wkb.loads(self.factory.create_multipolygon(area), hex=True)
            kind = "way" if area.from_way() else "relation"
            self.keep(area, kind, area.orig_id(), geometry, "area")
        except (RuntimeError, GEOSException):
            self.counts["incomplete_or_invalid_area"] += 1


class ObservedVersions(osmium.SimpleHandler):
    """Observe selected IDs even when newer geometry/tags no longer qualify."""

    def __init__(self, selected_ids):
        super().__init__()
        self.selected_ids = set(selected_ids)
        self.versions = {}

    def observe(self, kind, obj):
        key = f"{kind}/{obj.id}"
        if key in self.selected_ids:
            self.versions[key] = max(obj.version, self.versions.get(key, -1))

    def node(self, node):
        self.observe("node", node)

    def way(self, way):
        self.observe("way", way)

    def relation(self, relation):
        self.observe("relation", relation)


def extract_support(paths: list[Path], bounds, output: Path) -> dict:
    """Deduplicate by original object type/ID, preferring the highest version."""
    selected = {}
    counts = Counter()
    output.parent.mkdir(parents=True, exist_ok=True)
    for source in paths:
        # A worker process releases libosmium's mapped index handles on Windows.
        # It reads one source and returns clipped features; it never writes raw data.
        with tempfile.TemporaryDirectory(prefix="osm_locations_") as temporary:
            cache = Path(temporary) / "locations.idx"
            payload = Path(temporary) / "features.json"
            subprocess.run([sys.executable, str(Path(__file__).resolve()), str(source.resolve()),
                            str(cache), str(payload), *(str(x) for x in bounds)], check=True)
            batch = json.loads(payload.read_text(encoding="utf-8"))
            counts.update(batch["diagnostics"])
            for key, feature in batch["features"].items():
                if key in selected:
                    counts["duplicates"] += 1
                    if selected[key]["properties"]["version"] >= feature["properties"]["version"]:
                        continue
                selected[key] = feature
    # An additional metadata-only pass prevents an older in-zone feature from
    # surviving when a newer version moved outside or lost its selected tags.
    if len(paths) > 1 and selected:
        with tempfile.TemporaryDirectory(prefix="osm_versions_") as temporary:
            ids_path = Path(temporary) / "ids.json"
            ids_path.write_text(json.dumps(list(selected)), encoding="utf-8")
            superseded = set()
            for source in paths:
                payload = Path(temporary) / "versions.json"
                subprocess.run([sys.executable, str(Path(__file__).resolve()), "--versions",
                                str(source.resolve()), str(ids_path), str(payload)], check=True)
                for key, version in json.loads(payload.read_text(encoding="utf-8")).items():
                    if version > selected[key]["properties"]["version"]:
                        superseded.add(key)
            for key in superseded:
                del selected[key]
            counts["superseded_selected_features"] = len(superseded)
    features = [selected[key] for key in sorted(selected)]
    temporary_output = output.with_suffix(".tmp")
    temporary_output.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                                           ensure_ascii=False), encoding="utf-8")
    temporary_output.replace(output)
    return {"feature_count": len(features), "categories": dict(Counter(f["properties"]["category"] for f in features)),
            "diagnostics": dict(counts), "bbox_lon_lat": bounds,
            "deduplication": "original OSM type + ID; highest version; first source on ties",
            "limitations": "Unassembled relations and incomplete geometries may be absent; no legal-access inference"}


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--versions":
        observer = ObservedVersions(json.loads(Path(sys.argv[3]).read_text(encoding="utf-8")))
        observer.apply_file(sys.argv[2])
        Path(sys.argv[4]).write_text(json.dumps(observer.versions), encoding="utf-8")
        raise SystemExit(0)
    if len(sys.argv) != 8:
        raise SystemExit("Internal worker: source cache payload west south east north")
    source_path, cache_path, payload_path = map(Path, sys.argv[1:4])
    handler = SupportFeatures(tuple(float(x) for x in sys.argv[4:]))
    handler.source = source_path.name
    handler.apply_file(str(source_path), locations=True, idx=f"sparse_file_array,{cache_path}")
    payload_path.write_text(json.dumps({"features": handler.features, "diagnostics": dict(handler.counts)}), encoding="utf-8")
