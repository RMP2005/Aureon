"""ML model inference endpoints.

Currently, ML models exist only within the simulation engine (XGBoost demand
forecasting in simulation/src/ml/). They are trained inline during benchmark
runs and never persisted. The endpoints below reflect the actual state:

  - Dispatch strategies (hybrid, adaptive) are served through /simulation/run
  - XGBoost demand forecasting is available inside simulation benchmarks
  - No standalone ML inference server is implemented yet
"""

from fastapi import APIRouter

from src.models.schemas import (
    PredictionRequest,
    ResponseEnvelope,
)

router = APIRouter(prefix="/models", tags=["ml"])


@router.get("", response_model=ResponseEnvelope)
async def list_models() -> ResponseEnvelope:
    """List available ML models and their actual implementation status."""
    models = [
        {
            "id": "demand-forecast",
            "name": "Demand Forecast (XGBoost)",
            "status": "implemented_in_simulation",
            "note": "Trained inline during benchmark runs; not persisted or served standalone",
        },
        {
            "id": "hybrid-dispatch",
            "name": "Hybrid Dispatch Strategy",
            "status": "served",
            "note": "Available via POST /simulation/run?strategy=hybrid",
        },
        {
            "id": "adaptive-policy",
            "name": "Adaptive Policy Engine",
            "status": "served",
            "note": "Available via POST /simulation/run?strategy=adaptive",
        },
        {
            "id": "event-classifier",
            "name": "Event Classifier",
            "status": "not_implemented",
            "note": "Abstract interface only; no trained model exists",
        },
        {
            "id": "optimizer",
            "name": "Response Optimizer",
            "status": "not_implemented",
            "note": "RL scaffolding exists in simulation; no trained policy",
        },
    ]
    return ResponseEnvelope(data=models)


@router.post("/predict", response_model=ResponseEnvelope)
async def predict(request: PredictionRequest) -> ResponseEnvelope:
    """Run inference on a loaded model.

    Currently returns a clear message that standalone ML inference
    is not yet implemented. Use the simulation endpoints for dispatch
    strategy comparisons.
    """
    return ResponseEnvelope(
        data={
            "model_id": request.model_id,
            "prediction": None,
            "confidence": None,
            "message": (
                "Standalone ML inference not yet implemented. "
                "Use POST /simulation/run for dispatch strategy evaluation. "
                "The XGBoost demand forecast model is available within "
                "simulation benchmark runs (simulation/src/ml/)."
            ),
        }
    )


@router.get("/{model_id}", response_model=ResponseEnvelope)
async def get_model(model_id: str) -> ResponseEnvelope:
    """Get model metadata and implementation status."""
    models = {
        "demand-forecast": {
            "id": "demand-forecast",
            "status": "implemented_in_simulation",
            "location": "simulation/src/ml/demand_model.py",
        },
        "hybrid-dispatch": {
            "id": "hybrid-dispatch",
            "status": "served",
            "endpoint": "POST /simulation/run?strategy=hybrid",
        },
        "adaptive-policy": {
            "id": "adaptive-policy",
            "status": "served",
            "endpoint": "POST /simulation/run?strategy=adaptive",
        },
    }
    info = models.get(model_id)
    if not info:
        return ResponseEnvelope(
            data={"id": model_id, "status": "not_found", "message": f"Unknown model: {model_id}"}
        )
    return ResponseEnvelope(data=info)
