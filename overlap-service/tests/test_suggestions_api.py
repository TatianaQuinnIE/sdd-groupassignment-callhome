from datetime import UTC, datetime, time

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.windows import Person
from tests.fakes import DownContacts, FakeContacts

NOW = datetime(2026, 11, 16, 0, 0, tzinfo=UTC)
USER = Person(tz="Europe/Madrid", sleep_start=time(23, 0), sleep_end=time(7, 0))

MUM = {
    "id": 1,
    "name": "Mum",
    "city": "Seoul",
    "time_zone": "Asia/Seoul",
    "country_code": "KR",
    "sleep_start": "23:00:00",
    "sleep_end": "07:00:00",
    "call_minutes": 30,
    "call_every_days": 7,
    "last_called": None,
}
DAD = {**MUM, "id": 2, "name": "Dad", "last_called": "2026-11-15T00:00:00Z"}


def make_client(contacts):
    settings = Settings(db_host="", run_migrations=False)
    app = create_app(settings, contacts=contacts, clock=lambda: NOW, user=USER)
    return TestClient(app)


def test_suggestions_returns_ranked_contacts_with_windows():
    with make_client(FakeContacts([DAD, MUM])) as client:
        response = client.get("/suggestions?days=1")
    assert response.status_code == 200
    body = response.json()
    assert body["days"] == 1
    assert body["user_time_zone"] == "Europe/Madrid"
    assert [s["name"] for s in body["suggestions"]] == ["Mum", "Dad"]  # never called first
    mum = body["suggestions"][0]
    assert mum["overdue"] == {"days_since": None, "ratio": None, "is_due": True}
    assert mum["windows"] == [
        {"start": "2026-11-16T06:00:00Z", "end": "2026-11-16T14:00:00Z", "minutes": 480}
    ]


def test_default_is_seven_days():
    with make_client(FakeContacts([MUM])) as client:
        body = client.get("/suggestions").json()
    assert body["days"] == 7
    assert len(body["suggestions"][0]["windows"]) == 7


def test_no_contacts_gives_an_empty_list():
    with make_client(FakeContacts([])) as client:
        response = client.get("/suggestions")
    assert response.status_code == 200
    assert response.json()["suggestions"] == []


def test_contacts_service_down_gives_a_clear_503():
    with make_client(DownContacts()) as client:
        response = client.get("/suggestions")
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"]


def test_health_still_works_when_contacts_service_is_down():
    with make_client(DownContacts()) as client:
        assert client.get("/health").status_code == 200


@pytest.mark.parametrize("days", [0, 15, -1, "abc"])
def test_days_must_be_between_1_and_14(days):
    with make_client(FakeContacts([MUM])) as client:
        assert client.get(f"/suggestions?days={days}").status_code == 422