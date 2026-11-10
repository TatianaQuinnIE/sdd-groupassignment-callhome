import os
from dataclasses import dataclass, field


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    db_host: str = field(default_factory=lambda: os.getenv("DB_HOST", ""))
    db_port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "1433")))
    db_name: str = field(default_factory=lambda: os.getenv("DB_NAME", "overlap"))
    db_user: str = field(default_factory=lambda: os.getenv("DB_USER", ""))
    db_password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", ""))
    cors_origins: list[str] = field(
        default_factory=lambda: _split(os.getenv("CORS_ORIGINS", "http://localhost:8080"))
    )
    run_migrations: bool = field(
        default_factory=lambda: os.getenv("RUN_MIGRATIONS", "true").lower() == "true"
    )
    contacts_service_url: str = field(
        default_factory=lambda: os.getenv("CONTACTS_SERVICE_URL", "http://contacts-service:8000")
    )
    contacts_timeout_s: float = field(
        default_factory=lambda: float(os.getenv("CONTACTS_TIMEOUT_S", "3"))
    )
    nager_base_url: str = field(
        default_factory=lambda: os.getenv("NAGER_BASE_URL", "https://date.nager.at/api/v3")
    )
    nager_timeout_s: float = field(
        default_factory=lambda: float(os.getenv("NAGER_TIMEOUT_S", "3"))
    )

    @property
    def db_configured(self) -> bool:
        return bool(self.db_host and self.db_user and self.db_password)
