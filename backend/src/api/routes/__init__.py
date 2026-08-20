"""API route definitions."""

from fastapi import APIRouter

from src.api.routes.health import router as health_router
from src.api.routes.ml import router as ml_router
from src.api.routes.simulation import router as simulation_router

router = APIRouter()
router.include_router(health_router)
router.include_router(simulation_router)
router.include_router(ml_router)
