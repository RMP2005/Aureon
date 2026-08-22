"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


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

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

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
