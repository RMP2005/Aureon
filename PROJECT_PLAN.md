# Aureon — Project Plan

## 1. Project Vision

**Aureon** is an AI-powered digital twin platform that unifies real-time simulation, machine learning inference, and interactive visualization into a single cohesive system.

The platform enables users to:

- Build and run high-fidelity **digital twin simulations** of complex systems
- Train and deploy **ML models** that learn from simulation and real-world data
- Interact with simulations through a modern **web-based dashboard**
- Close the loop between simulation output, AI predictions, and human decision-making

Aureon is designed from the ground up for **modularity**, **scalability**, and **developer ergonomics** — every subsystem communicates through well-defined APIs and data contracts.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                 │
│         Dashboard · Visualization · Controls            │
└────────────────────────┬────────────────────────────────┘
                         │  REST / WebSocket
┌────────────────────────▼────────────────────────────────┐
│                    Backend (FastAPI)                     │
│       API Gateway · Auth · Orchestration · Events       │
├──────────────┬──────────────────────┬───────────────────┤
│              │                      │                   │
│   ┌──────────▼──────────┐  ┌───────▼────────────┐      │
│   │   ML Pipeline Layer │  │  Simulation Engine  │      │
│   │  Training · Serving │  │  Physics · Stepping │      │
│   └──────────┬──────────┘  └───────┬────────────┘      │
│              │                      │                   │
│   ┌──────────▼──────────────────────▼───────────┐      │
│   │              Data Layer                      │      │
│   │    Raw · Processed · Feature Store           │      │
│   └─────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Frontend framework | Next.js 14 + TypeScript | SSR, file-based routing, strong typing |
| API layer | FastAPI (Python) | Async, auto-docs, native Pydantic validation |
| ML framework | PyTorch / scikit-learn | Ecosystem maturity, GPU support |
| Simulation runtime | Custom Python engine | Full control over physics step, state, and I/O |
| Inter-service comms | REST + WebSocket | REST for CRUD, WebSocket for real-time streams |
| Data serialization | JSON + Parquet | JSON for API, Parquet for columnar analytics |

---

## 3. Folder Responsibilities

```
Aureon/
├── frontend/          → Next.js web application
├── backend/           → FastAPI REST/WebSocket server
├── ml/                → Machine learning pipelines & models
├── simulation/        → Digital twin simulation engine
├── data/              → Raw and processed datasets
├── docs/              → Architecture docs, ADRs, guides
└── PROJECT_PLAN.md    → This file
```

### `frontend/`
The user-facing web application. Responsible for:
- Dashboard views and data visualization (charts, 3D renderers)
- Simulation controls (start, stop, configure)
- ML model monitoring and result display
- Authentication and user management UI

### `backend/`
The central API server. Responsible for:
- REST API endpoints for all CRUD operations
- WebSocket endpoints for real-time simulation streaming
- Request validation, authentication, and authorization
- Orchestrating calls to ML and simulation subsystems
- Background task management (Celery / built-in task queue)

### `ml/`
Machine learning subsystem. Responsible for:
- Data preprocessing and feature engineering pipelines
- Model training scripts and hyperparameter tuning
- Model evaluation, versioning, and registry
- Inference serving (batch and real-time)

### `simulation/`
Digital twin simulation engine. Responsible for:
- Core simulation loop (time-stepping, state management)
- Physics and domain-specific models
- Scenario configuration and parametric sweeps
- State snapshots and replay

### `data/`
Centralized data storage. Responsible for:
- `raw/` — Immutable ingested data (sensor feeds, external sources)
- `processed/` — Cleaned, transformed, analysis-ready datasets
- `features/` — Engineered feature sets for ML consumption
- `snapshots/` — Simulation state checkpoints

### `docs/`
Project documentation. Responsible for:
- Architecture Decision Records (ADRs)
- API specifications and data contracts
- Developer onboarding guides
- Runbooks and operational playbooks

---

## 4. Data Flow

### 4.1 Ingestion → Processing → Storage

```
External Sources ──► data/raw/
                        │
                   ETL Pipeline
                        │
                        ▼
                   data/processed/
                        │
                  Feature Engineering
                        │
                        ▼
                   data/features/
```

### 4.2 Simulation Loop

```
Configuration ──► Simulation Engine
                        │
                   Step N (physics, state update)
                        │
                  ┌──────┴──────┐
                  ▼              ▼
           State Snapshot    WebSocket Stream
          (data/snapshots/)   (→ Frontend)
```

### 4.3 ML Training & Inference

```
data/features/ ──► Training Pipeline ──► Model Registry
                                              │
                                         Inference API
                                              │
Backend Request ──► ML Serving ──► Prediction Response
```

### 4.4 End-to-End Request Flow

```
User Action (Frontend)
    │
    ▼
API Request → Backend (FastAPI)
    │
    ├──► ML Inference  ──► Prediction
    ├──► Simulation    ──► State Update
    │
    ▼
API Response → Frontend (render)
```

---

## 5. AI Pipeline

### 5.1 Pipeline Stages

| Stage | Description | Tools |
|---|---|---|
| **Data Ingestion** | Collect raw data from sensors, APIs, simulations | Python scripts, connectors |
| **Preprocessing** | Clean, normalize, handle missing values | pandas, NumPy |
| **Feature Engineering** | Create derived features, embeddings | scikit-learn, custom transforms |
| **Training** | Train models with experiment tracking | PyTorch, MLflow |
| **Evaluation** | Metrics, validation, bias checks | scikit-learn metrics, custom |
| **Registry** | Version and store trained models | MLflow Model Registry |
| **Serving** | Expose models via API for inference | FastAPI, ONNX Runtime |
| **Monitoring** | Track drift, latency, accuracy in production | Prometheus, custom dashboards |

### 5.2 Model Lifecycle

```
Experiment → Train → Evaluate → Register → Deploy → Monitor → Retrain
                                                         │
                                                    Drift Detection
                                                         │
                                                    ◄────┘
```

### 5.3 Supported Model Types (Planned)

- **Predictive models** — Time-series forecasting, regression
- **Anomaly detection** — Unsupervised outlier detection on sensor/sim data
- **Reinforcement learning** — Agents trained inside the simulation environment
- **Surrogate models** — Fast ML approximations of expensive simulation runs

---

## 6. Frontend Experience Plan

### 6.1 Core Views

| View | Purpose |
|---|---|
| **Dashboard** | High-level KPIs, system health, recent activity |
| **Simulation Control** | Configure, launch, pause, and replay simulations |
| **Simulation Viewer** | Real-time 2D/3D visualization of simulation state |
| **ML Studio** | View training runs, compare models, inspect predictions |
| **Data Explorer** | Browse datasets, preview features, check quality |
| **Settings** | User preferences, API keys, system configuration |

### 6.2 Design Principles

- **Real-time first** — WebSocket-driven live updates for simulation and inference
- **Progressive disclosure** — Simple defaults, advanced controls on demand
- **Responsive layout** — Usable on desktop and tablet
- **Dark mode default** — Optimized for long working sessions
- **Accessible** — WCAG 2.1 AA compliance target

### 6.3 Tech Stack Details

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS
- **State management**: React Context + SWR for server state
- **Charts**: Recharts / D3.js
- **3D rendering**: Three.js / React Three Fiber (when needed)
- **Testing**: Jest + React Testing Library

---

## 7. Development Phases

### Phase 0 — Foundation (Current)
- [x] Define project structure and folder layout
- [x] Write PROJECT_PLAN.md
- [ ] Initialize all sub-project scaffolds (package.json, pyproject.toml, etc.)
- [ ] Set up linting, formatting, and editor config
- [ ] Create development environment documentation

### Phase 1 — Core API & Data Layer
- [ ] Implement FastAPI skeleton with health check and CORS
- [ ] Define core Pydantic models and database schemas
- [ ] Set up data ingestion pipeline (`data/raw/` → `data/processed/`)
- [ ] Create initial API endpoints (CRUD for entities)
- [ ] Add authentication scaffolding (JWT)

### Phase 2 — Simulation Engine MVP
- [ ] Build core simulation loop (initialize → step → snapshot)
- [ ] Implement basic physics/domain model
- [ ] Add scenario configuration via YAML/JSON
- [ ] Stream simulation state over WebSocket
- [ ] Write simulation unit and integration tests

### Phase 3 — ML Pipeline MVP
- [ ] Build preprocessing and feature engineering pipeline
- [ ] Train first baseline model on simulation data
- [ ] Set up experiment tracking (MLflow)
- [ ] Expose inference endpoint through backend
- [ ] Implement model versioning and registry

### Phase 4 — Frontend MVP
- [ ] Build dashboard layout with navigation
- [ ] Implement simulation control panel
- [ ] Add real-time simulation viewer (2D)
- [ ] Create ML model monitoring view
- [ ] Connect all views to backend API

### Phase 5 — Integration & Hardening
- [ ] End-to-end integration tests
- [ ] Performance profiling and optimization
- [ ] Security audit (auth, input validation, CORS)
- [ ] CI/CD pipeline setup
- [ ] Monitoring and alerting (logging, metrics)

### Phase 6 — Advanced Features
- [ ] 3D simulation visualization
- [ ] Reinforcement learning agent integration
- [ ] Surrogate model training from simulation runs
- [ ] Multi-user collaboration features
- [ ] Production deployment and scaling

---

## Appendix: Conventions

| Area | Convention |
|---|---|
| Branch naming | `feature/`, `fix/`, `chore/` prefixes |
| Commit messages | Conventional Commits (`feat:`, `fix:`, `docs:`) |
| Python style | Black + Ruff, type hints everywhere |
| TypeScript style | ESLint + Prettier, strict mode |
| API versioning | URL prefix (`/api/v1/`) |
| Environment config | `.env` files, never committed |
