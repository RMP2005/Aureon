# Aureon — Urban Intelligence Operating System

Aureon is a **digital twin of a living city** with **explainable emergency-dispatch
intelligence** built in. A simulated Bengaluru breathes in real time — incidents
spark, ambulances move over the road network, hospitals absorb patients — while
an AI dispatch strategy makes every allocation decision and *shows its work*.

The reference point is mission control, not a dashboard: NASA-grade restraint,
Gotham-grade operational density, terminal-grade information legibility.

> **Live demo path:** open the landing page → *Enter Command Center* →
> *Start Showcase Demo*. In under two minutes you will watch an incident unfold,
> watch Aureon dispatch against it, open the decision's evidence, and replay the
> mission debrief — all from real simulation output. No mock data anywhere.

---

## 1. What is Aureon?

Aureon couples three systems into one product:

| Layer | What it does |
|---|---|
| **Simulation engine** (`simulation/`) | A discrete-time city engine: incident generation, road-network routing (NetworkX/SciPy), ambulance & hospital lifecycles, scenario scripting |
| **Intelligence layer** (`simulation/src/dispatch/`) | Dispatch strategies that decide *which ambulance* and *which hospital* respond to each incident — with published rationale for every decision |
| **Operations frontend** (`frontend/`) | A Next.js command center: live 3D twin, decision ledger, mission debrief, evidence replay, baseline comparison |

The backend (`backend/`) binds them: FastAPI owns run lifecycle, persistence,
and streaming state to the frontend.

## 2. Problem statement

Emergency dispatch is a real-time allocation problem under uncertainty:

- Incidents arrive stochastically; fleets are finite and unevenly positioned.
- Choosing the *nearest* unit greedily can strip coverage from the next crisis.
- Human operators have seconds — not minutes — to weigh trade-offs.
- After the fact, cities rarely can answer *"why was this unit sent?"*

Most "smart city" dashboards visualize. They don't **decide**, and they
don't **explain**. Aureon does both, on the record.

## 3. Product vision

An **Urban Intelligence Operating System**: the city is the process, Aureon is
the kernel. The product principles:

1. **Observed, not predicted.** The UI renders only what the engine actually
   did. Decision panels quote the engine's own rationale verbatim.
2. **Evidence over claims.** Every run is event-recorded; any moment can be
   replayed frame-accurately as proof.
3. **Operator wins.** Camera automation (intro sweeps, guided debrief) yields
   instantly to human input.
4. **Legibility contract.** Color carries meaning: teal = operational state,
   violet = AI reasoning only, red = true critical events, titanium =
   infrastructure. Nothing glows without a reason.

## 4. Architecture overview

```
┌─────────────────────────────  frontend (Next.js)  ─────────────────────────┐
│  Landing (cinematic scroll)   Command Center (/command)   Compare / Analytics│
│  ├── three.js digital twin    ├── Mission bar · sim clock                  │
│  │   instanced fleet/city     ├── Incident queue · Fleet · Hospitals       │
│  ├── GSAP act choreography    ├── Decision Ledger → Explain panel           │
│  └── reduced-motion fallback  ├── Mission Debrief + Evidence Replay         │
│                               └── 1s poll feed w/ STALE / FEED LOST states  │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ REST (envelope: {status,data,error}) · 1 Hz poll
┌───────────────────────────────┴──────────────────────────────────────────────┐
│                        backend (FastAPI + Uvicorn)                            │
│  routes/simulation.py ─ run CRUD · scenarios · demos · recordings             │
│  services/ ─ SimulationService (background runs) · RunStore (SQLite WAL)      │
│              RunRecorder (event journal) · ScenarioLibrary · DemoLibrary      │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ in-process engine threads
┌───────────────────────────────┴──────────────────────────────────────────────┐
│                     simulation engine (pure Python package)                   │
│  CitySimulationEngine ─ tick loop · incident generator · road network         │
│  Dispatch strategies ─ HybridAureon (default) · Adaptive · Baseline           │
│  Every strategy returns DispatchDecision(rationale, metadata=…)               │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Why this shape?** The engine is dependency-free and deterministic, so it can
run identically inside backend threads, tests, or benchmarks. The backend adds
only lifecycle and persistence — never business logic. The frontend stays a
pure consumer of recorded facts.

## 5. Digital twin pipeline

1. **World construction** — `CitySimulationEngine` builds the road graph,
   hospital set, and ambulance fleet from scenario parameters (fixed seed).
2. **Tick loop** — each `step()` advances sim time: new incidents are drawn
   from a seeded stochastic process, units move along real road-network
   shortest paths, hospital capacity absorbs patients.
3. **Live feed** — the backend samples engine state at `wall_clock_factor`
   pacing and exposes `/state` snapshots; the frontend polls at 1 Hz.
4. **Twin rendering** — React never re-renders per tick. Ambulances, stations,
   and hospitals are `InstancedMesh`es driven from transient buffers inside
   `useFrame`; React state carries only selection and low-frequency UI.
5. **Recording** — a `RunRecorder` journals frames + events (INCIDENT /
   DISPATCH / ADMISSION / RESOLVED with incident linkage and measured response
   times) into SQLite, compressed.

**Why instancing?** Hundreds of vehicles must animate at 60 FPS. Per-entity
React components would thrash reconciliation; instanced meshes update matrices
on the GPU timeline instead.

## 6. AI dispatch intelligence

Every strategy implements one interface — `dispatch(incident, fleet, hospitals)`
→ `DispatchDecision` — so intelligence is **swappable and benchmarkable**:

| Strategy | Idea |
|---|---|
| `NearestAvailableStrategy` | Greedy baseline: closest capable unit |
| `AdaptiveAureonStrategy` | Batch assignment + coverage preservation |
| `PredictiveStrategy` | Demand-model-aware positioning |
| `HybridAureonStrategy` (**default**) | Coverage score + predictive demand + optimization pass, arbitrated per incident |

**Why hybrid?** Single-signal strategies fail predictably: greedy nearest
erodes coverage; pure optimization is slow under load. The hybrid arbitrates
cheap heuristics first and spends optimization only when candidates conflict.
The baseline strategies remain first-class so every improvement is measurable
against them (`/compare`).

## 7. Explainability system

Explainability is a **contract at the strategy interface**, not a UI garnish:

```python
DispatchDecision(
    ambulance_id="AMB-07",
    rationale="Closest capable unit … Coverage: west zone thinning",
    metadata={            # published by the strategy itself
        "mode": "hybrid",
        "factors": ["coverage_score", "eta_delta", "capability_match"],
        "alternatives": [{"id": "AMB-12", "rejected_reason": "…"}, …],
        "tradeoff": "…",
    },
)
```

- The **Decision Ledger** logs each committed decision with mode stamps.
- **Explain This Decision** renders *only* engine-published fields — the UI
  cannot invent a justification it wasn't given. Live decisions honestly show
  `[ EVIDENCE AT DEBRIEF ]` until the run completes.
- The **Mission Debrief** reconstructs each incident as a chapter
  (reported → dispatched → closed) from the recorder journal, with measured
  response times — answering *what happened, why, and with what outcome* in
  one screen.

## 8. Demo walkthrough (2–3 minutes)

Curated showcases live server-side (`DemoLibrary`) and launch as **real,
deterministic engine runs** — fixed seed, named scenario, auto-paced:

1. Open the landing page and click **Enter Command Center**
   (the camera sweeps down from the hero framing into operations).
2. Click **▶ Start Showcase Demo** — e.g. *Mass Casualty Response*
   (a `◈ SHOWCASE` chip marks curated runs).
3. Watch incidents appear on the twin and in the queue; decisions stream into
   the **Decision Ledger**.
4. Click **EXPLAIN** on any ledger row — rationale, factors, trade-offs,
   rejected alternatives.
5. When the run ends, click **▶ Evidence Replay**, then step through the
   **Mission Debrief** chapters (toggle **GUIDED** to let the camera follow).
6. Click **COMPARE →** to measure Aureon against the baseline strategy.

From source, the same path works headless:

```bash
cd backend && uv run uvicorn src.main:app --reload
curl -s localhost:8000/api/v1/simulation/demos | jq
curl -s -X POST localhost:8000/api/v1/simulation/demos/default/launch | jq
```

Screenshots for press/portfolio should be captured from this exact path:
landing hero, command center mid-demo, decision explain panel, debrief chapters.

## 9. Technical stack

| Component | Technology | Why |
|---|---|---|
| Simulation | Python 3.11+, NumPy, SciPy, NetworkX | Deterministic numerics; graph routing on real road topology |
| ML (optional) | scikit-learn, XGBoost | Demand prediction & clustering behind feature flags |
| Backend | FastAPI, Uvicorn | Async API with typed envelopes; background run threads |
| Persistence | SQLite (WAL mode), zero ORM | Single-file ops simplicity, safe concurrent reads, trivial backups |
| Frontend | Next.js 15, React 19 | App router, server-safe shells around client instruments |
| 3D | three.js via @react-three/fiber | Declarative scene graph, imperative performance escape hatches |
| Motion | GSAP + ScrollTrigger | Scrubbed cinematic acts tied to scroll position |
| State | Zustand | Minimal stores where React re-render cost is acceptable |

## 10. Setup instructions

Prerequisites: Node.js 20+, Python 3.11+ ([uv](https://docs.astral.sh/uv/) recommended), Make.

```bash
# 1. Configure
cp .env.example .env

# 2. Full stack via Docker
make dev            # frontend :3000 · backend :8000
make dev-down

# — or run pieces locally —
make backend-dev    # FastAPI on :8000
make frontend-dev   # Next.js on :3000

# 3. Tests
(cd backend && uv run pytest -q)                    # API/persistence suite
(cd simulation && PYTHONPATH=.. uv run pytest -q)   # engine suite
(cd frontend && npm run type-check && npm run build)
```

### Key engineering decisions (and why)

- **Determinism first.** Seeded generators mean identical inputs reproduce
  identical worlds — prerequisites for evidence, demos, and regression tests.
- **SQLite over Postgres (for now).** Aureon is a showcase-grade system;
  single-file storage keeps setup friction near zero. WAL mode gives the
  concurrent read pattern the 1 Hz poll needs. The store interface isolates
  this choice for a future swap.
- **Polling over websockets.** A 1 Hz envelope poll keeps the client simple,
  survives proxy timeouts, and powers honest feed-health semantics
  (STALE at 2.5 s, FEED LOST at 6 s) derived from actual poll age.
- **Event recording over re-simulation.** Debrief/replay read what happened,
  they don't recompute it — evidence must be immutable.
- **UI renders engine words.** All explanation copy originates in strategy
  metadata; the frontend is forbidden from synthesizing justifications.
- **Motion budgets.** One hero gesture per arrival (intro sweep, act fades);
  everything else respects `prefers-reduced-motion`.

Further docs: [Architecture](docs/architecture.md) ·
[API Contracts](docs/api-contracts.md) · [Docs Home](docs/README.md)
