# Aureon — System Architecture

## Overview

Aureon is a modular platform composed of four primary subsystems that communicate
through well-defined interfaces:

| Subsystem | Technology | Responsibility |
|---|---|---|
| Frontend | Next.js + TypeScript | User interface, visualization, controls |
| Backend | FastAPI + Python | API gateway, orchestration, auth |
| ML | Python + PyTorch/sklearn | Training, evaluation, inference |
| Simulation | Python + NumPy | Digital twin engine, physics, state |

## Communication Patterns

### REST API (synchronous)

Used for all CRUD operations and request-response workflows.

```
Frontend ──HTTP──► Backend ──► ML Inference
                           ──► Simulation Config
```

### WebSocket (real-time)

Used for streaming simulation state and live inference results.

```
Simulation Engine ──state──► Backend ──WS──► Frontend
```

### Internal (in-process / subprocess)

ML and Simulation modules are invoked by the Backend as Python libraries
or subprocesses, not as separate network services (in the initial architecture).

## Data Storage

```
data/
├── raw/          → Source of truth, immutable
├── processed/    → ETL output, reproducible
├── features/     → ML-ready feature matrices
└── snapshots/    → Simulation checkpoints
```

## Future Considerations

- **Message queue**: Add Redis/RabbitMQ for async job dispatch when scale requires it
- **Containerization**: Docker Compose for local dev, Kubernetes for production
- **Database**: Migrate from SQLite to PostgreSQL for production
- **Model serving**: Dedicated inference server (Triton, TorchServe) for GPU workloads
