from datetime import UTC, date, datetime, time

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.holidays import Holiday, HolidayService
from app.main import create_app
from app.windows import Person
from tests.fakes import DownContacts, FakeContacts, FakeHolidaySource

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


def make_client(contacts, holiday_source=None):
    # Always inject a holiday source: tests must never call the real Nager.Date.
    holidays = HolidayService(holiday_source or FakeHolidaySource())
    settings = Settings(db_host="", run_migrations=False)
    app = create_app(settings, contacts=contacts, clock=lambda: NOW, user=USER, holidays=holidays)
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
        {
            "start": "2026-11-16T06:00:00Z",
            "end": "2026-11-16T14:00:00Z",
            "minutes": 480,
            "holiday": None,
        }
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


# 17 Nov is a Tuesday. Mum is in Seoul, where the window that day is 06:00-14:00 UTC.
KR_HOLIDAY = Holiday(date(2026, 11, 17), "Test Holiday", "테스트 휴일")


def test_holidays_flag_the_window_on_that_day_and_list_on_the_contact():
    source = FakeHolidaySource({("KR", 2026): [KR_HOLIDAY]})
    with make_client(FakeContacts([MUM]), source) as client:
        body = client.get("/suggestions?days=3").json()
    assert body["holidays_available"] is True
    mum = body["suggestions"][0]
    assert mum["holidays"] == [
        {"date": "2026-11-17", "name": "Test Holiday", "local_name": "테스트 휴일"}
    ]
    flagged = {w["start"][:10]: w["holiday"] for w in mum["windows"]}
    assert flagged["2026-11-17"] == {
        "date": "2026-11-17",
        "name": "Test Holiday",
        "local_name": "테스트 휴일",
    }
    assert flagged["2026-11-16"] is None
    assert flagged["2026-11-18"] is None


def test_nager_down_still_returns_windows_without_flags():
    with make_client(FakeContacts([MUM]), FakeHolidaySource(down=True)) as client:
        response = client.get("/suggestions?days=3")
    assert response.status_code == 200
    body = response.json()
    assert body["holidays_available"] is False
    mum = body["suggestions"][0]
    assert len(mum["windows"]) == 3
    assert mum["holidays"] == []
    assert all(w["holiday"] is None for w in mum["windows"])


def test_nager_is_asked_once_per_country_and_year_across_contacts_and_requests():
    source = FakeHolidaySource({("KR", 2026): []})
    with make_client(FakeContacts([MUM, DAD]), source) as client:
        client.get("/suggestions")
        client.get("/suggestions")
    assert source.calls == [("KR", 2026)]


def test_the_period_crossing_new_year_asks_for_both_years():
    source = FakeHolidaySource()
    settings = Settings(db_host="", run_migrations=False)
    late_december = datetime(2026, 12, 28, tzinfo=UTC)
    app = create_app(
        settings,
        contacts=FakeContacts([MUM]),
        clock=lambda: late_december,
        user=USER,
        holidays=HolidayService(source),
    )
    with TestClient(app) as client:
        client.get("/suggestions?days=7")
    assert sorted(source.calls) == [("KR", 2026), ("KR", 2027)]


def test_contacts_down_is_still_a_503_even_with_working_holidays():
    source = FakeHolidaySource({("KR", 2026): [KR_HOLIDAY]})
    with make_client(DownContacts(), source) as client:
        assert client.get("/suggestions").status_code == 503
