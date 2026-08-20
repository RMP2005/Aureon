# Aureon

Aureon is an AI-powered urban digital twin platform. It features a Next.js frontend, a FastAPI backend, Python-based machine learning models, and an advanced urban simulation engine.

## Tech Stack

| Component | Technology |
|---|---|
| **Frontend** | Next.js 14, React, Tailwind CSS |
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **Machine Learning** | Python, scikit-learn, PyTorch |
| **Simulation** | Python, custom digital twin engine |
| **Deployment** | Docker, Docker Compose |

## Prerequisites

- **Node.js** 20+
- **Python** 3.11+
- **Docker** & **Docker Compose**
- **Make** (optional, but recommended)

## Quick Start (Docker)

The easiest way to run the entire Aureon stack is using Docker Compose via the provided Makefile.

1. **Configure Environment**
   ```bash
   cp .env.example .env
   ```

2. **Start the Stack**
   ```bash
   make dev
   ```
   This will build the Docker images and start the frontend on `http://localhost:3000` and the backend on `http://localhost:8000`.

3. **Stop the Stack**
   ```bash
   make dev-down
   ```

## Local Development (Without Docker)

You can also run components individually using Make targets:

- **Frontend**: `make frontend-dev`
- **Backend**: `make backend-dev`
- **Testing**: `make test` (runs all tests)
- **Linting**: `make lint` (runs all linters)

Check `make help` for all available commands.

## Documentation

- [Docs Home](docs/README.md)
- [Architecture](docs/architecture.md)
- [API Contracts](docs/api-contracts.md)
- [Project Plan](PROJECT_PLAN.md)
