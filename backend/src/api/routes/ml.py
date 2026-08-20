"""ML model inference endpoints."""

from fastapi import APIRouter

from src.models.schemas import (
    PredictionRequest,
    ResponseEnvelope,
)

router = APIRouter(prefix="/models", tags=["ml"])


@router.get("", response_model=ResponseEnvelope)
async def list_models() -> ResponseEnvelope:
    """List available ML models."""
    models = [
        {"id": "event-classifier", "name": "Event Classifier", "status": "not_loaded"},
        {"id": "predictor", "name": "Prediction Engine", "status": "not_loaded"},
        {"id": "optimizer", "name": "Response Optimizer", "status": "not_loaded"},
    ]
    return ResponseEnvelope(data=models)


@router.post("/predict", response_model=ResponseEnvelope)
async def predict(request: PredictionRequest) -> ResponseEnvelope:
    """Run inference on a loaded model."""
    # Placeholder — will integrate with ML pipeline
    return ResponseEnvelope(
        data={
            "model_id": request.model_id,
            "prediction": None,
            "confidence": None,
            "message": "Model inference not yet implemented",
        }
    )


@router.get("/{model_id}", response_model=ResponseEnvelope)
async def get_model(model_id: str) -> ResponseEnvelope:
    """Get model metadata."""
    return ResponseEnvelope(
        data={
            "id": model_id,
            "status": "not_loaded",
            "version": None,
        }
    )
