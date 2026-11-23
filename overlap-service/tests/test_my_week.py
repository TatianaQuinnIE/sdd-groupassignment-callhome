from datetime import UTC, datetime, time

import pymssql
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.holidays import HolidayService
from app.main import create_app
from app.schedule import (
    DatabaseUnavailable,
    InMemoryScheduleRepository,
    SqlScheduleRepository,
    describe,
    find_overlap,
    to_person,
)
from app.windows import BusyBlock, Person
from tests.fakes import FakeContacts, FakeHolidaySource

NOW = datetime(2026, 11, 16, 0, 0, tzinfo=UTC)  # a Monday
USER = Person(
    tz="Europe/Madrid",
    sleep_start=time(23, 0),
    sleep_end=time(7, 0),
    busy=(BusyBlock(weekday=1, start=time(9, 0), end=time(11, 0)),),  # Tuesday 9-11
)
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
BLOCK = {"weekday": 0, "start": time(9, 0), "end": time(11, 0), "label": "Class"}


def make_client():
    settings = Settings(db_host="", run_migrations=False)
    app = create_app(
        settings,
        contacts=FakeContacts([MUM]),
        clock=lambda: NOW,
        user=USER,
        holidays=HolidayService(FakeHolidaySource()),
    )
    return TestClient(app)


# --- the overlap rule ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("start", "end", "clashes"),
    [
        (time(10, 0), time(12, 0), True),  # overlaps the end
        (time(8, 0), time(9, 30), True),  # overlaps the start
        (time(9, 30), time(10, 0), True),  # inside
        (time(8, 0), time(12, 0), True),  # around
        (time(11, 0), time(12, 0), False),  # touches the end
        (time(8, 0), time(9, 0), False),  # touches the start
    ],
)
def test_find_overlap_on_the_same_day(start, end, clashes):
    assert (find_overlap([BLOCK], 0, start, end) is not None) is clashes


def test_find_overlap_ignores_other_days():
    assert find_overlap([BLOCK], 1, time(9, 0), time(11, 0)) is None


def test_describe_with_and_without_label():
    assert describe(BLOCK) == "Mon 09:00-11:00 (Class)"
    assert describe({**BLOCK, "label": None}) == "Mon 09:00-11:00"


def test_to_person_builds_busy_blocks():
    person = to_person(
        {"time_zone": "Europe/Madrid", "sleep_start": time(23), "sleep_end": time(7)}, [BLOCK]
    )
    assert person.busy == (BusyBlock(0, time(9), time(11)),)


# --- the API ------------------------------------------------------------------------


def test_get_my_week_starts_from_the_user():
    with make_client() as client:
        body = client.get("/me").json()
    assert body["time_zone"] == "Europe/Madrid"
    assert body["sleep_start"] == "23:00:00"
    assert body["busy"] == [
        {"id": 1, "weekday": 1, "start": "09:00:00", "end": "11:00:00", "label": None}
    ]


def test_update_settings():
    with make_client() as client:
        response = client.put(
            "/me", json={"time_zone": "Asia/Tokyo", "sleep_start": "22:30", "sleep_end": "06:30"}
        )
        assert response.status_code == 200
        assert client.get("/me").json()["time_zone"] == "Asia/Tokyo"
        assert client.get("/suggestions").json()["user_time_zone"] == "Asia/Tokyo"


def test_update_settings_rejects_unknown_time_zone():
    with make_client() as client:
        response = client.put(
            "/me", json={"time_zone": "Mars/Olympus", "sleep_start": "23:00", "sleep_end": "07:00"}
        )
    assert response.status_code == 422


def test_add_and_delete_a_busy_block():
    with make_client() as client:
        response = client.post(
            "/me/busy", json={"weekday": 0, "start": "18:00", "end": "19:30", "label": " Gym "}
        )
        assert response.status_code == 201
        block = response.json()
        assert block["label"] == "Gym"
        assert client.delete(f"/me/busy/{block['id']}").status_code == 204
        assert client.delete(f"/me/busy/{block['id']}").status_code == 404


def test_overlapping_block_is_refused_with_a_clear_message():
    with make_client() as client:
        response = client.post("/me/busy", json={"weekday": 1, "start": "10:00", "end": "12:00"})
    assert response.status_code == 409
    assert response.json()["detail"].startswith("This overlaps Tue 09:00-11:00")


@pytest.mark.parametrize(
    "body",
    [
        {"weekday": 0, "start": "11:00", "end": "10:00"},  # ends before it starts
        {"weekday": 0, "start": "10:00", "end": "10:00"},  # empty
        {"weekday": 7, "start": "10:00", "end": "11:00"},  # no such day
    ],
)
def test_invalid_blocks_are_rejected(body):
    with make_client() as client:
        assert client.post("/me/busy", json=body).status_code == 422


def test_a_new_busy_block_changes_the_suggested_windows():
    with make_client() as client:
        before = client.get("/suggestions?days=1").json()["suggestions"][0]["windows"]
        # Monday 16 Nov: Mum's window is 06:00-14:00 UTC = 07:00-15:00 in Madrid.
        assert before == [
            {
                "start": "2026-11-16T06:00:00Z",
                "end": "2026-11-16T14:00:00Z",
                "minutes": 480,
                "holiday": None,
            }
        ]
        client.post("/me/busy", json={"weekday": 0, "start": "10:00", "end": "12:00"})
        after = client.get("/suggestions?days=1").json()["suggestions"][0]["windows"]
    assert after == [
        {
            "start": "2026-11-16T06:00:00Z",
            "end": "2026-11-16T09:00:00Z",
            "minutes": 180,
            "holiday": None,
        },
        {
            "start": "2026-11-16T11:00:00Z",
            "end": "2026-11-16T14:00:00Z",
            "minutes": 180,
            "holiday": None,
        },
    ]


def test_database_down_gives_a_clear_503():
    settings = Settings(db_host="", run_migrations=False)
    app = create_app(
        settings,
        contacts=FakeContacts([MUM]),
        clock=lambda: NOW,
        user=USER,
        holidays=HolidayService(FakeHolidaySource()),
    )
    app.state.schedule = SqlScheduleRepository(_refuse_connection)
    with TestClient(app) as client:
        response = client.get("/me")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable, please try again shortly"}


# --- storage ------------------------------------------------------------------------


def test_in_memory_repository_keeps_blocks_sorted():
    repo = InMemoryScheduleRepository(USER)
    repo.add_block({"weekday": 0, "start": time(18), "end": time(19), "label": None})
    assert [b["weekday"] for b in repo.list_blocks()] == [0, 1]


def _refuse_connection():
    raise pymssql.OperationalError("database is resuming")


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.executed = []
        self.rowcount = 1

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.rows[0]

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.cursor_ = FakeCursor(rows)
        self.committed = False
        self.closed = False

    def cursor(self, as_dict=False):
        return self.cursor_

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def test_sql_repository_reads_times_returned_as_text():
    conn = FakeConnection(
        [{"time_zone": "Europe/Madrid", "sleep_start": "23:00:00.0000000", "sleep_end": "07:00:00"}]
    )
    settings = SqlScheduleRepository(lambda: conn).get_settings()
    assert settings == {"time_zone": "Europe/Madrid", "sleep_start": time(23), "sleep_end": time(7)}
    assert conn.closed


def test_sql_repository_lists_blocks():
    conn = FakeConnection(
        [{"id": 3, "weekday": 0, "start_time": time(9), "end_time": "11:00:00", "label": "Class"}]
    )
    blocks = SqlScheduleRepository(lambda: conn).list_blocks()
    assert blocks == [{"id": 3, "weekday": 0, "start": time(9), "end": time(11), "label": "Class"}]


def test_sql_repository_add_update_and_delete():
    conn = FakeConnection(
        [{"id": 7, "time_zone": "UTC", "sleep_start": time(1), "sleep_end": time(2)}]
    )
    repo = SqlScheduleRepository(lambda: conn)
    assert repo.add_block(BLOCK) == {"id": 7, **BLOCK}
    repo.update_settings({"time_zone": "UTC", "sleep_start": time(1), "sleep_end": time(2)})
    assert repo.delete_block(7) is True
    assert conn.committed
    sql = " ".join(s for s, _ in conn.cursor_.executed)
    assert "OUTPUT INSERTED.id" in sql and "UPDATE my_settings" in sql and "DELETE FROM" in sql


def test_sql_repository_raises_database_unavailable():
    with pytest.raises(DatabaseUnavailable):
        SqlScheduleRepository(_refuse_connection).list_blocks()
