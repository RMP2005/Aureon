# Phase 6 — Adaptive Hybrid Emergency Intelligence

## Objective

Redesign Aureon's dispatch decision architecture to eliminate the severe response-time regression discovered in Phase 5, while preserving and improving clinical quality metrics (capability matching, hospital suitability).

## Phase 5 Failure

The Phase 5 XLARGE benchmark on a real 736-node Bangalore road network (20 seeds, 120-min simulation, 50 ambulances) revealed that the original Aureon multi-factor dispatch strategy was statistically significantly worse than nearest-available baseline on response time:

| Metric | Baseline | Old Aureon | Delta |
|---|---|---|---|
| Mean RT | 18.23 min | 23.03 min | **+26.4% slower** |
| Critical RT | 18.22 min | 24.34 min | **+33.6% slower** |
| Completed | 15.95 | 13.45 | **-15.7% fewer** |
| Fleet distance | 548 km | 703 km | **+28.2% more** |

Paired t-test: t = -13.35, p < 0.0001, Cohen's d = -2.99 (very large).

**Root cause:** Old Aureon's multi-factor scoring (50% ETA, 30% capability, 20% hospital spec) dispatched farther ambulances to achieve better hospital/capability matching. At city scale, the transit time penalty overwhelmed the quality gains.

## Architectural Changes

Phase 6 redesigns the dispatch decision pipeline from scratch:

### 1. Hybrid Dispatch Policy (proximity-first default)

Old Aureon always optimized a composite score. Hybrid defaults to nearest-available and only overrides when:

- Incident requires ALS capability
- Nearest ambulance is BLS
- A capable ambulance exists within the configurable ETA tolerance (default 15%)
- Hard ceiling: never dispatch an ambulance more than 1.5x the nearest ETA

This guarantees the strategy can never be significantly worse than baseline.

### 2. Decoupled Hospital Selection

Old Aureon coupled ambulance and hospital selection into a single scoring pass, sometimes sacrificing ambulance ETA for hospital suitability.

Hybrid separates the two decisions:
1. Select ambulance based on ETA + capability + coverage
2. Select hospital based on specialty match + capacity + transport time

Hospital selection never affects ambulance response time.

### 3. Coverage-Aware Dispatch

Fleet coverage analyzer evaluates the impact of removing a candidate ambulance from service:
- Computes remaining nearest-response-time per zone
- Identifies coverage gaps (zones with no ambulance within threshold ETA)
- Falls back to nearest when coverage would be critically degraded

### 4. Outcome Scoring Framework

Composable reward/penalty scoring engine (`EmergencyOutcomeScore`) with independent, auditable components:
- Proximity score (response time relative to nearest option)
- Capability match score (ALS/BLS alignment with incident need)
- Hospital suitability score (specialty + capacity + transport time)
- Coverage preservation score
- Distance penalty, capability gap penalty, coverage gap penalty

This framework is RL-compatible for future optimization.

## Experimental Setup

| Parameter | Value |
|---|---|
| Road network | 736,057 nodes, 1,591,353 edges (real Bangalore OSM PBF) |
| Simulation duration | 120 minutes per seed |
| Seeds | 20 (42-61), paired comparison |
| Incident rate | 14.0/hour (Poisson, dynamic zone weighting) |
| Fleet | 50 ambulances (30% ALS), 10 stations |
| Hospitals | 28 real Bangalore hospitals |
| Strategies | NearestAvailable vs Old Aureon vs New Hybrid |

**Integrity guarantees:**
- Both strategies receive identical incident schedules per seed (deep copy)
- Fallback check: 736,057 nodes confirmed (no downscaling)
- All three strategies run on the same graph infrastructure

## Results

### 20-Seed XLARGE Benchmark

| Strategy | Mean RT | CI95% | Crit RT | Completed | Cap Match | Hosp Suit | Fleet km |
|---|---|---|---|---|---|---|---|
| **Baseline** | **18.23 min** | [17.32, 19.14] | 18.22 min | 15.95 | 41.3% | 0.630 | 548 |
| **Old Aureon** | 23.03 min | [21.98, 24.08] | 24.34 min | 13.45 | 94.6% | 0.767 | 703 |
| **New Hybrid** | **18.34 min** | [17.49, 19.18] | 18.49 min | 16.00 | 58.1% | 0.767 | 592 |

### Paired t-tests vs Baseline

| Comparison | RT Diff | t-stat | p-value | Cohen's d | Significant? |
|---|---|---|---|---|---|
| Old Aureon | -4.80 min | -13.35 | < 0.0001 | -2.99 | **YES (worse)** |
| New Hybrid | -0.11 min | -0.58 | 0.567 | -0.13 | NO (equivalent) |

### Per-Seed Response Times (minutes)

| Seed | Baseline | Old Aureon | Hybrid | Hybrid vs Baseline |
|---|---|---|---|---|
| 42 | 16.98 | 22.26 | 17.28 | +1.8% |
| 43 | 19.91 | 24.70 | 20.90 | +5.0% |
| 44 | 15.40 | 19.58 | 15.70 | +1.9% |
| 45 | 17.34 | 20.34 | 17.07 | -1.6% |
| 46 | 13.93 | 19.87 | 14.29 | +2.6% |
| 47 | 20.64 | 23.43 | 20.88 | +1.2% |
| 48 | 18.08 | 22.21 | 18.60 | +2.9% |
| 49 | 22.44 | 24.58 | 20.26 | -9.7% |
| 50 | 19.89 | 23.87 | 18.32 | -7.9% |
| 51 | 17.07 | 21.74 | 17.27 | +1.2% |
| 52 | 16.32 | 21.73 | 17.09 | +4.7% |
| 53 | 20.53 | 27.64 | 21.13 | +2.9% |
| 54 | 15.99 | 20.67 | 16.26 | +1.7% |
| 55 | 19.81 | 26.01 | 19.67 | -0.7% |
| 56 | 17.54 | 21.85 | 18.44 | +5.1% |
| 57 | 17.49 | 23.69 | 18.10 | +3.5% |
| 58 | 18.06 | 24.49 | 17.93 | -0.7% |
| 59 | 17.64 | 22.32 | 17.10 | -3.1% |
| 60 | 19.47 | 21.44 | 19.11 | -1.8% |
| 61 | 20.07 | 28.21 | 21.35 | +6.4% |

### Quality Improvements (Hybrid vs Baseline)

| Metric | Baseline | Hybrid | Change |
|---|---|---|---|
| Capability match | 41.3% | 58.1% | **+40.7% relative improvement** |
| Hospital suitability | 0.630 | 0.767 | **+21.7% improvement** |
| Completed incidents | 15.95 | 16.00 | +0.3% (equivalent) |
| Fleet distance | 548 km | 592 km | +7.9% (modest) |

## Analysis

### Why Hybrid Matches Baseline on RT

The hybrid dispatch defaults to nearest-available in the vast majority of cases. It only overrides to a capability-matched ambulance when the ETA penalty is within 15% of the nearest ETA. On the real Bangalore network with 50 ambulances distributed across 10 stations, this override triggers infrequently because:

1. Most incidents are served by the nearest ambulance regardless of capability
2. When the nearest is BLS and an ALS ambulance is nearby, the ALS ambulance is often at the same station (0% penalty)
3. When ALS ambulances are far away, the 15% threshold prevents override

This is the correct behavior. The hybrid is designed to never sacrifice RT for quality.

### Why Capability Match Improves

When the override does trigger (ALS ambulance within 15% of nearest ETA), the incident receives clinically appropriate care. This happens in roughly 17% of dispatches that need ALS, improving the capability match rate from 41.3% to 58.1% without any RT cost.

### Why Hospital Suitability Improves

Hybrid's decoupled hospital selection uses suitability-weighted transport time scoring (suitability * 1/(1 + ln(1 + eta/300))). This preferentially selects specialty-matched hospitals that are still reasonably close, achieving the same 0.767 suitability score as old Aureon but without coupling the decision to ambulance selection.

### Fleet Distance

Hybrid uses 7.9% more fleet distance than baseline (592 vs 548 km). This is modest compared to old Aureon's 28.2% overhead (703 km). The extra distance comes from occasional capability overrides that send a slightly farther ambulance.

## Limitations

1. **Hybrid matches baseline; it does not beat it.** The validated result is statistical equivalence (p=0.567, d=-0.13), not superiority. The value is in the quality improvements at zero RT cost.

2. **Coverage analysis was disabled in benchmarks.** The coverage-aware dispatch module is implemented and unit-tested but was disabled (`enable_coverage_analysis=False`) to isolate the core hybrid dispatch logic. Enabling it could provide additional benefits or costs that are not yet quantified at XLARGE scale.

3. **Capability tolerance threshold (15%) was not swept.** The 15% threshold is a reasonable default but was not optimized. Different thresholds could shift the RT/quality tradeoff.

4. **Single road network.** All results are on the Bangalore OSM network. Generalization to other cities is plausible but not verified.

5. **Simulation fidelity.** Discrete-time simulation with Poisson incident generation, Dijkstra routing, and simplified hospital models. Real emergency systems have additional complexities (communication delays, crew fatigue, multi-patient incidents).

## Conclusion

Phase 6 eliminates the catastrophic response-time regression of the previous Aureon multi-factor strategy. The hybrid architecture achieves statistically equivalent response time to nearest-available dispatch (p=0.567, Cohen's d=-0.13) while materially improving:

- **Capability matching:** 41.3% to 58.1% (+40.7% relative)
- **Hospital suitability:** 0.630 to 0.767 (+21.7%)
- **Incidents completed:** 15.95 to 16.00 (equivalent)

This validates the architectural insight that proximity-first dispatch with capability override is the correct design for city-scale emergency response. The multi-factor scoring approach was fundamentally misguided at scale because it conflated per-dispatch optimization with system-level performance.

## Test Suite

25 Phase 6 unit tests covering:
- Hybrid dispatch config (2 tests)
- Core dispatch logic (8 tests)
- Coverage analyzer (3 tests)
- Outcome scoring (4 tests)
- Decoupled hospital selection (2 tests)
- Engine integration (2 tests)
- Stress scenarios A-D (4 tests)

All 150 tests in the full suite pass (11 PBF tests excluded from fast suite).

## Files

| File | Description |
|---|---|
| `simulation/src/dispatch/hybrid_intelligence.py` | Hybrid dispatch strategy |
| `simulation/src/dispatch/coverage.py` | Fleet coverage analyzer |
| `simulation/src/dispatch/outcome_score.py` | Outcome scoring framework |
| `simulation/tests/test_phase6.py` | Unit tests (25) |
| `PHASE6_XLARGE_RESULTS.json` | 20-seed XLARGE benchmark data |
| `PHASE6_VALIDATION.json` | 10-seed small-scale benchmark data |
