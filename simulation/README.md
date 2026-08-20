# Aureon Simulation

Aureon is an AI-powered urban intelligence platform — a digital twin of a city for emergency response and resource optimization.

## Structure
- `src/engine/`: Core simulation engine and time-stepping logic.
- `src/models/`: Production-grade Pydantic models for city state, environment, and emergency events.
- `src/scenarios/`: Default configurations and scenario generation.
- `tests/`: Unit tests.

## Setup
Install dependencies with:
```bash
pip install -e ".[dev]"
```

Run tests with:
```bash
pytest
```
