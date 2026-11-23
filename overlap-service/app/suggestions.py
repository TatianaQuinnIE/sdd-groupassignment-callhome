"""Turn contacts into ranked call suggestions. Pure functions: no HTTP and no database."""

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.holidays import Holiday, holidays_in_range
from app.overdue import CallHistory, Overdue, overdue_status, rank_by_overdue
from app.windows import Person, Window, find_windows

logger = logging.getLogger("overlap.suggestions")


@dataclass(frozen=True)
class ContactSuggestion:
    contact_id: int
    name: str
    city: str
    time_zone: str
    country_code: str
    call_minutes: int
    overdue: Overdue
    windows: list[Window]
    holidays: list[Holiday] = field(default_factory=list)  # in the contact's country, next days


def _parse_time(value: str | None) -> time | None:
    return None if value is None else time.fromisoformat(value)


def _parse_last_called(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _contact_person(contact: dict) -> Person:
    """The contact's availability. preferred_start / preferred_end are optional."""
    return Person(
        tz=contact["time_zone"],
        sleep_start=_parse_time(contact["sleep_start"]),
        sleep_end=_parse_time(contact["sleep_end"]),
        preferred_start=_parse_time(contact.get("preferred_start")),
        preferred_end=_parse_time(contact.get("preferred_end")),
    )


def _local_dates(time_zone: str, now: datetime, days: int) -> tuple[date, date]:
    """First and last calendar day of the period, as dates in the contact's time zone."""
    zone = ZoneInfo(time_zone)
    return now.astimezone(zone).date(), (now + timedelta(days=days)).astimezone(zone).date()


def build_suggestions(
    contacts: list[dict],
    now: datetime,
    days: int,
    user: Person,
    holidays_by_country: dict[str, list[Holiday]] | None = None,
) -> list[ContactSuggestion]:
    """Call windows for every contact, most overdue contact first.

    holidays_by_country maps an upper-case country code to that country's holidays; each
    contact gets the ones that fall in the period, by the contact's own calendar.
    A contact whose data cannot be used (missing field, unknown time zone) is skipped with a
    warning, so one bad record never breaks the whole page.
    """
    holidays_by_country = holidays_by_country or {}
    usable: dict[int, ContactSuggestion] = {}
    histories: list[CallHistory] = []
    for contact in contacts:
        try:
            windows = find_windows(
                user, _contact_person(contact), contact["call_minutes"], now, days
            )
            history = CallHistory(
                contact["id"],
                contact["call_every_days"],
                _parse_last_called(contact.get("last_called")),
            )
            first_day, last_day = _local_dates(contact["time_zone"], now, days)
            country = str(contact["country_code"]).upper()
            # Every field the response needs (and the overdue maths) runs inside the try, so a
            # bad record is skipped here and cannot crash the ranking below.
            suggestion = ContactSuggestion(
                contact_id=history.contact_id,
                name=contact["name"],
                city=contact["city"],
                time_zone=contact["time_zone"],
                country_code=country,
                call_minutes=contact["call_minutes"],
                overdue=overdue_status(history.last_called, history.call_every_days, now),
                windows=windows,
                holidays=holidays_in_range(
                    holidays_by_country.get(country, []), first_day, last_day
                ),
            )
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("skipping unusable contact %r: %s", contact.get("id"), exc)
            continue
        usable[history.contact_id] = suggestion
        histories.append(history)

    return [usable[ranked.contact_id] for ranked in rank_by_overdue(histories, now)]
