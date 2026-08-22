#!/usr/bin/env python3
"""1-seed smoke validation for Phase 7 scenarios."""
import json
import sys
import time

sys.path.insert(0, "simulation/src")

from simulation.src.evaluation.phase7_scenarios import (
    ALL_SCENARIOS, ScenarioConfig, run_scenario_single,
    summarize_results,
)
from simulation.src.dispatch.baseline import NearestAvailableStrategy
from simulation.src.dispatch.hybrid_intelligence import HybridAureonStrategy, HybridDispatchConfig
from simulation.src.dispatch.adaptive_policy import AdaptiveAureonStrategy

SEED = 42
results_all = {}

for letter, configs in ALL_SCENARIOS.items():
    config = list(configs.values())[0]
    config.seed = SEED
    print(f"\n=== Scenario {letter}: {config.name} ({config.description}) ===")
    print(f"    Fleet={config.fleet_size}, Duration={config.duration_minutes}min")

    results = {"Baseline": [], "Hybrid Aureon": [], "Adaptive Aureon": []}

    for label, strategy in [
        ("Baseline", NearestAvailableStrategy()),
        ("Hybrid Aureon", HybridAureonStrategy(
            config=HybridDispatchConfig(enable_coverage_analysis=True))),
        ("Adaptive Aureon", AdaptiveAureonStrategy()),
    ]:
        t0 = time.time()
        r = run_scenario_single(config, strategy, SEED)
        elapsed = time.time() - t0
        results[label].append(r)

        m = r.metrics
        ms = r.mode_stats or {}
        print(f"  {label:20s}: RT={m.mean_response_time_sec/60:.2f}m "
              f"P90={m.p90_response_time_sec/60:.2f}m "
              f"Cap={m.capability_match_rate*100:.0f}% "
              f"Hosp={m.mean_hospital_suitability:.3f} "
              f"Svc={m.total_incidents_dispatched}/{m.total_incidents_reported} "
              f"Unsv={m.unserviced_incidents_count} "
              f"Batch={ms.get('batch_dispatches',0)} "
              f"Modes={ms.get('mode_counts',{})} "
              f"({elapsed:.1f}s)")

    summary = summarize_results(results)
    results_all[letter] = {"config": config.name, "summary": summary}

with open("PHASE7_SMOKE_V1.json", "w") as f:
    json.dump(results_all, f, indent=2, default=str)

print("\n\n=== SUMMARY TABLE ===")
print(f"{'Scen':<6} {'Strategy':<20} {'RT':>6} {'P90':>6} {'Crit':>6} {'Cap':>5} {'Hosp':>5} {'Svc':>5} {'Unsv':>4} {'Batch':>5}")
for letter, data in results_all.items():
    for strat, vals in data["summary"].items():
        print(f"{letter:<6} {strat:<20} "
              f"{vals['mean_response_time_min']:>6.2f} "
              f"{vals['p90_response_time_min']:>6.2f} "
              f"{vals['critical_mean_rt_min']:>6.2f} "
              f"{vals['capability_match_pct']:>5.1f} "
              f"{vals['hospital_suitability']:>5.3f} "
              f"{vals['dispatched_incidents']:>5.1f} "
              f"{vals['unserviced']:>4.1f} "
              f"{vals.get('batch_dispatches',0):>5}")

print("\n=== DIFFERENTIATION ANALYSIS ===")
for letter, data in results_all.items():
    summ = data["summary"]
    base_rt = summ.get("Baseline", {}).get("mean_response_time_min", 0)
    adapt_rt = summ.get("Adaptive Aureon", {}).get("mean_response_time_min", 0)
    diff_pct = ((adapt_rt - base_rt) / base_rt * 100) if base_rt > 0 else 0
    batch = summ.get("Adaptive Aureon", {}).get("batch_dispatches", 0)
    modes = summ.get("Adaptive Aureon", {}).get("mode_counts", {})
    verdict = "IDENTICAL" if abs(diff_pct) < 0.5 else (
        f"ADAPTIVE {'BETTER' if diff_pct < 0 else 'WORSE'} by {abs(diff_pct):.1f}%"
    )
    print(f"  {letter} {data['config']:<25s}: {verdict:<30s} batch={batch} modes={modes}")
