"""OpenStreetMap graph provider with download and local caching.

Downloads Bangalore road network via OSMnx and caches the result locally.
Supports two modes:
  - 'osm': Download from Overpass API (requires network access)
  - 'cache': Load from local GraphML cache

Configuration:
  AUREON_MAP_SOURCE=cache|osm
  AUREON_MAP_CACHE_DIR=simulation/data/osm_cache

Limitation:
  Live OSM download requires network access to overpass-api.de.
  If unavailable, pre-generate the cache on a machine with access
  and copy the .graphml file to the cache directory.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("aureon.maps.osm_provider")

# Default Bangalore bounding box covering all requested areas:
# Electronic City (south) to Yelahanka (north), Bannerghatta (west) to Whitefield (east)
BANGALORE_BBOX_NORTH = 13.10
BANGALORE_BBOX_SOUTH = 12.84
BANGALORE_BBOX_EAST = 77.74
BANGALORE_BBOX_WEST = 77.54


@dataclass
class OSMGraphStats:
    """Statistics about a loaded OSM graph."""

    node_count: int
    edge_count: int
    bbox: tuple[float, float, float, float]
    source: str  # "osm" or "cache"
    load_time_sec: float
    file_size_bytes: int = 0


class OSMProvider:
    """Loads Bangalore road network from OpenStreetMap or local cache.

    Usage:
        provider = OSMProvider()
        graph = provider.load()
        stats = provider.last_stats
    """

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        source: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> None:
        """
        Args:
            cache_dir: Directory for cached .graphml files.
                       Defaults to simulation/data/osm_cache relative to repo root.
            source: 'osm' or 'cache'. Defaults to AUREON_MAP_SOURCE env var, then 'cache'.
            bbox: (north, south, east, west). Defaults to Bangalore bounding box.
        """
        self.bbox = bbox or (BANGALORE_BBOX_NORTH, BANGALORE_BBOX_SOUTH,
                             BANGALORE_BBOX_EAST, BANGALORE_BBOX_WEST)

        if cache_dir is None:
            # Walk up from this file to find repo root
            repo_root = Path(__file__).resolve().parent.parent.parent.parent
            self.cache_dir = repo_root / "simulation" / "data" / "osm_cache"
        else:
            self.cache_dir = Path(cache_dir)

        self.source = source or os.environ.get("AUREON_MAP_SOURCE", "cache")
        self.cache_filename = "bangalore_drive.graphml"
        self._last_stats: OSMGraphStats | None = None

    @property
    def last_stats(self) -> OSMGraphStats | None:
        return self._last_stats

    @property
    def cache_path(self) -> Path:
        return self.cache_dir / self.cache_filename

    def load(self) -> Any:
        """Load the road network graph.

        Returns:
            NetworkX MultiDiGraph with OSM node/edge attributes.

        Raises:
            FileNotFoundError: If source='cache' and no cache file exists.
            RuntimeError: If source='osm' and download fails.
        """
        if self.source == "cache":
            return self._load_from_cache()
        elif self.source == "osm":
            return self._download_and_cache()
        else:
            raise ValueError(f"Unknown source: {self.source}. Use 'osm' or 'cache'.")

    def _load_from_cache(self) -> Any:
        """Load graph from local GraphML cache."""
        if not self.cache_path.exists():
            raise FileNotFoundError(
                f"Cache not found: {self.cache_path}\n"
                f"To generate: set AUREON_MAP_SOURCE=osm on a machine with network access,\n"
                f"or copy a pre-built {self.cache_filename} to {self.cache_dir}/"
            )

        t0 = time.time()
        import osmnx as ox
        G = ox.load_graphml(str(self.cache_path))
        elapsed = time.time() - t0

        file_size = self.cache_path.stat().st_size
        self._last_stats = OSMGraphStats(
            node_count=G.number_of_nodes(),
            edge_count=G.number_of_edges(),
            bbox=self.bbox,
            source="cache",
            load_time_sec=elapsed,
            file_size_bytes=file_size,
        )
        logger.info(
            "Loaded cached OSM graph: %d nodes, %d edges (%.1f MB, %.2fs)",
            self._last_stats.node_count,
            self._last_stats.edge_count,
            file_size / (1024 * 1024),
            elapsed,
        )
        return G

    def _download_and_cache(self) -> Any:
        """Download from Overpass API and save to local cache."""
        import osmnx as ox

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Downloading Bangalore driving network (bbox=%s)...", self.bbox)
        t0 = time.time()
        G = ox.graph_from_bbox(
            bbox=self.bbox,
            network_type="drive",
            simplify=True,
        )
        elapsed = time.time() - t0
        logger.info("Downloaded in %.1fs", elapsed)

        # Save to cache
        ox.save_graphml(G, filepath=str(self.cache_path))
        file_size = self.cache_path.stat().st_size

        self._last_stats = OSMGraphStats(
            node_count=G.number_of_nodes(),
            edge_count=G.number_of_edges(),
            bbox=self.bbox,
            source="osm",
            load_time_sec=elapsed,
            file_size_bytes=file_size,
        )
        return G

    def get_cache_info(self) -> dict[str, Any]:
        """Return info about the cached graph file."""
        if not self.cache_path.exists():
            return {"exists": False, "path": str(self.cache_path)}

        stat = self.cache_path.stat()
        return {
            "exists": True,
            "path": str(self.cache_path),
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
        }
