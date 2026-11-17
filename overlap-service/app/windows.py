"""
This is the algorithm behind the app.
It find the time windows when two people can both take a call.
It works by converting each person’s local unavailable times,
like sleep, busy blocks, and outside preferred hours,
into UTC. Then it removes those blocked times from
the full time range and keeps only the free stretches
that are long enough for the call.

"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

Interval = tuple[datetime, datetime]


def get_zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"unknown time zone: {name!r}") from exc


@dataclass(frozen=True)
class BusyBlock:
    weekday: int  # 0 = Monday ... 6 = Sunday
    start: time
    end: time


@dataclass(frozen=True)
class Person:
    tz: str
    sleep_start: time
    sleep_end: time
    busy: tuple[BusyBlock, ...] = ()
    preferred_start: time | None = None
    preferred_end: time | None = None

    def __post_init__(self) -> None:
        if (self.preferred_start is None) != (self.preferred_end is None):
            raise ValueError("set both preferred_start and preferred_end, or neither")


@dataclass(frozen=True)
class Window:
    start: datetime
    end: datetime

    @property
    def minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)

    def in_zone(self, tz: str) -> tuple[datetime, datetime]:
        zone = get_zone(tz)
        return self.start.astimezone(zone), self.end.astimezone(zone)


def local_to_utc(zone: ZoneInfo, day: date, start: time, end: time) -> Interval | None:
    # Convert a local time range on one day into UTC.
    if start == end:
        return None

    end_day = day
    if end <= start:
        end_day = day + timedelta(days=1)

    start_dt = datetime.combine(day, start, tzinfo=zone).astimezone(UTC)
    end_dt = datetime.combine(end_day, end, tzinfo=zone).astimezone(UTC)
    return start_dt, end_dt


def get_unavailable(person: Person, period_start: datetime, period_end: datetime) -> list[Interval]:
    # Return all UTC intervals when this person cannot take a call.
    zone = get_zone(person.tz)
    intervals: list[Interval] = []

    start_day = period_start.astimezone(zone).date() - timedelta(days=1)
    end_day = period_end.astimezone(zone).date() + timedelta(days=1)

    day = start_day
    while day <= end_day:
        sleep = local_to_utc(zone, day, person.sleep_start, person.sleep_end)
        if sleep is not None:
            intervals.append(sleep)

        if person.preferred_start is not None and person.preferred_end is not None:
            outside = local_to_utc(zone, day, person.preferred_end, person.preferred_start)
            if outside is not None:
                intervals.append(outside)

        for block in person.busy:
            if block.weekday == day.weekday():
                busy = local_to_utc(zone, day, block.start, block.end)
                if busy is not None:
                    intervals.append(busy)

        day += timedelta(days=1)

    return intervals


def merge_intervals(intervals: list[Interval]) -> list[Interval]:
    # Join overlapping or touching intervals.
    if not intervals:
        return []

    merged: list[Interval] = []
    for start, end in sorted(intervals):
        if not merged:
            merged.append((start, end))
            continue

        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))

    return merged


def subtract_blocked(period: Interval, blocked: list[Interval]) -> list[Interval]:
    # Return the parts of period that are not blocked.
    free: list[Interval] = []
    cursor = period[0]

    for start, end in blocked:
        if end <= cursor:
            continue
        if start >= period[1]:
            break

        if start > cursor:
            free.append((cursor, start))

        if end > cursor:
            cursor = end

    if cursor < period[1]:
        free.append((cursor, period[1]))

    return free


def find_windows(
    user: Person,
    contact: Person,
    call_minutes: int,
    now: datetime,
    days: int = 7,
) -> list[Window]:
    # Find shared free windows for the next few days.
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if call_minutes <= 0 or days <= 0:
        raise ValueError("call_minutes and days must be positive")

    period_start = now.astimezone(UTC)
    period_end = period_start + timedelta(days=days)

    user_blocked = get_unavailable(user, period_start, period_end)
    contact_blocked = get_unavailable(contact, period_start, period_end)
    blocked = merge_intervals(user_blocked + contact_blocked)

    free = subtract_blocked((period_start, period_end), blocked)
    needed = timedelta(minutes=call_minutes)

    windows: list[Window] = []
    for start, end in free:
        if end - start >= needed:
            windows.append(Window(start, end))

    return windows
