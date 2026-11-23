from datetime import UTC, date, datetime

import pytest

from app.holidays import (
    Holiday,
    HolidayService,
    HolidaysUnavailable,
    holiday_for_window,
    holidays_in_range,
    parse_nager,
)
from app.windows import Window
from tests.fakes import FakeHolidaySource, InMemoryHolidayStore

XMAS = Holiday(date(2026, 12, 25), "Christmas Day", "Weihnachtstag")
NEW_YEAR = Holiday(date(2027, 1, 1), "New Year's Day", "Neujahr")


def utc(month, day, hour=0, minute=0, year=2026):
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


# parse_nager
def test_parse_nager_reads_date_and_names():
    payload = [
        {
            "date": "2026-12-25",
            "localName": "Weihnachtstag",
            "name": "Christmas Day",
            "global": True,
        }
    ]
    assert parse_nager(payload) == [XMAS]


def test_parse_nager_skips_regional_holidays():
    payload = [
        {"date": "2026-03-17", "localName": "Local", "name": "Regional Day", "global": False},
        {
            "date": "2026-12-25",
            "localName": "Weihnachtstag",
            "name": "Christmas Day",
            "global": True,
        },
    ]
    assert [h.name for h in parse_nager(payload)] == ["Christmas Day"]


def test_parse_nager_falls_back_to_the_english_name():
    [holiday] = parse_nager([{"date": "2026-12-25", "name": "Christmas Day"}])
    assert holiday.local_name == "Christmas Day"


def test_parse_nager_skips_malformed_entries_and_sorts_the_rest():
    payload = [
        {"date": "2027-01-01", "name": "B"},
        {"name": "no date"},
        {"date": "not-a-date", "name": "bad date"},
        "not an object",
        {"date": "2026-12-25", "name": "A"},
    ]
    assert [h.name for h in parse_nager(payload)] == ["A", "B"]


@pytest.mark.parametrize("payload", [{"message": "x"}, "text", None, 5])
def test_parse_nager_rejects_a_payload_that_is_not_a_list(payload):
    with pytest.raises(ValueError):
        parse_nager(payload)


# holidays_in_range
def test_range_is_inclusive_at_both_ends():
    found = holidays_in_range([XMAS, NEW_YEAR], date(2026, 12, 25), date(2027, 1, 1))
    assert found == [XMAS, NEW_YEAR]
    assert holidays_in_range([XMAS, NEW_YEAR], date(2026, 12, 26), date(2026, 12, 31)) == []


# holiday_for_window (Seoul is UTC+9, so 25 Dec in Seoul is 24 Dec 15:00 to 25 Dec 15:00 UTC)
def test_window_inside_the_holiday_is_flagged():
    window = Window(utc(12, 24, 20), utc(12, 25, 2))  # Seoul 05:00-11:00 on 25 Dec
    assert holiday_for_window(window, "Asia/Seoul", [XMAS]) == XMAS


def test_window_that_runs_into_the_holiday_is_flagged():
    window = Window(utc(12, 24, 10), utc(12, 24, 20))  # Seoul 19:00 on 24 Dec to 05:00 on 25 Dec
    assert holiday_for_window(window, "Asia/Seoul", [XMAS]) == XMAS


def test_window_ending_exactly_at_midnight_does_not_touch_the_next_day():
    window = Window(utc(12, 24, 10), utc(12, 24, 15))  # ends at Seoul 00:00 on 25 Dec
    assert holiday_for_window(window, "Asia/Seoul", [XMAS]) is None


def test_the_contacts_calendar_decides_not_utc():
    # 25 Dec 20:00-23:00 UTC is already 26 Dec in Seoul, so it is not Christmas there.
    window = Window(utc(12, 25, 20), utc(12, 25, 23))
    assert holiday_for_window(window, "Asia/Seoul", [XMAS]) is None
    assert holiday_for_window(window, "UTC", [XMAS]) == XMAS


def test_no_holidays_means_no_flag():
    assert holiday_for_window(Window(utc(12, 25, 1), utc(12, 25, 5)), "UTC", []) is None


# HolidayService
def test_first_lookup_asks_nager_and_saves_to_the_database():
    source = FakeHolidaySource({("DE", 2026): [XMAS]})
    store = InMemoryHolidayStore()
    service = HolidayService(source, store)
    assert service.for_year("DE", 2026) == [XMAS]
    assert source.calls == [("DE", 2026)]
    assert store.data[("DE", 2026)] == [XMAS]


def test_second_lookup_comes_from_memory():
    source = FakeHolidaySource({("DE", 2026): [XMAS]})
    service = HolidayService(source, InMemoryHolidayStore())
    service.for_year("DE", 2026)
    service.for_year("DE", 2026)
    assert source.calls == [("DE", 2026)]


def test_a_new_process_reads_the_database_instead_of_nager():
    store = InMemoryHolidayStore({("DE", 2026): [XMAS]})
    source = FakeHolidaySource()
    assert HolidayService(source, store).for_year("DE", 2026) == [XMAS]
    assert source.calls == []


def test_a_year_with_no_holidays_is_cached_and_not_refetched():
    store = InMemoryHolidayStore({("XX", 2026): []})  # fetched before, nothing in it
    source = FakeHolidaySource()
    assert HolidayService(source, store).for_year("XX", 2026) == []
    assert source.calls == []


def test_a_broken_database_read_falls_back_to_nager():
    source = FakeHolidaySource({("DE", 2026): [XMAS]})
    service = HolidayService(source, InMemoryHolidayStore(fail_load=True))
    assert service.for_year("DE", 2026) == [XMAS]


def test_a_broken_database_write_does_not_lose_the_result():
    source = FakeHolidaySource({("DE", 2026): [XMAS]})
    service = HolidayService(source, InMemoryHolidayStore(fail_save=True))
    assert service.for_year("DE", 2026) == [XMAS]


def test_the_database_is_asked_only_once_per_missing_year():
    store = InMemoryHolidayStore()
    service = HolidayService(FakeHolidaySource({("DE", 2026): []}), store)
    service.for_year("DE", 2026)
    service.for_year("DE", 2026)
    assert store.loads == [("DE", 2026)]


def test_works_without_a_database():
    service = HolidayService(FakeHolidaySource({("DE", 2026): [XMAS]}), store=None)
    assert service.for_year("DE", 2026) == [XMAS]


def test_nager_down_raises_and_is_not_retried_for_a_minute():
    clock = {"now": 100.0}
    source = FakeHolidaySource(down=True)
    service = HolidayService(source, retry_after_s=60, monotonic=lambda: clock["now"])
    with pytest.raises(HolidaysUnavailable):
        service.for_year("DE", 2026)
    clock["now"] = 130.0  # 30 s later: still inside the minute
    with pytest.raises(HolidaysUnavailable):
        service.for_year("DE", 2026)
    assert len(source.calls) == 1
    clock["now"] = 161.0  # more than a minute later: try again
    source.down = False
    source.data = {("DE", 2026): [XMAS]}
    assert service.for_year("DE", 2026) == [XMAS]
    assert len(source.calls) == 2


def test_lookup_combines_years_and_countries():
    source = FakeHolidaySource({("DE", 2026): [XMAS], ("DE", 2027): [NEW_YEAR], ("KR", 2026): []})
    result = HolidayService(source).lookup(["DE", "KR"], [2026, 2027])
    assert result.available
    assert result.by_country == {"DE": [XMAS, NEW_YEAR], "KR": []}


def test_lookup_reports_unavailable_but_keeps_what_it_has():
    source = FakeHolidaySource({("DE", 2026): [XMAS]})
    service = HolidayService(source)
    service.for_year("DE", 2026)  # DE is now in memory
    source.down = True
    result = service.lookup(["DE", "KR"], [2026])
    assert not result.available
    assert result.by_country == {"DE": [XMAS]}  # KR missing, DE still served


def test_lookup_with_nager_down_pays_for_one_failure_only():
    source = FakeHolidaySource(down=True)
    result = HolidayService(source).lookup(["DE", "KR", "JP"], [2026, 2027])
    assert not result.available
    assert len(source.calls) == 1
