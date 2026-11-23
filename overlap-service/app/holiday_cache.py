"""Holiday cache in this service's own database (tables from migration 001).

One fetch from Nager.Date per country and year is stored. holiday_cache_status records that a
country and year was fetched, even when it has no holidays, so empty years are not refetched.
"""

import datetime as dt
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from app.holidays import Holiday


def _to_date(value: Any) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


class SqlHolidayCache:
    """One connection per call, like the contacts repository."""

    def __init__(self, connect: Callable):
        self._connect = connect

    @contextmanager
    def _cursor(self) -> Iterator:
        conn = self._connect()
        try:
            yield conn.cursor()
            conn.commit()
        finally:
            conn.close()

    def load(self, country: str, year: int) -> list[Holiday] | None:
        """The cached holidays, or None if this country and year was never fetched."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT 1 FROM holiday_cache_status WHERE country_code = %s AND year = %s",
                (country, year),
            )
            if cur.fetchone() is None:
                return None
            cur.execute(
                "SELECT holiday_date, local_name, name FROM holiday_cache "
                "WHERE country_code = %s AND year = %s ORDER BY holiday_date, name",
                (country, year),
            )
            return [Holiday(_to_date(r[0]), r[2], r[1]) for r in cur.fetchall()]

    def save(self, country: str, year: int, holidays: list[Holiday]) -> None:
        """Replace what is stored for this country and year, in one transaction."""
        unique = {(h.date, h.name): h for h in holidays}.values()  # the table has a unique key
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM holiday_cache WHERE country_code = %s AND year = %s", (country, year)
            )
            cur.execute(
                "DELETE FROM holiday_cache_status WHERE country_code = %s AND year = %s",
                (country, year),
            )
            cur.execute(
                "INSERT INTO holiday_cache_status (country_code, year) VALUES (%s, %s)",
                (country, year),
            )
            for h in unique:
                cur.execute(
                    "INSERT INTO holiday_cache "
                    "(country_code, year, holiday_date, local_name, name, is_global) "
                    "VALUES (%s, %s, %s, %s, %s, 1)",
                    (country, year, h.date.isoformat(), h.local_name, h.name),
                )
