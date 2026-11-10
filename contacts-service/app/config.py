"""Settings read only from environment variables (no secrets in code)."""

import os
from dataclasses import dataclass, field


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    db_host: str = field(default_factory=lambda: os.getenv("DB_HOST", ""))
    db_port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "1433")))
    db_name: str = field(default_factory=lambda: os.getenv("DB_NAME", "contacts"))
    db_user: str = field(default_factory=lambda: os.getenv("DB_USER", ""))
    db_password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", ""))
    cors_origins: list[str] = field(
        default_factory=lambda: _split(os.getenv("CORS_ORIGINS", "http://localhost:8080"))
    )
    run_migrations: bool = field(
        default_factory=lambda: os.getenv("RUN_MIGRATIONS", "true").lower() == "true"
    )

    @property
    def db_configured(self) -> bool:
        return bool(self.db_host and self.db_user and self.db_password)
