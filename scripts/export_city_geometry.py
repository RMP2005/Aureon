#!/usr/bin/env python3
"""Export a compact Bengaluru arterial skeleton for the Phase 10B digital twin.

Distills the cached OSM drive graph (314 MB GraphML — far too heavy for the
browser) into a small JSON payload consumed by the frontend twin:

    frontend/src/data/bangalore-city.json

Contents:
  - bbox            geographic envelope of the kept network
  - segments        [lng1, lat1, lng2, lat2, tier] arterial road segments
                    (tier: 0 = trunk, 1 = primary, 2 = secondary)
  - hospitals       {id, name, lat, lng} from the simulation hospital dataset
  - stations        ambulance base stations from the station dataset

Reproducible: reads only committed datasets + the OSM cache produced by the
standard osm_provider flow. Run from repo root:

    python3 scripts/export_city_geometry.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "simulation"))

GRAPHML_PATH = REPO_ROOT / "simulation/data/osm_cache/bangalore_drive.graphml"
OUTPUT_PATH = REPO_ROOT / "frontend/src/data/bangalore-city.json"

# Arterial classes worth drawing at city scale, mapped to draw tiers.
HIGHWAY_TIER = {
    "trunk": 0,
    "trunk_link": 0,
    "primary": 1,
    "primary_link": 1,
    "secondary": 2,
    "secondary_link": 2,
}


def main() -> None:
    import networkx as nx

    from src.maps.ambulance_stations import get_stations
    from src.maps.bangalore_hospitals import get_all_hospital_locations

    t0 = time.time()
    print(f"Loading {GRAPHML_PATH.name} ({GRAPHML_PATH.stat().st_size / 1e6:.0f} MB)…")
    graph = nx.read_graphml(GRAPHML_PATH)
    print(f"Loaded in {time.time() - t0:.1f}s — "
          f"{graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")

    seen_segments: set[tuple[str, str]] = set()
    segments: list[list[float]] = []
    min_lat = min_lng = float("inf")
    max_lat = max_lng = float("-inf")

    def track(lat: float, lng: float) -> None:
        nonlocal min_lat, min_lng, max_lat, max_lng
        min_lat = min(min_lat, lat)
        max_lat = max(max_lat, lat)
        min_lng = min(min_lng, lng)
        max_lng = max(max_lng, lng)

    t1 = time.time()
    for u, v, data in graph.edges(data=True):
        highway = data.get("highway")
        if isinstance(highway, list):
            highway = highway[0] if highway else None
        tier = HIGHWAY_TIER.get(highway)
        if tier is None:
            continue

        n_u, n_v = graph.nodes[u], graph.nodes[v]
        # osmnx stores coordinates under x (lng) and y (lat)
        try:
            lng1, lat1 = float(n_u["x"]), float(n_u["y"])
            lng2, lat2 = float(n_v["x"]), float(n_v["y"])
        except (KeyError, TypeError, ValueError):
            continue

        key = (f"{lng1:.6f},{lat1:.6f}", f"{lng2:.6f},{lat2:.6f}")
        dedupe_key = tuple(sorted(key))
        if dedupe_key in seen_segments:
            continue
        seen_segments.add(dedupe_key)

        segments.append([
            round(lng1, 5), round(lat1, 5),
            round(lng2, 5), round(lat2, 5),
            tier,
        ])
        track(lat1, lng1)
        track(lat2, lng2)

    print(f"Filtered to {len(segments)} arterial segments in {time.time() - t1:.1f}s")

    hospitals = [
        {"id": f"hosp_{i}", "name": name, "lat": round(lat, 5), "lng": round(lng, 5)}
        for i, (name, lat, lng) in enumerate(get_all_hospital_locations())
    ]
    stations = [
        {"id": f"stn_{i}", "name": s.name, "lat": round(s.latitude, 5), "lng": round(s.longitude, 5)}
        for i, s in enumerate(get_stations())
    ]

    payload = {
        "bbox": {
            "minLat": round(min_lat, 5), "maxLat": round(max_lat, 5),
            "minLng": round(min_lng, 5), "maxLng": round(max_lng, 5),
        },
        "segments": segments,
        "hospitals": hospitals,
        "stations": stations,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, separators=(",", ":")))
    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} "
          f"({size_kb:.0f} KB, {len(hospitals)} hospitals, {len(stations)} stations)")


if __name__ == "__main__":
    main()
