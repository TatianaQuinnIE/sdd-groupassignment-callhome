from datetime import date, datetime

import pytest

from app.holiday_cache import SqlHolidayCache
from app.holidays import Holiday

XMAS = Holiday(date(2026, 12, 25), "Christmas Day", "Weihnachtstag")


class FakeCursor:
    def __init__(self, status_row=None, holiday_rows=()):
        self.status_row = status_row
        self.holiday_rows = list(holiday_rows)
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self.status_row

    def fetchall(self):
        return self.holiday_rows


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.commits = 0
        self.closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


def cache_with(cursor):
    conn = FakeConn(cursor)
    return SqlHolidayCache(lambda: conn), conn


def test_load_returns_none_when_the_year_was_never_fetched():
    cache, conn = cache_with(FakeCursor(status_row=None))
    assert cache.load("DE", 2026) is None
    assert conn.closed


def test_load_returns_holidays_with_names_in_the_right_order():
    rows = [(date(2026, 12, 25), "Weihnachtstag", "Christmas Day")]  # date, local_name, name
    cache, _ = cache_with(FakeCursor(status_row=(1,), holiday_rows=rows))
    assert cache.load("DE", 2026) == [XMAS]


def test_load_returns_an_empty_list_for_a_fetched_year_with_no_holidays():
    cache, _ = cache_with(FakeCursor(status_row=(1,), holiday_rows=[]))
    assert cache.load("XX", 2026) == []


def test_load_accepts_datetimes_and_strings_from_the_driver():
    rows = [
        (datetime(2026, 12, 25, 0, 0), "Weihnachtstag", "Christmas Day"),
        ("2026-12-26", "Zweiter", "Second Day"),
    ]
    cache, _ = cache_with(FakeCursor(status_row=(1,), holiday_rows=rows))
    assert [h.date for h in cache.load("DE", 2026)] == [date(2026, 12, 25), date(2026, 12, 26)]


def test_save_replaces_the_year_in_the_right_order_and_commits():
    cursor = FakeCursor()
    cache, conn = cache_with(cursor)
    cache.save("DE", 2026, [XMAS])
    statements = [sql.split(" (")[0].split(" WHERE")[0] for sql, _ in cursor.executed]
    # Children before the status row they point at on delete, status row before children on insert.
    assert statements == [
        "DELETE FROM holiday_cache",
        "DELETE FROM holiday_cache_status",
        "INSERT INTO holiday_cache_status",
        "INSERT INTO holiday_cache",
    ]
    assert cursor.executed[-1][1] == ("DE", 2026, "2026-12-25", "Weihnachtstag", "Christmas Day")
    assert conn.commits == 1 and conn.closed


def test_save_with_no_holidays_still_records_the_year():
    cursor = FakeCursor()
    cache, _ = cache_with(cursor)
    cache.save("XX", 2026, [])
    assert any(sql.startswith("INSERT INTO holiday_cache_status") for sql, _ in cursor.executed)
    assert not any(sql.startswith("INSERT INTO holiday_cache ") for sql, _ in cursor.executed)


def test_save_skips_duplicates_that_would_break_the_unique_key():
    cursor = FakeCursor()
    cache, _ = cache_with(cursor)
    cache.save("DE", 2026, [XMAS, XMAS])
    inserts = [sql for sql, _ in cursor.executed if sql.startswith("INSERT INTO holiday_cache ")]
    assert len(inserts) == 1


def test_connection_is_closed_and_error_propagates_when_a_statement_fails():
    class Broken(FakeCursor):
        def execute(self, sql, params=None):
            raise RuntimeError("boom")

    cache, conn = cache_with(Broken())
    with pytest.raises(RuntimeError):
        cache.load("DE", 2026)
    assert conn.closed and conn.commits == 0
