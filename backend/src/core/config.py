"""Application configuration loaded from environment variables."""

import json
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode


class Settings(BaseSettings):
    """Global application settings."""

    # Application
    PROJECT_NAME: str = "Aureon"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS — fully environment driven for production deployments.
    # NoDecode: the raw env string is handed to the validator below, which
    # accepts every platform spelling (JSON array / comma list / single).
    CORS_ORIGINS: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: object) -> object:
        """Accept every deployment-platform spelling of the origin list.

        Platforms differ in what they can express in an env var:
          - JSON array      -> '["https://app.example.com"]'
          - comma-separated -> 'https://app.example.com,https://www.example.com'
          - single origin   -> 'https://app.example.com'
        All forms normalize to a clean list (whitespace stripped, trailing
        slashes removed so origin matching is exact per the Fetch spec).
        """
        if isinstance(v, str):
            text = v.strip()
            if not text:
                return []
            if text.startswith("["):
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    return [str(o).strip().rstrip("/") for o in parsed]
            return [o.strip().rstrip("/") for o in text.split(",") if o.strip()]
        if isinstance(v, list):
            return [str(o).strip().rstrip("/") for o in v]
        return v

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./aureon.db"

    # Simulation
    SIMULATION_TICK_RATE: float = 0.1
    SIMULATION_MAX_STEPS: int = 10000

    # Resource protection
    RATE_LIMIT_MAX_REQUESTS: int = 30
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    MAX_STORED_RUNS: int = 100

    # ML
    ML_MODEL_DIR: str = "./models"
    ML_DEFAULT_CONFIDENCE_THRESHOLD: float = 0.7

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
