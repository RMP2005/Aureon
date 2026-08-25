# Aureon

<p align="center">
  <img
    src="https://readme-typing-svg.demolab.com?font=Space+Mono&weight=600&size=34&duration=2800&pause=1200&color=00D9C0&center=true&vCenter=true&repeat=true&width=1000&height=90&lines=AUREON;URBAN+INTELLIGENCE+OPERATING+SYSTEM"
    alt="AUREON — Urban Intelligence Operating System"
  />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/LIVE_DEMO-Aureon-00d9c0?style=for-the-badge" alt="Live Demo"/>
  <img src="https://img.shields.io/badge/STATUS-LIVE-00d9c0?style=for-the-badge" alt="Status"/>
  <img src="https://img.shields.io/badge/API-HEALTHY-00d9c0?style=for-the-badge" alt="API Health"/>
  <img src="https://img.shields.io/badge/Next.js-15-black?style=for-the-badge&logo=next.js" alt="Next.js"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi" alt="FastAPI"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react" alt="React"/>
  <img src="https://img.shields.io/badge/Three.js-black?style=flat-square&logo=three.js" alt="Three.js"/>
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/NetworkX-3776AB?style=flat-square" alt="NetworkX"/>
  <img src="https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite" alt="SQLite"/>
  <img src="https://img.shields.io/badge/Vercel-black?style=flat-square&logo=vercel" alt="Vercel"/>
  <img src="https://img.shields.io/badge/Render-46E3B7?style=flat-square&logo=render" alt="Render"/>
</p>

<p align="center">
  <strong>A digital twin of Bengaluru with explainable emergency-dispatch intelligence.</strong>
</p>

<p align="center">
  Simulate a living city · Dispatch ambulances · Explain decisions · Replay outcomes
</p>

<p align="center">
  <a href="https://aureon-phi.vercel.app">Live Demo</a>
  ·
  <a href="https://github.com/RMP2005/Aureon">Source Code</a>
  ·
  <a href="https://aureon-vvki.onrender.com/api/v1/health">API Health</a>
</p>

<p align="center">
  <img src="assets/aureon-hero.png" alt="Aureon — Urban Intelligence Operating System" width="900"/>
</p>

<p align="center">
  <img src="assets/aureon-demo.gif" alt="Aureon showcase demo" width="900"/>
</p>

---

## What is Aureon?

Aureon is an experimental **Urban Intelligence Operating System** built around a simulated Bengaluru.

Instead of simply visualizing a city, Aureon simulates one.

Incidents emerge, ambulances move through a road network, hospitals receive patients, and dispatch strategies make allocation decisions under changing conditions.

The core idea is **explainable decision-making**.

Aureon records:

- what decision was made
- why it was made
- which alternatives were considered
- what happened afterwards

> **Simulate the city. Make the decision. Preserve the evidence.**

---

## Why Aureon?

Emergency dispatch is a real-time allocation problem under uncertainty.

A simple system might ask:

> Which ambulance is closest?

But the closest ambulance may be the only available unit protecting another part of the city.

Aureon explores a broader decision space:

```text
Response ETA
      +
Vehicle capability
      +
Fleet coverage
      +
Demand conditions
      ↓
Dispatch Decision
```

The goal is not to claim that one strategy is universally optimal.

The goal is to make the trade-offs **visible, explainable and measurable**.

---

## Experience Aureon

The recommended way to experience the project is:

```text
Landing Page
     ↓
Enter Command Center
     ↓
Start Showcase Demo
     ↓
Watch incidents unfold
     ↓
Inspect Decision Ledger
     ↓
Explain a decision
     ↓
Let the run complete
     ↓
Evidence Replay
     ↓
Mission Debrief
     ↓
Compare strategies
```

### Suggested first run

1. Open the live demo and click **Enter Command Center**
2. Click **Start Showcase Demo**
3. Let the simulation run for a moment
4. Watch incidents appear on the map and incident queue
5. Watch ambulances move through the road network
6. Open the **Decision Ledger**
7. Select **EXPLAIN** on a decision
8. Let the simulation finish
9. Open **Evidence Replay**
10. Explore the **Mission Debrief**
11. Use **COMPARE** to evaluate the dispatch strategy

The showcase uses a curated scenario backed by the actual simulation engine rather than a prerecorded UI animation.

---

## Cold Start & Public Demo Notes

The public frontend is deployed on Vercel while the Python backend currently runs on Render's Free tier.

After inactivity, the backend may temporarily spin down.

When this happens, the frontend may initially show:

```text
BACKEND OFFLINE
CONNECTING
FEED LOST
```

If this happens:

- wait around **1–2 minutes**
- refresh the page once
- reopen the Command Center
- start the showcase again if necessary

Once the backend wakes, the Command Center and showcase should operate normally.

This is a hosting cold-start limitation of the public demo environment, not a failure of the simulation engine.

For production-scale deployment, the backend should run on infrastructure without Free-tier spin-down behaviour and with durable shared storage.

---

## Command Center

<img width="1280" height="727" alt="image" src="https://github.com/user-attachments/assets/fd9bfd58-72d7-48f0-8b84-522ed1a85fd0" />


The Command Center is Aureon's primary operational interface.

It combines:

- **Digital Twin** — live simulated city
- **Incident Queue** — active emergency events
- **Fleet** — ambulance state
- **Hospitals** — facility state
- **Decision Ledger** — dispatch decisions
- **Entity Inspector** — detailed entity information
- **Mission Timeline** — simulation progress

The interface is intentionally designed around mission control rather than a conventional analytics dashboard.

### Digital Twin

The central 3D scene represents the simulated city.

It contains:

- road infrastructure
- ambulances
- hospitals
- stations
- active incidents
- route movement
- operational state

The simulation engine advances the city through discrete steps while the frontend renders the resulting state.

Repeated entities such as vehicles and infrastructure are rendered using GPU-friendly techniques so the scene remains responsive while many entities are active.

---

## Dispatch Intelligence

Aureon supports multiple dispatch strategies so that decisions can be benchmarked rather than judged in isolation.

| Strategy | Purpose |
| --- | --- |
| `NearestAvailableStrategy` | Greedy proximity-based baseline |
| `AdaptiveAureonStrategy` | Assignment with coverage preservation |
| `PredictiveStrategy` | Demand-oriented positioning |
| `HybridAureonStrategy` | Combines multiple decision signals |

The primary showcase strategy is **`HybridAureonStrategy`**.

A decision can incorporate:

```text
Response ETA
Vehicle capability
Coverage preservation
Demand conditions
Alternative candidates
        ↓
Dispatch Decision
```

The system therefore explores decisions beyond simply selecting the nearest available ambulance.

---

## Explainable Decisions

Explainability exists at the decision layer rather than being added only as frontend copy.

A strategy publishes structured information alongside its selected unit:

```python
DispatchDecision(
    ambulance_id="AMB-07",
    rationale="Closest capable unit while preserving west-zone coverage",
    metadata={
        "mode": "hybrid",
        "factors": [
            "coverage_score",
            "eta_delta",
            "capability_match"
        ],
        "alternatives": [...],
        "tradeoff": "Preserves regional coverage"
    }
)
```

The frontend displays the reasoning supplied by the decision engine.

It does not independently invent a justification.

The resulting chain is:

```text
Dispatch Strategy
       ↓
Decision + Rationale
       ↓
Event Journal
       ↓
Backend
       ↓
Decision Ledger
       ↓
Operator Explanation
```

This makes explainability part of the simulation architecture rather than simply a visual feature.

---

## Decision Ledger & Evidence Replay

The Decision Ledger acts as Aureon's operational audit trail.

A decision can expose:

- selected ambulance
- ETA
- capability match
- coverage state
- alternatives
- rejected candidates
- trade-offs
- timestamps
- outcome

### Demo Run

<img width="1280" height="730" alt="image" src="https://github.com/user-attachments/assets/f153124e-368e-4db9-9e75-6aecd23dfd0e" />


Once a run completes, the recorded events become available through the Mission Debrief and Evidence Replay.

### Evidence Replay

<img width="1280" height="731" alt="image" src="https://github.com/user-attachments/assets/c30fa739-5163-47ec-a967-cea0d1fc039d" />


The replay is based on recorded simulation output rather than simply executing the same scenario again.

```text
Live Run
   ↓
Recorded Events
   ↓
Mission Debrief
   ↓
Evidence Replay
```

This lets the operator understand not only the final result, but the sequence of decisions that produced it.

---

## Compare & Custom Scenarios

Aureon includes a comparison surface for evaluating different dispatch strategies.

<img width="1280" height="721" alt="image" src="https://github.com/user-attachments/assets/5e20ffe9-e367-463f-b75e-bbe32f1d3e28" />

The comparison experience can be used to explore differences in:

- response behaviour
- coverage
- capability matching
- incident completion
- strategy decisions

### Custom Scenario Simulator

The Custom Scenario Simulator allows users to create their own emergency scenario rather than relying only on curated presets.

Users can specify:

- incident type
- location
- severity
- traffic/context
- weather/context
- time/context

The simulator then produces a decision-oriented result containing information such as:

- selected ambulance
- expected response time
- recommended hospital
- decision factors
- reasoning behind the assignment

Locations are resolved against Aureon's configured locality and facility data, while free-text locations can also be accepted by the simulator.

The feature demonstrates how the same decision engine responds to changing conditions rather than showing one hard-coded outcome.

---

## Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                         FRONTEND                             │
│                                                              │
│  Landing · Command Center · Compare                          │
│                                                              │
│  Three.js Digital Twin                                       │
│  Incident Queue · Fleet · Hospitals                         │
│  Decision Ledger · Evidence Replay                           │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              │ REST API
                              │ 1 Hz state polling
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                          BACKEND                             │
│                                                              │
│  FastAPI                                                     │
│  Run lifecycle                                               │
│  Scenario library                                            │
│  Demo library                                                │
│  Persistence                                                 │
│  Event recording                                             │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                     SIMULATION ENGINE                        │
│                                                              │
│  Incident generation                                         │
│  Road network                                                 │
│  Ambulance lifecycle                                          │
│  Hospital lifecycle                                           │
│  Dispatch strategies                                          │
│  Event journal                                                │
└──────────────────────────────────────────────────────────────┘
```

### Simulation pipeline

```text
Scenario
   ↓
City Construction
   ↓
Incident Generation
   ↓
Dispatch Decision
   ↓
Ambulance Routing
   ↓
Hospital Assignment
   ↓
Event Recording
   ↓
Frontend State Feed
   ↓
Mission Debrief
```

Seeded scenarios make behaviour reproducible for demonstrations, testing and benchmarking.

---

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 15, React 19 |
| 3D | Three.js, React Three Fiber |
| Animation | GSAP, ScrollTrigger |
| State | Zustand |
| Backend | FastAPI, Uvicorn |
| Simulation | Python |
| Numerical Computing | NumPy, SciPy |
| Graph Algorithms | NetworkX |
| ML | scikit-learn, XGBoost |
| Persistence | SQLite |
| Testing | Pytest |
| Frontend Deployment | Vercel |
| Backend Deployment | Render |

---

## Deployment

Aureon's public deployment is split between frontend and backend:

```text
                    USER
                      │
                      ▼
              ┌──────────────┐
              │    Vercel    │
              │   Next.js    │
              │   Frontend   │
              └──────┬───────┘
                     │
                   REST
                     │
                     ▼
              ┌──────────────┐
              │    Render    │
              │   FastAPI    │
              │  Simulation  │
              │    SQLite    │
              └──────────────┘
```

The frontend receives the backend URL through environment configuration.

Important deployment variables include:

```text
NEXT_PUBLIC_API_URL
NEXT_PUBLIC_WS_URL
CORS_ORIGINS
DEBUG
PORT
```

Production secrets should never be committed to the repository.

---

## Local Development

### Requirements

- Node.js 20+
- Python 3.11+
- `uv`
- Make
- Docker (optional)

### Configure

```bash
cp .env.example .env
```

### Full stack

```bash
make dev
```

Expected services:

```text
Frontend → http://localhost:3000
Backend  → http://localhost:8000
```

### Individual services

```bash
make backend-dev
make frontend-dev
```

### Tests

```bash
cd backend
uv run pytest -q

cd ../simulation
PYTHONPATH=.. uv run pytest -q

cd ../frontend
npm run type-check
npm run build
```

---

## Data, Sources & Scope

Aureon is a simulation and research-oriented prototype.

The city, incidents, fleet behaviour and emergency outcomes are simulated for experimentation and demonstration.

The system should **not** be interpreted as real-world emergency dispatch infrastructure.

### Technology documentation

- Next.js — https://nextjs.org/docs
- React — https://react.dev/
- FastAPI — https://fastapi.tiangolo.com/
- Uvicorn — https://www.uvicorn.org/
- NumPy — https://numpy.org/doc/
- SciPy — https://docs.scipy.org/doc/scipy/
- NetworkX — https://networkx.org/documentation/stable/
- scikit-learn — https://scikit-learn.org/stable/
- XGBoost — https://xgboost.readthedocs.io/
- Three.js — https://threejs.org/docs/
- React Three Fiber — https://r3f.docs.pmnd.rs/
- GSAP — https://gsap.com/docs/
- Zustand — https://zustand.docs.pmnd.rs/
- SQLite — https://www.sqlite.org/docs.html
- Vercel — https://vercel.com/docs
- Render — https://render.com/docs

Where geographic/reference data is derived from OpenStreetMap, attribution is provided in accordance with the applicable OpenStreetMap licence requirements.

### Scope

Aureon explores:

- urban simulation
- resource allocation
- emergency-dispatch decision support
- explainability
- digital twins
- event recording
- strategy benchmarking
- operational interfaces

It is not intended to replace trained emergency operators or provide operational medical or emergency-response instructions.

---

## Limitations

Aureon is currently a showcase and research prototype.

Known limitations include:

- simulated rather than live emergency data
- Render Free-tier cold starts
- SQLite-based persistence
- single-instance backend architecture
- REST polling rather than WebSockets
- limited production-scale concurrency
- deterministic showcase scenarios

These constraints are intentional trade-offs for a lightweight, reproducible research and portfolio environment.

---

## Roadmap

Future directions include:

- live traffic integration
- richer demand prediction
- larger geographic datasets
- real-time WebSocket telemetry
- persistent production database
- multi-instance simulation workers
- larger-scale strategy benchmarking
- experiment tracking
- multi-city simulation
- richer hospital and fleet intelligence
- production authentication
- deeper observability

---
---

## License

This project is licensed under the MIT License.

See the `LICENSE` file for details.

---

<p align="center">
  Built with curiosity, caffeine & a slightly unreasonable love for making cities think.
</p>

<p align="center">
  <strong>Built with ♥ by Mayank</strong>
</p>

<p align="center">
  <sub>
    Aureon is a research-oriented simulation project and is not intended for real-world emergency dispatch.
  </sub>
</p>

<p align="center">
  <strong>Simulate the city. Make the decision. Preserve the evidence.</strong>
</p>

<p align="center">
  Built as an exploration of simulation, AI-assisted decision-making and operational interface design.
</p>
