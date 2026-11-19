import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.fakes import DownRepository, InMemoryRepository

MUM = {
    "name": "Mum",
    "city": "Seoul",
    "time_zone": "Asia/Seoul",
    "country_code": "kr",
    "sleep_start": "22:30",
    "sleep_end": "06:30",
    "call_minutes": 45,
    "call_every_days": 7,
}


@pytest.fixture
def client():
    app = create_app(Settings(db_host="", run_migrations=False), repo=InMemoryRepository())
    with TestClient(app) as c:
        yield c


def test_create_returns_201_with_id(client):
    response = client.post("/contacts", json=MUM)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["country_code"] == "KR"  # normalised to upper case
    assert body["sleep_start"] == "22:30:00"


def test_defaults_applied(client):
    body = client.post(
        "/contacts",
        json={
            "name": "Leo",
            "city": "New York",
            "time_zone": "America/New_York",
            "country_code": "US",
        },
    ).json()
    assert body["sleep_start"] == "23:00:00"
    assert body["call_minutes"] == 30
    assert body["call_every_days"] == 7


def test_list_sorted_by_name(client):
    client.post("/contacts", json={**MUM, "name": "Zoe"})
    client.post("/contacts", json={**MUM, "name": "Ana"})
    names = [c["name"] for c in client.get("/contacts").json()]
    assert names == ["Ana", "Zoe"]


def test_get_one(client):
    client.post("/contacts", json=MUM)
    assert client.get("/contacts/1").json()["name"] == "Mum"


def test_update(client):
    client.post("/contacts", json=MUM)
    response = client.put("/contacts/1", json={**MUM, "call_every_days": 3})
    assert response.status_code == 200
    assert response.json()["call_every_days"] == 3


def test_delete(client):
    client.post("/contacts", json=MUM)
    assert client.delete("/contacts/1").status_code == 204
    assert client.get("/contacts/1").status_code == 404


@pytest.mark.parametrize(
    "method,path",
    [("get", "/contacts/99"), ("delete", "/contacts/99"), ("put", "/contacts/99")],
)
def test_missing_contact_is_404(client, method, path):
    kwargs = {"json": MUM} if method == "put" else {}
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 404
    assert response.json() == {"detail": "Contact 99 not found"}


@pytest.mark.parametrize(
    "change",
    [
        {"time_zone": "Mars/Olympus"},
        {"time_zone": ""},
        {"country_code": "KOR"},
        {"name": "   "},
        {"call_minutes": 1},
        {"call_every_days": 0},
        {"sleep_start": "25:00"},
    ],
)
def test_invalid_input_is_422(client, change):
    assert client.post("/contacts", json={**MUM, **change}).status_code == 422


def test_database_down_gives_clear_503():
    app = create_app(Settings(db_host="", run_migrations=False), repo=DownRepository())
    with TestClient(app) as c:
        response = c.get("/contacts")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable, please try again shortly"}
