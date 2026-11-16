from datetime import UTC, datetime, time

import pytest

from app.windows import BusyBlock, Person, Window, find_windows


def utc(month, day, hour=0, minute=0, year=2026):
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def person(tz, sleep=("23:00", "07:00"), busy=(), preferred=None):
    sleep_start, sleep_end = (time.fromisoformat(value) for value in sleep)
    if preferred:
        pref_start, pref_end = (time.fromisoformat(value) for value in preferred)
    else:
        pref_start = pref_end = None

    return Person(
        tz=tz,
        sleep_start=sleep_start,
        sleep_end=sleep_end,
        busy=tuple(busy),
        preferred_start=pref_start,
        preferred_end=pref_end,
    )


def spans(windows):
    return [(window.start, window.end) for window in windows]


# What if one person is in Madird and wants to find a time window with someone from Seoul
def test_basic_window_for_madrid_and_seoul():
    windows = find_windows(person("Europe/Madrid"), person("Asia/Seoul"), 30, utc(11, 16), 1)
    assert spans(windows) == [(utc(11, 16, 6), utc(11, 16, 14))]
    assert windows[0].minutes == 480


def test_window_can_be_converted_to_local_time():
    window = find_windows(person("Europe/Madrid"), person("Asia/Seoul"), 30, utc(11, 16), 1)[0]
    madrid_start, madrid_end = window.in_zone("Europe/Madrid")
    seoul_start, seoul_end = window.in_zone("Asia/Seoul")
    assert (madrid_start.hour, madrid_end.hour) == (7, 15)
    assert (seoul_start.hour, seoul_end.hour) == (15, 23)


# Test when they have added a busy block or do not disturb
def test_busy_block_removes_that_time():
    monday_busy = BusyBlock(weekday=0, start=time(9, 0), end=time(11, 0))
    user = person("Europe/Madrid", busy=[monday_busy])
    windows = find_windows(user, person("Asia/Seoul"), 30, utc(11, 16), 1)
    assert spans(windows) == [
        (utc(11, 16, 6), utc(11, 16, 8)),
        (utc(11, 16, 10), utc(11, 16, 14)),
    ]


def test_window_that_crosses_midnight_is_kept_as_one_window():
    windows = find_windows(person("Asia/Seoul"), person("America/Los_Angeles"), 30, utc(11, 16), 2)
    assert (utc(11, 16, 22), utc(11, 17, 7)) in spans(windows)


def test_short_windows_are_removed():
    monday_busy = BusyBlock(weekday=0, start=time(9, 0), end=time(11, 0))
    user = person("Europe/Madrid", busy=[monday_busy])
    windows = find_windows(user, person("Asia/Seoul"), 180, utc(11, 16), 1)
    assert spans(windows) == [(utc(11, 16, 10), utc(11, 16, 14))]


def test_preferred_hours_limit_the_window():
    contact = person("Asia/Seoul", preferred=("18:00", "22:00"))
    windows = find_windows(person("Europe/Madrid"), contact, 30, utc(11, 16), 1)
    assert spans(windows) == [(utc(11, 16, 9), utc(11, 16, 13))]


def test_preferred_hours_can_cross_midnight():
    contact = person("Asia/Seoul", preferred=("22:00", "02:00"))
    windows = find_windows(person("Europe/Madrid"), contact, 30, utc(11, 16), 1)
    assert spans(windows) == [(utc(11, 16, 13), utc(11, 16, 14))]


def test_window_is_cut_at_now():
    windows = find_windows(person("Europe/Madrid"), person("Asia/Seoul"), 30, utc(11, 16, 8), 1)
    assert windows[0].start == utc(11, 16, 8)
    assert windows[0].end == utc(11, 16, 14)


# The daylight saving changed at a different day in madrid and in new york
def test_daylight_saving_changes_the_window_start():
    madrid, new_york = person("Europe/Madrid"), person("America/New_York")
    before = find_windows(madrid, new_york, 30, utc(10, 28), 1)
    after = find_windows(madrid, new_york, 30, utc(11, 3), 1)
    assert spans(before) == [(utc(10, 28, 11), utc(10, 28, 22))]
    assert spans(after) == [(utc(11, 3, 12), utc(11, 3, 22))]


def test_invalid_inputs_are_rejected():
    with pytest.raises(ValueError, match="unknown time zone"):
        find_windows(person("Mars/Olympus"), person("UTC"), 30, utc(11, 16), 1)

    with pytest.raises(ValueError, match="timezone-aware"):
        find_windows(person("UTC"), person("UTC"), 30, datetime(2026, 11, 16), 1)

    with pytest.raises(ValueError):
        find_windows(person("UTC"), person("UTC"), 0, utc(11, 16), 7)


def test_window_value_object():
    assert Window(utc(11, 16, 6), utc(11, 16, 7)) == Window(utc(11, 16, 6), utc(11, 16, 7))


def test_one_preferred_time_is_rejected():
    with pytest.raises(ValueError, match="both preferred_start and preferred_end"):
        Person("UTC", time(23, 0), time(7, 0), preferred_start=time(18, 0))
