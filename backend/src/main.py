"""Aureon Backend — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.routes import router as api_router
from src.core.config import settings
from src.core.logging import setup_logging
from src.core.rate_limit import RateLimitMiddleware

logger: logging.Logger | None = None


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — startup and shutdown."""
    global logger
    logger = setup_logging(debug=settings.DEBUG)
    logger.info("%s v%s starting", settings.PROJECT_NAME, settings.VERSION)
    logger.info("API prefix: %s", settings.API_V1_PREFIX)
    yield
    if logger:
        logger.info("%s shutting down", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)
