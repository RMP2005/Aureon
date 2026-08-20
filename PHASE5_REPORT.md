# Phase 5 Report: Real Bangalore Digital Twin

## Executive Summary

Phase 5 implements the infrastructure for scaling Aureon from a 32-node toy graph to real OpenStreetMap road networks. All components are built, tested (53 new tests), and integrated. **The live OSM download could not be executed** due to network restrictions in the development environment — this is documented as a known limitation with clear instructions for resolution.

## What Was Built

### 1. OSM Provider (`simulation/src/maps/osm_provider.py`)
- Downloads Bangalore driving network from Overpass API via OSMnx
- Two modes: `AUREON_MAP_SOURCE=osm` (download) or `cache` (local GraphML)
- Configurable bounding box: N=13.10, S=12.84, E=77.74, W=77.54
- Auto-caches to `simulation/data/osm_cache/bangalore_drive.graphml`
- Cache file info, stats tracking, graceful error handling

### 2. Graph Processor (`simulation/src/maps/graph_processor.py`)
- Converts OSMnx MultiDiGraph → Aureon RoadNetwork
- **KD-tree spatial index** (scipy cKDTree) for O(log n) nearest-node lookup
- OSM highway → Aureon RoadType mapping (motorway→EXPRESSWAY, primary→PRIMARY_ARTERIAL, etc.)
- Automatic zone assignment via geographic bounding boxes
- Speed estimation from OSM maxspeed tags with road-type fallbacks

### 3. Hospital Dataset (`simulation/src/maps/bangalore_hospitals.py`)
- **Real hospital names and coordinates** for 28 Bangalore hospitals
- Three scales: small (6), medium (15), large (28)
- **ALL capacity numbers explicitly marked as "SIMULATION CONFIGURATION"**
- Hospitals include: NIMHANS, Bowring, Victoria, Vani Vilas, Manipal, St. John's, Narayana Health, Apollo, Aster CMI, Vydehi, Fortis, Columbia Asia, Rainbow Children's, Motherhood, Sakra, MS Ramaiah, Sapthagiri, Jayadeva, Cloudnine, and more

### 4. Ambulance Stations + Fleet (`simulation/src/maps/ambulance_stations.py`)
- 10 geographically distributed stations across Bangalore
- Configurable fleet sizes: 14 (small), 30 (medium), 50 (large), 100 (xlarge)
- Proportional station distribution with 30% ALS ratio
- Unique IDs, callsigns, proper status initialization

### 5. Spatial Traffic Model (`simulation/src/maps/traffic_model.py`)
- **Spatially correlated** — adjacent roads in same zone share congestion
- Time-of-day: morning peak (07:30-10:30), midday, evening peak (16:30-20:00), night
- Road-class effects: expressway (0.8x), arterial (1.2x), residential (1.0x)
- Zone-specific: Silk Board (2.5x peak), ORR Marathahalli (2.0x peak), MG Road CBD (1.5x)
- ±15% stochastic variation, deterministic per (seed, zone, time_bucket)
- Congestion events with distance falloff and auto-expiry

### 6. Traffic Events (`simulation/src/maps/traffic_events.py`)
- Four event types: road closure, congestion spike, construction, incident blockage
- Road closures use 25x congestion factor (forces rerouting)
- Construction reduces lanes + moderate slowdown
- Random event generation distributed across simulation duration
- 70% hotspot-biased (Silk Board, Hebbal, Marathahalli, etc.)
- Network update with original state snapshots and restoration

### 7. Intersection Delay Model (`simulation/src/maps/intersection_model.py`)
- Configurable per-intersection signal delay (default 15s)
- Road-class specific: expressway (0s), arterial (20s), residential (10s)
- Emergency priority preemption (50% delay reduction)
- Turn penalty for road-class changes
- NoIntersectionDelay null-object for backward compatibility

### 8. Benchmark Configs (`simulation/src/maps/benchmark_configs.py`)

| Scale | Nodes | Fleet | OSM | Traffic Events | Intersection Delays |
|---|---|---|---|---|---|
| SMALL | 32 | 14 | No (legacy) | No | No |
| MEDIUM | ~5k | 30 | Yes | Yes | Yes |
| LARGE | ~50k | 50 | Yes | Yes | Yes |

## Known Limitation: OSM Graph Unavailable

**The Overpass API (overpass-api.de) was unreachable from this development environment** (connection refused). This means:

- MEDIUM and LARGE benchmarks **fall back to the 32-node graph** with a clear limitation message
- The complete OSM download → cache → processor pipeline is built and tested
- **To run MEDIUM/LARGE benchmarks**: execute on a machine with network access:
  ```bash
  AUREON_MAP_SOURCE=osm PYTHONPATH=simulation/src python3.14 -c "
  from simulation.src.maps.osm_provider import OSMProvider
  OSMProvider().load()
  "
  ```
  This generates `simulation/data/osm_cache/bangalore_drive.graphml` (~2-10 MB)
- Subsequent runs use the cache automatically (`AUREON_MAP_SOURCE=cache`)

## Benchmark Results (SMALL Scale, 20 Seeds)

| Metric | Baseline | Heuristic Aureon | Difference |
|---|---|---|---|
| Mean RT (min) | 11.17 | 13.14 | **-17.7%** (worse) |
| 95% CI | [9.85, 12.49] | [12.20, 14.09] | CI overlaps |
| P50 RT (min) | 11.43 | 12.95 | — |
| P90 RT (min) | 42.62 | 46.38 | — |
| Critical RT (min) | 10.91 | 12.74 | — |
| Completed incidents | 5.4 | 4.7 | — |
| Distance (km) | 172.2 | 185.3 | — |

**Honest assessment**: Heuristic Aureon does NOT improve over baseline at any scale tested. The multi-factor dispatch heuristic is worse than nearest-available on the 32-node graph. This is consistent with Phase 4 results.

## Test Results

```
Phase 5 tests: 53 passed (0.71s)
Full test suite: 124 passed, 1 failed (pre-existing: 6 zones vs 5 expected)
```

## Performance

| Operation | Time |
|---|---|
| 32-node graph build | <1ms |
| Per-seed simulation (30 min) | ~10ms |
| 20-seed benchmark total | ~0.2s |
| KD-tree build (for OSM) | ~0.1s (estimated for 50k nodes) |
| KD-tree nearest-node query | O(log n) sub-ms |

## Data Sources vs Simulation Parameters

### REAL DATA
- Hospital names and approximate geographic coordinates
- Road network topology (when OSM is loaded)
- Bangalore geographic bounding box
- Zone definitions based on actual Bangalore neighborhoods
- Ambulance station locations (based on real Bangalore EMS infrastructure)

### SIMULATION PARAMETERS (clearly marked)
- All hospital capacity numbers (beds, ICU, occupancy)
- Traffic congestion multipliers and time-of-day factors
- Intersection delay values
- Fleet size configurations
- Incident rates and severity distributions

## Files Created

```
simulation/src/maps/__init__.py
simulation/src/maps/osm_provider.py          # OSM download/cache
simulation/src/maps/graph_processor.py       # KD-tree + OSM→Aureon conversion
simulation/src/maps/bangalore_hospitals.py    # 28 real hospitals, synthetic capacity
simulation/src/maps/ambulance_stations.py     # 10 stations, 4 fleet configs
simulation/src/maps/traffic_model.py          # Spatially correlated traffic
simulation/src/maps/traffic_events.py         # Road closures, construction
simulation/src/maps/intersection_model.py     # Signal delays
simulation/src/maps/benchmark_configs.py      # SMALL/MEDIUM/LARGE configs
simulation/src/evaluation/phase5_benchmark.py # Scale benchmark runner
simulation/tests/test_phase5.py               # 53 tests
simulation/data/osm_cache/                    # Cache directory (empty until OSM download)
```
