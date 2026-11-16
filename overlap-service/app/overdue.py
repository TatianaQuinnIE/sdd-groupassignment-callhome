"""
Overdue ranks contacts by how overdue they are for a call.
It compares how long it has been since each person was last
called to the schedule you usually follow for them, so
someone who is much later than expected comes first.
Contacts who have never been called are placed at the top.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

SECONDS_PER_DAY = 86400


@dataclass(frozen=True)
class CallHistory:
    contact_id: int
    call_every_days: int
    last_called: datetime | None


@dataclass(frozen=True)
class Overdue:
    days_since: float | None
    ratio: float | None
    is_due: bool


@dataclass(frozen=True)
class Ranked:
    contact_id: int
    overdue: Overdue


def overdue_status(last_called: datetime | None, call_every_days: int, now: datetime) -> Overdue:
    if call_every_days <= 0:
        raise ValueError("call_every_days must be positive")
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if last_called is None:
        return Overdue(None, None, True)
    if last_called.tzinfo is None:
        raise ValueError("last_called must be timezone-aware")

    days_since = max(0.0, (now - last_called).total_seconds() / SECONDS_PER_DAY)
    ratio = days_since / call_every_days
    return Overdue(days_since, ratio, ratio >= 1)


def rank_by_overdue(contacts: Iterable[CallHistory], now: datetime) -> list[Ranked]:
    ranked: list[Ranked] = []
    for contact in contacts:
        status = overdue_status(contact.last_called, contact.call_every_days, now)
        ranked.append(Ranked(contact.contact_id, status))

    return sorted(
        ranked,
        key=lambda item: (
            item.overdue.ratio is not None,
            -(item.overdue.ratio or 0.0),
            item.contact_id,
        ),
    )
