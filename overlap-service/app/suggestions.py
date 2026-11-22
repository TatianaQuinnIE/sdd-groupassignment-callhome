"""Turn contacts into ranked call suggestions. Pure functions: no HTTP and no database."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, time

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


def build_suggestions(
    contacts: list[dict], now: datetime, days: int, user: Person
) -> list[ContactSuggestion]:
    """Call windows for every contact, most overdue contact first.

    A contact whose data cannot be used (missing field, unknown time zone) is skipped with a
    warning, so one bad record never breaks the whole page.
    """
    usable: dict[int, tuple[dict, list[Window]]] = {}
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
            # Validate the overdue data here too, so a bad record is skipped now instead of
            # crashing the ranking step below.
            overdue_status(history.last_called, history.call_every_days, now)
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("skipping unusable contact %r: %s", contact.get("id"), exc)
            continue
        usable[history.contact_id] = (contact, windows)
        histories.append(history)

    suggestions = []
    for ranked in rank_by_overdue(histories, now):
        contact, windows = usable[ranked.contact_id]
        suggestions.append(
            ContactSuggestion(
                contact_id=ranked.contact_id,
                name=contact["name"],
                city=contact["city"],
                time_zone=contact["time_zone"],
                country_code=contact["country_code"],
                call_minutes=contact["call_minutes"],
                overdue=ranked.overdue,
                windows=windows,
            )
        )
    return suggestions
