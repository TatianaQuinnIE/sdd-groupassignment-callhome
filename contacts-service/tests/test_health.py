from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def make_client(**overrides):
    settings = Settings(db_host="", run_migrations=False, **overrides)
    return TestClient(create_app(settings))


def test_health_returns_ok():
    with make_client() as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "contacts-service"}


def test_cors_allows_configured_origin_only():
    with make_client(cors_origins=["https://ui.example"]) as client:
        allowed = client.get("/health", headers={"Origin": "https://ui.example"})
        blocked = client.get("/health", headers={"Origin": "https://evil.example"})
    assert allowed.headers.get("access-control-allow-origin") == "https://ui.example"
    assert "access-control-allow-origin" not in blocked.headers


def test_settings_read_from_environment(monkeypatch):
    monkeypatch.setenv("DB_HOST", "db")
    monkeypatch.setenv("DB_USER", "sa")
    monkeypatch.setenv("DB_PASSWORD", "x")
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example, https://b.example")
    monkeypatch.setenv("RUN_MIGRATIONS", "false")
    settings = Settings()
    assert settings.db_configured
    assert settings.cors_origins == ["https://a.example", "https://b.example"]
    assert settings.run_migrations is False
