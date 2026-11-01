from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Configuration from environment variables or backend/.env (see .env.example)."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # Absolute path so the DB location doesn't depend on the working directory.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'expenses.db').as_posix()}"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Supabase Auth. Tokens signed with the project's asymmetric keys are checked
    # against its JWKS; projects still on the legacy shared secret set the secret.
    supabase_url: str | None = None  # https://<project-ref>.supabase.co
    supabase_jwt_secret: str | None = None
    jwt_audience: str = "authenticated"

    @property
    def jwt_issuer(self) -> str | None:
        return f"{self.supabase_url.rstrip('/')}/auth/v1" if self.supabase_url else None


settings = Settings()
