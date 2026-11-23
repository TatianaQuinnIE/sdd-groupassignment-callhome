"""Public holidays: parsing Nager.Date data, a two-level cache, and matching to call windows.

Holidays are looked up per country and year. A lookup checks memory first, then the database
cache, and only then asks Nager.Date. If Nager.Date fails, the failure is remembered for a
minute so a long outage costs one slow request, not one per page load.
"""

import datetime as dt
import logging
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Protocol

from app.windows import Window, get_zone

logger = logging.getLogger("overlap.holidays")


class HolidaysUnavailable(Exception):
    """Holiday data could not be fetched (Nager.Date down, too slow, or unusable)."""


@dataclass(frozen=True)
class Holiday:
    date: dt.date
    name: str
    local_name: str


class HolidaySource(Protocol):
    def fetch(self, country: str, year: int) -> list[Holiday]: ...


class HolidayStore(Protocol):
    def load(self, country: str, year: int) -> list[Holiday] | None: ...
    def save(self, country: str, year: int, holidays: list[Holiday]) -> None: ...


@dataclass
class HolidayLookup:
    by_country: dict[str, list[Holiday]] = field(default_factory=dict)
    available: bool = True  # False if some country's holidays could not be found


def parse_nager(payload: object) -> list[Holiday]:
    """Nager.Date PublicHolidays JSON to Holidays.

    Holidays that only apply to some regions of a country ("global": false) are left out,
    because flagging them would be wrong for most of that country. Malformed entries are
    skipped; a payload that is not a list at all raises ValueError.
    """
    if not isinstance(payload, list):
        raise ValueError("expected a list of holidays")
    holidays = []
    for item in payload:
        try:
            if item.get("global", True) is False:
                continue
            name = item["name"]
            holidays.append(
                Holiday(dt.date.fromisoformat(item["date"]), name, item.get("localName") or name)
            )
        except (KeyError, ValueError, TypeError, AttributeError):
            continue
    return sorted(holidays, key=lambda h: (h.date, h.name))


def holidays_in_range(holidays: Iterable[Holiday], start: dt.date, end: dt.date) -> list[Holiday]:
    """Holidays on or between two dates (both inclusive)."""
    return [h for h in holidays if start <= h.date <= end]


def holiday_for_window(window: Window, tz: str, holidays: Iterable[Holiday]) -> Holiday | None:
    """The first holiday falling on any local day the window touches, in the contact's zone."""
    zone = get_zone(tz)
    first_day = window.start.astimezone(zone).date()
    # The end is exclusive, so a window ending exactly at midnight does not touch that day.
    last_day = (window.end - dt.timedelta(microseconds=1)).astimezone(zone).date()
    for holiday in holidays:
        if first_day <= holiday.date <= last_day:
            return holiday
    return None


class HolidayService:
    def __init__(
        self,
        source: HolidaySource,
        store: HolidayStore | None = None,
        retry_after_s: float = 60.0,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self._source = source
        self._store = store
        self._retry_after_s = retry_after_s
        self._monotonic = monotonic
        self._memory: dict[tuple[str, int], list[Holiday]] = {}
        self._not_stored: set[tuple[str, int]] = set()  # database had nothing (or failed)
        self._down_until = 0.0

    def for_year(self, country: str, year: int) -> list[Holiday]:
        key = (country, year)
        if key in self._memory:
            return self._memory[key]

        stored = self._load_stored(key)
        if stored is not None:
            self._memory[key] = stored
            return stored

        if self._monotonic() < self._down_until:
            raise HolidaysUnavailable("Nager.Date failed recently, not retrying yet")
        try:
            fetched = self._source.fetch(country, year)
        except HolidaysUnavailable:
            self._down_until = self._monotonic() + self._retry_after_s
            raise
        self._memory[key] = fetched
        self._save_stored(key, fetched)
        return fetched

    def lookup(self, countries: Iterable[str], years: Iterable[int]) -> HolidayLookup:
        """Holidays for several countries and years. Never raises: failures set available=False."""
        result = HolidayLookup()
        wanted_years = sorted(set(years))
        for country in sorted(set(countries)):
            try:
                result.by_country[country] = [
                    h for year in wanted_years for h in self.for_year(country, year)
                ]
            except HolidaysUnavailable as exc:
                logger.warning("no holidays for %s: %s", country, exc)
                result.available = False
        return result

    # The database cache is an optimisation: if it fails, carry on without it.
    def _load_stored(self, key: tuple[str, int]) -> list[Holiday] | None:
        if self._store is None or key in self._not_stored:
            return None
        try:
            stored = self._store.load(*key)
        except Exception as exc:
            logger.warning("holiday cache read failed for %s: %s", key, exc)
            stored = None
        if stored is None:
            self._not_stored.add(key)
        return stored

    def _save_stored(self, key: tuple[str, int], holidays: list[Holiday]) -> None:
        if self._store is None:
            return
        try:
            self._store.save(*key, holidays)
        except Exception as exc:
            logger.warning("holiday cache write failed for %s: %s", key, exc)
