from datetime import UTC, date, datetime, time

from app.holidays import Holiday
from app.suggestions import build_suggestions
from app.windows import Person

NOW = datetime(2026, 11, 16, 0, 0, tzinfo=UTC)  # a Monday
# The user sleeps 22:00-06:00 UTC (Madrid, winter) and has no classes in these tests.
USER = Person(tz="Europe/Madrid", sleep_start=time(23, 0), sleep_end=time(7, 0))


def contact(contact_id, **overrides):
    base = {
        "id": contact_id,
        "name": f"Contact {contact_id}",
        "city": "Seoul",
        "time_zone": "Asia/Seoul",
        "country_code": "KR",
        "sleep_start": "23:00:00",  # contacts-service sends HH:MM:SS
        "sleep_end": "07:00:00",
        "call_minutes": 30,
        "call_every_days": 7,
        "last_called": None,
    }
    return {**base, **overrides}


def ids(suggestions):
    return [s.contact_id for s in suggestions]


def test_empty_contact_list():
    assert build_suggestions([], NOW, 7, USER) == []


def test_windows_are_computed_for_a_contact():
    # Madrid sleeps 22:00-06:00 UTC, Seoul sleeps 14:00-22:00 UTC, so 06:00-14:00 UTC is free.
    result = build_suggestions([contact(1)], NOW, 1, USER)
    assert len(result) == 1
    assert [(w.start.hour, w.end.hour) for w in result[0].windows] == [(6, 14)]
    assert result[0].name == "Contact 1"
    assert result[0].country_code == "KR"


def test_never_called_contacts_come_first_then_by_how_overdue():
    contacts = [
        contact(1, last_called="2026-11-14T00:00:00Z"),  # 2 days ago, every 7: not due
        contact(2, last_called="2026-11-01T00:00:00Z"),  # 15 days ago, every 7: very overdue
        contact(3, last_called=None),  # never called
    ]
    assert ids(build_suggestions(contacts, NOW, 7, USER)) == [3, 2, 1]


def test_overdue_details_are_passed_through():
    [suggestion] = build_suggestions(
        [contact(1, last_called="2026-11-09T00:00:00+00:00")], NOW, 1, USER
    )
    assert suggestion.overdue.days_since == 7.0
    assert suggestion.overdue.is_due


def test_last_called_without_a_zone_is_read_as_utc():
    [suggestion] = build_suggestions([contact(1, last_called="2026-11-09T00:00:00")], NOW, 1, USER)
    assert suggestion.overdue.days_since == 7.0


def test_preferred_hours_are_used_when_present():
    # Seoul 18:00-22:00 is 09:00-13:00 UTC.
    preferred = contact(1, preferred_start="18:00:00", preferred_end="22:00:00")
    [suggestion] = build_suggestions([preferred], NOW, 1, USER)
    assert [(w.start.hour, w.end.hour) for w in suggestion.windows] == [(9, 13)]


def test_missing_preferred_hours_mean_no_restriction():
    nulls = contact(1, preferred_start=None, preferred_end=None)
    [suggestion] = build_suggestions([nulls], NOW, 1, USER)
    assert [(w.start.hour, w.end.hour) for w in suggestion.windows] == [(6, 14)]


def test_a_contact_with_no_overlap_is_still_listed_with_no_windows():
    # Sleeps 00:00-12:00 and 12:00-00:00 in UTC leave no shared time with this user either.
    round_the_clock = contact(
        1, time_zone="UTC", sleep_start="06:00:00", sleep_end="22:00:00", call_minutes=240
    )
    [suggestion] = build_suggestions([round_the_clock], NOW, 1, USER)
    assert suggestion.windows == []


def test_unusable_contacts_are_skipped_not_fatal():
    contacts = [
        contact(1),
        contact(2, time_zone="Mars/Olympus"),  # unknown time zone
        {"id": 3, "name": "Broken"},  # missing fields
        contact(4, call_every_days="often"),  # wrong type
    ]
    assert ids(build_suggestions(contacts, NOW, 7, USER)) == [1]


def test_a_contact_missing_a_display_field_is_skipped_not_fatal():
    # name and city are only needed for the response, but a missing one must not crash the page.
    without_name = {k: v for k, v in contact(2).items() if k != "name"}
    without_country = {k: v for k, v in contact(3).items() if k != "country_code"}
    assert ids(build_suggestions([contact(1), without_name, without_country], NOW, 7, USER)) == [1]


KR_HOLIDAYS = [
    Holiday(date(2026, 11, 16), "Today", "오늘"),
    Holiday(date(2026, 11, 20), "Later this week", "이번 주"),
    Holiday(date(2026, 12, 25), "Too far away", "먼 미래"),
]


def test_holidays_in_the_period_are_attached_to_the_contact():
    [suggestion] = build_suggestions([contact(1)], NOW, 7, USER, {"KR": KR_HOLIDAYS})
    assert [h.name for h in suggestion.holidays] == ["Today", "Later this week"]


def test_holidays_are_matched_by_country_code_in_any_case():
    lower = contact(1, country_code="kr")
    [suggestion] = build_suggestions([lower], NOW, 7, USER, {"KR": KR_HOLIDAYS})
    assert suggestion.country_code == "KR"
    assert len(suggestion.holidays) == 2


def test_other_countries_holidays_are_not_attached():
    [suggestion] = build_suggestions([contact(1)], NOW, 7, USER, {"DE": KR_HOLIDAYS})
    assert suggestion.holidays == []


def test_without_holiday_data_contacts_have_no_holidays():
    [suggestion] = build_suggestions([contact(1)], NOW, 7, USER)
    assert suggestion.holidays == []


def test_the_period_is_measured_in_the_contacts_calendar():
    # The period runs from 16 Nov 20:00 UTC to 21 Nov 20:00 UTC. In Seoul (UTC+9) that is
    # 17 Nov 05:00 to 22 Nov 05:00, so Seoul's 16th is outside it and Seoul's 22nd is inside,
    # which is the opposite of what the UTC dates would say.
    start = datetime(2026, 11, 16, 20, 0, tzinfo=UTC)
    holidays = [
        Holiday(date(2026, 11, 16), "Seoul 16th", "x"),
        Holiday(date(2026, 11, 22), "Seoul 22nd", "x"),
    ]
    [suggestion] = build_suggestions([contact(1)], start, 5, USER, {"KR": holidays})
    assert [h.name for h in suggestion.holidays] == ["Seoul 22nd"]
