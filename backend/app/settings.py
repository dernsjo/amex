from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Configuration from environment variables or backend/.env (see .env.example)."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # Absolute path so the DB location doesn't depend on the working directory.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'expenses.db').as_posix()}"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
