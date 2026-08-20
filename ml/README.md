# Aureon — ML

Machine learning pipelines, model training, evaluation, and inference.

## Setup

```bash
cd ml
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Optional: PyTorch support
pip install -e ".[torch]"

# Optional: MLflow experiment tracking
pip install -e ".[tracking]"
```

## Structure

```
src/
├── pipelines/       → Data processing and training pipelines
│   └── base.py      → Abstract pipeline interface
├── models/          → Model architectures and definitions
├── training/        → Training scripts and hyperparameter configs
├── evaluation/      → Metrics, validation, and benchmarking
└── inference/       → Inference serving and batch prediction
tests/               → Test suite
```

## Pipeline Usage

All pipelines extend `BasePipeline` and implement a `run()` method:

```python
from src.pipelines.base import BasePipeline

class MyPipeline(BasePipeline):
    def run(self, **kwargs):
        # 1. Load data
        # 2. Preprocess
        # 3. Train / Predict
        # 4. Return results
        ...
```
