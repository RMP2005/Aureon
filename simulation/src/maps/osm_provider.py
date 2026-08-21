"""OpenStreetMap graph provider with download, local caching, and PBF ingestion.

Supports three modes:
  - 'cache': Load from local GraphML cache
  - 'osm':   Download from Overpass API (requires network access)
  - 'pbf':   Load from a local .osm.pbf file via pyrosm

Configuration:
  AUREON_MAP_SOURCE=cache|osm|pbf

PBF workflow:
  1. Place a .osm.pbf file in the cache directory.
  2. For large region PBFs (e.g. entire state), the provider uses
     osmium CLI to pre-extract the Bangalore bounding box, then
     pyrosm to parse the result into NetworkX.
  3. The result is a NetworkX MultiDiGraph compatible with GraphProcessor.

Limitation:
  Live OSM download requires network access to overpass-api.de.
  If unavailable, use a local PBF file or pre-generated GraphML cache.
"""

from __future__ import annotations

import glob
import logging
import os
import subprocess
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

# PBF file size threshold (bytes) above which we use osmium extract first
_PBF_LARGE_THRESHOLD = 100 * 1024 * 1024  # 100 MB


@dataclass
class OSMGraphStats:
    """Statistics about a loaded OSM graph."""

    node_count: int
    edge_count: int
    bbox: tuple[float, float, float, float]
    source: str  # "osm", "cache", or "pbf"
    load_time_sec: float
    file_size_bytes: int = 0


class OSMProvider:
    """Loads Bangalore road network from OpenStreetMap, local cache, or PBF.

    Usage:
        # From cache
        provider = OSMProvider(source="cache")
        graph = provider.load()

        # From local PBF
        provider = OSMProvider(source="pbf")
        graph = provider.load()
    """

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        source: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        pbf_filename: str | None = None,
    ) -> None:
        """
        Args:
            cache_dir: Directory for cached files.
                       Defaults to simulation/data/osm_cache relative to repo root.
            source: 'osm', 'cache', or 'pbf'.
                    Defaults to AUREON_MAP_SOURCE env var, then 'cache'.
            bbox: (north, south, east, west). Defaults to Bangalore bounding box.
            pbf_filename: Name of the .osm.pbf file to load when source='pbf'.
                          If None, auto-discovers the first .osm.pbf in cache_dir.
        """
        self.bbox = bbox or (BANGALORE_BBOX_NORTH, BANGALORE_BBOX_SOUTH,
                             BANGALORE_BBOX_EAST, BANGALORE_BBOX_WEST)

        if cache_dir is None:
            repo_root = Path(__file__).resolve().parent.parent.parent.parent
            self.cache_dir = repo_root / "simulation" / "data" / "osm_cache"
        else:
            self.cache_dir = Path(cache_dir)

        self.source = source or os.environ.get("AUREON_MAP_SOURCE", "cache")
        self.cache_filename = "bangalore_drive.graphml"
        self._pbf_filename = pbf_filename
        self._last_stats: OSMGraphStats | None = None

    @property
    def last_stats(self) -> OSMGraphStats | None:
        return self._last_stats

    @property
    def cache_path(self) -> Path:
        return self.cache_dir / self.cache_filename

    def _find_pbf(self) -> Path:
        """Locate the .osm.pbf file to use."""
        if self._pbf_filename:
            p = self.cache_dir / self._pbf_filename
            if not p.exists():
                raise FileNotFoundError(f"PBF file not found: {p}")
            return p

        # Auto-discover: prefer files without date stamps (e.g. bangalore.osm.pbf)
        candidates = sorted(glob.glob(str(self.cache_dir / "*.osm.pbf")))
        if not candidates:
            raise FileNotFoundError(
                f"No .osm.pbf files found in {self.cache_dir}\n"
                f"Place a PBF file there, or use source='cache' with a GraphML file."
            )
        # Prefer shortest name (likely the extracted one)
        return Path(min(candidates, key=lambda p: len(Path(p).stem)))

    def _extract_pbf_bbox(self, src_pbf: Path) -> Path:
        """Use osmium CLI to extract the Bangalore bbox from a large PBF.

        Returns the path to the extracted (smaller) PBF file.
        """
        out_pbf = self.cache_dir / "bangalore_extracted.osm.pbf"
        if out_pbf.exists():
            logger.info("Using cached extraction: %s", out_pbf)
            return out_pbf

        # osmium extract uses: west,south,east,north
        bbox_str = f"{self.bbox[3]},{self.bbox[1]},{self.bbox[2]},{self.bbox[0]}"
        logger.info(
            "Extracting bbox %s from %s via osmium...", bbox_str, src_pbf.name,
        )
        t0 = time.time()
        result = subprocess.run(
            ["osmium", "extract", "-b", bbox_str, str(src_pbf),
             "-o", str(out_pbf), "--overwrite"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"osmium extract failed (rc={result.returncode}): {result.stderr}"
            )
        elapsed = time.time() - t0
        size_mb = out_pbf.stat().st_size / (1024 * 1024)
        logger.info("Extracted to %s (%.1f MB, %.1fs)", out_pbf.name, size_mb, elapsed)
        return out_pbf

    def _load_pbf(self) -> Any:
        """Load a NetworkX graph from a local .osm.pbf file via pyrosm."""
        import pyrosm

        src_pbf = self._find_pbf()
        src_size = src_pbf.stat().st_size
        logger.info("PBF source: %s (%.1f MB)", src_pbf.name, src_size / (1024 * 1024))

        # For large PBFs, extract the Bangalore bbox first
        if src_size > _PBF_LARGE_THRESHOLD:
            pbf_to_parse = self._extract_pbf_bbox(src_pbf)
        else:
            pbf_to_parse = src_pbf

        t0 = time.time()
        osm = pyrosm.OSM(str(pbf_to_parse))
        nodes_df, edges_df = osm.get_network(nodes=True, network_type="drive")
        t1 = time.time()
        logger.info(
            "pyrosm extracted %d nodes, %d edges (%.1fs)",
            len(nodes_df), len(edges_df), t1 - t0,
        )

        G = osm.to_graph(nodes_df, edges_df, graph_type="networkx")
        t2 = time.time()
        logger.info(
            "NetworkX graph: %d nodes, %d edges (%.1fs)",
            G.number_of_nodes(), G.number_of_edges(), t2 - t1,
        )

        file_size = pbf_to_parse.stat().st_size
        self._last_stats = OSMGraphStats(
            node_count=G.number_of_nodes(),
            edge_count=G.number_of_edges(),
            bbox=self.bbox,
            source="pbf",
            load_time_sec=t2 - t0,
            file_size_bytes=file_size,
        )
        return G

    def load(self) -> Any:
        """Load the road network graph.

        Returns:
            NetworkX MultiDiGraph with OSM node/edge attributes.

        Raises:
            FileNotFoundError: If source='cache' and no cache file exists.
            FileNotFoundError: If source='pbf' and no PBF file exists.
            RuntimeError: If source='osm' and download fails.
        """
        if self.source == "cache":
            return self._load_from_cache()
        elif self.source == "osm":
            return self._download_and_cache()
        elif self.source == "pbf":
            return self._load_pbf()
        else:
            raise ValueError(
                f"Unknown source: {self.source}. Use 'osm', 'cache', or 'pbf'."
            )

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
