from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-secret-change-me-before-deploying"  # noqa: S105 - rejected outside dev


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VI_", env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite:///./data/vendor_intake.db"
    storage_dir: Path = Path("./data/uploads")
    jwt_secret: str = DEV_JWT_SECRET
    jwt_ttl_minutes: int = 480
    max_upload_bytes: int = 10 * 1024 * 1024
    # Simulated extraction latency so the UI exercises its polling path.
    extraction_delay_seconds: float = 1.0
    cookie_secure: bool = False

    @model_validator(mode="after")
    def _require_real_secret_outside_dev(self) -> "Settings":
        if self.environment != "development" and self.jwt_secret == DEV_JWT_SECRET:
            raise ValueError("VI_JWT_SECRET must be set outside development")
        return self

    def prepare_paths(self) -> None:
        """Create the upload directory and, for a SQLite file database, its parent directory."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix) and not self.database_url.endswith(":memory:"):
            Path(self.database_url.removeprefix(prefix)).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
