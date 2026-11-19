from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.fakes import InMemoryRepository

MUM = {"name": "Mum", "city": "Seoul", "time_zone": "Asia/Seoul", "country_code": "KR"}


@pytest.fixture
def client():
    app = create_app(Settings(db_host="", run_migrations=False), repo=InMemoryRepository())
    with TestClient(app) as c:
        c.post("/contacts", json=MUM)
        yield c


def test_new_contact_was_never_called(client):
    assert client.get("/contacts/1").json()["last_called"] is None


def test_log_call_defaults_to_now(client):
    response = client.post("/contacts/1/calls", json={"minutes": 40, "note": "Weekly catch-up"})
    assert response.status_code == 201
    called = datetime.fromisoformat(response.json()["called_at"])
    assert datetime.now(UTC) - called < timedelta(minutes=1)


def test_last_called_is_most_recent_call(client):
    client.post("/contacts/1/calls", json={"called_at": "2026-11-10T19:00:00Z"})
    client.post("/contacts/1/calls", json={"called_at": "2026-11-15T19:00:00Z"})
    client.post("/contacts/1/calls", json={"called_at": "2026-11-12T19:00:00Z"})
    contact = client.get("/contacts/1").json()
    assert contact["last_called"].startswith("2026-11-15T19:00:00")
    listed = client.get("/contacts").json()[0]
    assert listed["last_called"] == contact["last_called"]


def test_times_are_stored_in_utc(client):
    body = client.post("/contacts/1/calls", json={"called_at": "2026-11-16T09:00:00+09:00"}).json()
    assert body["called_at"].startswith("2026-11-16T00:00:00")


def test_list_calls_newest_first(client):
    client.post("/contacts/1/calls", json={"called_at": "2026-11-10T19:00:00Z"})
    client.post("/contacts/1/calls", json={"called_at": "2026-11-15T19:00:00Z"})
    days = [c["called_at"][:10] for c in client.get("/contacts/1/calls").json()]
    assert days == ["2026-11-15", "2026-11-10"]


def test_delete_call(client):
    call = client.post("/contacts/1/calls", json={}).json()
    assert client.delete(f"/contacts/1/calls/{call['id']}").status_code == 204
    assert client.get("/contacts/1/calls").json() == []
    assert client.delete(f"/contacts/1/calls/{call['id']}").status_code == 404


def test_deleting_contact_removes_its_calls(client):
    client.post("/contacts/1/calls", json={})
    client.delete("/contacts/1")
    assert client.get("/contacts/1/calls").status_code == 404


def test_calls_for_missing_contact_are_404(client):
    assert client.get("/contacts/99/calls").status_code == 404
    assert client.post("/contacts/99/calls", json={}).status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"called_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()},
        {"minutes": 0},
        {"note": "x" * 501},
    ],
)
def test_invalid_call_is_422(client, body):
    assert client.post("/contacts/1/calls", json=body).status_code == 422
