"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global application settings.

    Values are loaded from environment variables or a .env file.
    """

    PROJECT_NAME: str = "Aureon"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Database (placeholder)
    DATABASE_URL: str = "sqlite+aiosqlite:///./aureon.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
