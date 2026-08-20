# Aureon — Simulation

Digital twin simulation engine with time-stepping, state management, and scenario configuration.

## Setup

```bash
cd simulation
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Structure

```
src/
├── engine/
│   ├── __init__.py
│   └── core.py       → BaseEngine ABC, SimulationState dataclass
├── models/            → Domain-specific physics models
└── scenarios/         → Scenario configs (YAML) and loaders
tests/                 → Test suite
```

## Engine Usage

All simulation engines extend `BaseEngine`:

```python
from src.engine.core import BaseEngine, SimulationState
import copy

class MyEngine(BaseEngine):
    def step(self) -> SimulationState:
        self.state.tick += 1
        self.state.time += self.dt
        # Update domain-specific state...
        return copy.deepcopy(self.state)

engine = MyEngine(dt=0.01)
history = engine.run(steps=1000)
```
