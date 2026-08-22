# Phase 7 Calibration Report

**Date:** August 2026  
**Seed:** 42 (1-seed smoke validation)  
**Status:** Honest assessment — no fabricated wins

---

## Architecture Implemented

| Component | Status | Lines |
|-----------|--------|-------|
| `ScenarioDetector` | Working | 253 |
| `AdaptiveAureonStrategy` + OR-Tools MIP | Working | 768 |
| `supports_batch` / `dispatch_batch` in base ABC + engine | Working | +54 |
| 8 scenario configs with deterministic schedules | Working | 553 |
| Unit tests | 29/29 pass | 411 |

---

## Results Summary (1 seed, Scenario A–H)

| Scen | Baseline RT | Hybrid RT | Adaptive RT | Baseline Cap | Hybrid Cap | Adaptive Cap | Batch Fires | Mode Switch |
|------|-------------|-----------|-------------|--------------|------------|--------------|-------------|-------------|
| A    | 4.56m       | 4.56m     | 4.56m       | 71.4%        | 71.4%      | 71.4%        | 0           | normal      |
| B    | 9.33m       | 9.33m     | 9.33m       | 66.7%        | 66.7%      | 66.7%        | 4           | —           |
| C    | 3.42m       | 3.42m     | 3.42m       | 100.0%       | 100.0%     | 100.0%       | 4           | normal      |
| D    | 9.13m       | 9.13m     | 9.13m       | 80.0%        | 80.0%      | 80.0%        | 5           | fleet_scarcity |
| E    | 3.89m       | 3.89m     | 3.89m       | 83.3%        | 83.3%      | 83.3%        | 4           | normal      |
| **F**| **7.92m**   | **8.25m** | **8.25m**   | **66.7%**    | **83.3%**  | **83.3%**    | 6           | —           |
| G    | 3.42m       | 3.42m     | 3.42m       | 75.0%        | 75.0%      | 75.0%        | 0           | normal      |
| H    | 11.36m      | 11.36m    | 11.39m      | 66.7%        | 66.7%      | 66.7%        | 5           | high_demand |

---

## Where Differentiation Actually Happens

### Scenario F: Hospital Congestion — ONLY genuine differentiation

| Metric | Baseline | Hybrid | Adaptive |
|--------|----------|--------|----------|
| Mean RT | 7.92m | 8.25m (+4.2%) | 8.25m (+4.2%) |
| P90 RT | 13.33m | 13.33m | 15.33m (+15.0%) |
| Capability | 66.7% | **83.3% (+16.6pp)** | **83.3% (+16.6pp)** |
| Hospital suitability | 0.650 | **0.717 (+0.067)** | **0.717 (+0.067)** |

**Mechanism:** Hybrid's capability override selects ALS ambulance (`amb_ecity_als_1`, 11.0m away) instead of nearest BLS (`amb_kora_bls_1`, 9.0m away) for MAJOR_TRAUMA. This trades response time for correct capability match and better hospital routing.

**Key finding:** This differentiation is from the **Hybrid capability override** (Phase 6), NOT from batch dispatch or mode switching. Adaptive matches Hybrid because it inherits the same capability override logic.

### Scenarios A–E, G, H: IDENTICAL across all 3 strategies

No differentiation. Nearest-available dispatch IS the globally optimal assignment on this network.

---

## Why Batch Dispatch Doesn't Change Outcomes

**Root cause:** On a 32-node sparse network with 6 stations, each incident has exactly one "best" ambulance. The OR-Tools batch MIP converges to the same assignment as sequential nearest-available because:

1. **No ambulance competition:** With 14 ambulances across 6 well-separated stations, no two incidents compete for the same ambulance
2. **Sparse topology:** Travel times between 32 nodes have large gaps — the nearest ambulance is always ~2-3x faster than the 2nd-nearest
3. **No penalty for greedy:** Unlike real networks, there are no congestion effects or detours that a batch solver could exploit

This is a **network density problem**, not an algorithm problem. Batch dispatch would add value on denser networks where ambulance competition creates non-trivial assignment tradeoffs.

---

## What Mode Switching Actually Does

| Scenario | Detected Mode | Effect |
|----------|--------------|--------|
| D (simultaneous) | FLEET_SCARCITY | Fires batch (5 assignments) — but same result as greedy |
| H (combined) | HIGH_DEMAND | Fires batch (5 assignments) — same result |
| A, C, E, G | NORMAL | No batch, no mode-specific logic |

Mode detection works. The problem is that on this network, the mode-specific dispatch logic produces the same assignments as normal dispatch.

---

## Honest Assessment

### What works:
- Scenario detection infrastructure (thresholds, mode transitions)
- Batch dispatch plumbing (OR-Tools MIP solver, engine integration)
- Adaptive policy switching framework
- Capability override in Hybrid strategy (Phase 6 legacy)
- Deterministic schedule generation for reproducible scenarios

### What doesn't differentiate on this network:
- Batch MIP vs sequential nearest-available (converge to same assignment)
- Mode-specific dispatch logic (produces same results as normal)
- Hospital congestion routing (all hospitals at similar congestion → no rerouting benefit)

### Why:
The 32-node Bangalore network is too sparse for batch optimization to add value. With 14 ambulances across 6 stations, there is always a clearly dominant nearest ambulance for each incident. No resource conflict exists.

---

## Recommendation

**Do not proceed with 5-seed validation yet.** The current results show:
1. Scenario F differentiation is genuine but comes from Phase 6 capability override, not Phase 7 batch dispatch
2. All other scenarios are identical across strategies
3. No statistically significant benefit from batch dispatch or mode switching

**Options before 5-seed validation:**
1. **Accept honest result:** Phase 7 architecture works, but the 32-node network doesn't create conditions where batch dispatch adds value. Report this as a network density limitation.
2. **Increase network density:** Add more nodes/edges to create ambulance competition scenarios where batch MIP would actually differ from greedy.
3. **Increase scenario severity:** More simultaneous incidents with smaller fleets to force genuine resource conflicts.
4. **Differentiate hospital routing:** Make hospitals have significantly different congestion levels so capacity-aware selection actually reroutes patients.
