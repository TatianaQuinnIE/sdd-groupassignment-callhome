import logging

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_one_log_line_per_request(caplog):
    client = TestClient(create_app(Settings(db_host="", run_migrations=False)))
    with caplog.at_level(logging.INFO, logger="contacts.requests"):
        client.get("/health")
        client.get("/does-not-exist")
    lines = [r.getMessage() for r in caplog.records if r.name == "contacts.requests"]
    assert len(lines) == 2
    assert lines[0].startswith("method=GET path=/health status=200 duration_ms=")
    assert "path=/does-not-exist status=404" in lines[1]
