# Aureon XLARGE Final Validation Benchmark Report

## Executive Summary

**Baseline (Nearest Available) significantly outperforms Aureon (Multi-Factor Intelligence) on the 736k-node real Bangalore road network.** This is an honest, statistically rigorous finding. Aureon's multi-factor scoring causes dispatch of farther ambulances to achieve better hospital/capability matching, but the transit time penalty outweighs the quality gains at city scale.

---

## Experimental Setup

| Parameter | Value |
|---|---|
| Road network | 736,057 nodes, 1,591,353 edges (real Bangalore OSM PBF) |
| Simulation duration | 120 minutes per seed |
| Seeds | 20 (42–61), paired comparison |
| Incident rate | 14.0/hour (Poisson) |
| Fleet | 50 ambulances (30% ALS), 10 stations |
| Hospitals | 28 real Bangalore hospitals |
| Strategies | NearestAvailable (baseline) vs AureonDecisionEngine |

**Integrity guarantees:**
- Both strategies receive the **identical incident schedule** per seed (deep copy from same generator)
- Fallback check: 736,057 nodes confirmed (no downscaling to 32-node toy graph)
- scipy CSR matrix and NX graph both present (no routing regression)

---

## Primary Results

### Response Time (Mean, minutes)

| Strategy | Mean | CI 95% | Std Dev |
|---|---|---|---|
| **Baseline** | **18.23** | [17.32, 19.14] | 2.08 |
| Aureon | 23.03 | [21.98, 24.08] | 2.40 |

- **Difference:** Baseline is **4.80 minutes faster** (CI95: [4.10, 5.51])
- **Paired t-test:** t = -13.35, **p < 0.0001**
- **Effect size:** Cohen's d = -2.99 (very large)
- **Wins:** Baseline wins **20/20 seeds** (100%)

### Response Time (Percentiles, minutes)

| Metric | Baseline | Aureon | Delta |
|---|---|---|---|
| Median RT | 16.52 | 20.46 | +23.8% |
| P90 RT | 31.47 | 43.55 | +38.4% |
| P95 RT | 38.30 | 50.41 | +31.6% |
| Critical RT | 18.22 | 24.34 | +33.6% |

### Completion Rate

| Metric | Baseline | Aureon | Delta |
|---|---|---|---|
| Mean completed | 15.95 | 13.45 | -15.7% |
| Mean reported | 29.30 | 29.30 | 0% (same schedule) |
| Completion rate | 54.4% | 45.9% | -8.5pp |
| Completed difference t-test | | | p < 0.0001 |

### Critical Incidents

| Metric | Baseline | Aureon |
|---|---|---|
| Critical mean RT | 18.22 min | 24.34 min |
| Difference | -6.12 min (baseline faster) |
| Effect size | Cohen's d = -3.82 |
| p-value | < 0.0001 |

### Fleet Efficiency

| Metric | Baseline | Aureon | Delta |
|---|---|---|---|
| Fleet distance (km) | 548.2 | 702.6 | +28.2% |
| Fleet utilization | 21.6% | 24.1% | +2.5pp |

### Quality Metrics (Aureon advantage)

| Metric | Baseline | Aureon |
|---|---|---|
| Hospital suitability | 0.630 | 0.767 (+21.7%) |
| Capability match rate | 0.413 | 0.946 (+129.3%) |

Aureon achieves substantially better hospital suitability and capability matching, but at the cost of significantly longer response times.

---

## Per-Seed Results

| Seed | Baseline RT | Aureon RT | Delta (%) | BL Completed | AU Completed |
|---|---|---|---|---|---|
| 42 | 16.98 | 22.26 | -31.1% | 17 | 11 |
| 43 | 19.91 | 24.70 | -24.1% | 16 | 14 |
| 44 | 15.40 | 19.58 | -27.1% | 19 | 17 |
| 45 | 17.34 | 20.34 | -17.3% | 20 | 16 |
| 46 | 13.93 | 19.87 | -42.6% | 22 | 19 |
| 47 | 20.64 | 23.43 | -13.5% | 22 | 17 |
| 48 | 18.08 | 22.21 | -22.8% | 21 | 18 |
| 49 | 22.44 | 24.58 | -9.5% | 13 | 12 |
| 50 | 19.89 | 23.87 | -20.0% | 11 | 9 |
| 51 | 17.07 | 21.74 | -27.4% | 18 | 14 |
| 52 | 16.32 | 21.73 | -33.2% | 18 | 13 |
| 53 | 20.53 | 27.64 | -34.6% | 14 | 10 |
| 54 | 15.99 | 20.67 | -29.3% | 8 | 7 |
| 55 | 19.81 | 26.01 | -31.3% | 16 | 13 |
| 56 | 17.54 | 21.85 | -24.6% | 18 | 18 |
| 57 | 17.49 | 23.69 | -35.4% | 14 | 11 |
| 58 | 18.06 | 24.49 | -35.6% | 11 | 9 |
| 59 | 17.64 | 22.32 | -26.5% | 14 | 14 |
| 60 | 19.47 | 21.44 | -10.2% | 11 | 13 |
| 61 | 20.07 | 28.21 | -40.6% | 16 | 14 |

---

## Infrastructure

| Metric | Value |
|---|---|
| Graph load time | 39.6s |
| Peak memory | 6,405 MB |
| Mean wall time (baseline) | 30.1s per seed |
| Mean wall time (aureon) | 28.6s per seed |
| Total benchmark time | ~20 min |

---

## Root Cause Analysis

**Why does Aureon lose at city scale?**

1. **Distance dominates multi-factor scoring.** On a 736k-node graph, the average inter-node distance is large. When Aureon scores an ambulance as "better" (higher hospital suitability, better capability match), that ambulance is often several kilometers farther away. The transit time penalty (~2–4 min extra per dispatch) far exceeds the quality benefit.

2. **Capacity-based hospital selection routes to distant hospitals.** Aureon's `select_hospital_for_incident` penalizes busy hospitals and favors specialty matches. On the real graph, this frequently selects a hospital 10–15 km away instead of the nearest 3–5 km away.

3. **The multi-factor scoring conflates per-dispatch optimization with fleet-level response time.** A single dispatch that selects a slightly farther but better-matched ambulance may improve that one incident's outcome quality, but it leaves the rest of the fleet in worse positions for subsequent incidents.

4. **Heuristic weights are not calibrated for city-scale geometry.** The scoring weights (congestion, proximity, hospital suitability, capability match) were tuned on a 32-node toy graph where distances are trivial. On the real network, the weight magnitudes produce fundamentally different ranking behavior.

5. **Completion rate difference compounds.** Baseline completes 15.95 incidents vs Aureon's 13.45. Each completed incident frees an ambulance for the next. Aureon's longer per-trip times create a cascading shortage.

---

## Comparison with Smaller Scales

| Scale | Nodes | Baseline RT | Aureon RT | Delta |
|---|---|---|---|---|
| SMALL | 1,000 | 3.8 min | 3.2 min | -15.8% (Aureon wins) |
| MEDIUM | 10,000 | 5.1 min | 4.8 min | -5.9% (Aureon wins) |
| LARGE | 100,000 | 7.9 min | 7.6 min | -3.8% (Aureon wins) |
| **XLARGE** | **736,057** | **18.2 min** | **23.0 min** | **+26.4% (Baseline wins)** |

The crossover from Aureon-wins to Baseline-wins occurs between 100k and 736k nodes. The multi-factor intelligence provides marginal benefit at small scales but becomes actively harmful at true city scale.

---

## Honest Assessment

**Aureon's multi-factor dispatch intelligence does not improve emergency response times at real city scale.** The system correctly identifies "better" ambulance-hospital pairings by hospital suitability (+22%) and capability matching (+129%), but these quality gains are overwhelmed by:

- 28% more fleet distance traveled
- 26.4% slower mean response times
- 15.7% fewer incidents completed
- 33.6% slower critical incident response

**This is a scientifically valid negative result.** Proximity-first dispatch (nearest available) remains the optimal strategy for minimizing response times on real road networks at city scale. The intelligence layer's value lies elsewhere (hospital suitability, capability matching) and would need to be reweighted or restructured to avoid penalizing response time.

---

## Recommendations

1. **Weight recaling:** Reduce hospital suitability and capability match weights by 5–10x so that proximity dominates and quality factors only break ties between similarly-distant ambulances.

2. **Hybrid strategy:** Use nearest-available as primary, then optimize hospital selection (not ambulance selection) to capture the quality gains without the transit penalty.

3. **Proximity-constrained scoring:** Only consider Aureon's multi-factor scoring among ambulances within a proximity threshold (e.g., within 20% of the nearest ambulance's distance).

4. **Accept the tradeoff:** If hospital suitability and capability matching are valued over raw response time, document this as a conscious design choice with quantified costs.
