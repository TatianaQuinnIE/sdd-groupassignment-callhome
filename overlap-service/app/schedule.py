"""The user's own week ("My week"): time zone, sleep hours and weekly busy blocks.

The suggestions endpoint builds the user's Person from here, so changing the week in the
UI changes the call windows. The API layer only talks to a repository, so tests use the
in-memory one and the service uses the SQL one.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import time
from typing import Protocol

import pymssql

from app.windows import BusyBlock, Person

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class DatabaseUnavailable(Exception):
    """The database could not be reached (down, starting, or resuming from auto-pause)."""


def find_overlap(blocks: list[dict], weekday: int, start: time, end: time) -> dict | None:
    """The first existing block on the same weekday that overlaps start-end, if any.

    Touching blocks (one ends at 11:00, the next starts at 11:00) do not overlap.
    """
    for block in blocks:
        if block["weekday"] == weekday and start < block["end"] and block["start"] < end:
            return block
    return None


def describe(block: dict) -> str:
    """'Mon 09:00-11:00 (Class)', used in error messages."""
    text = f"{WEEKDAYS[block['weekday']]} {block['start']:%H:%M}-{block['end']:%H:%M}"
    return f"{text} ({block['label']})" if block.get("label") else text


def to_person(settings: dict, blocks: list[dict]) -> Person:
    return Person(
        tz=settings["time_zone"],
        sleep_start=settings["sleep_start"],
        sleep_end=settings["sleep_end"],
        busy=tuple(BusyBlock(b["weekday"], b["start"], b["end"]) for b in blocks),
    )


class ScheduleRepository(Protocol):
    def get_settings(self) -> dict: ...
    def update_settings(self, data: dict) -> dict: ...
    def list_blocks(self) -> list[dict]: ...
    def add_block(self, data: dict) -> dict: ...
    def delete_block(self, block_id: int) -> bool: ...


def _sorted(blocks: list[dict]) -> list[dict]:
    return sorted(blocks, key=lambda b: (b["weekday"], b["start"]))


class InMemoryScheduleRepository:
    """Used by the tests, and when no database is configured. Starts from a Person."""

    def __init__(self, person: Person):
        self._settings = {
            "time_zone": person.tz,
            "sleep_start": person.sleep_start,
            "sleep_end": person.sleep_end,
        }
        self._blocks: list[dict] = []
        for b in person.busy:
            self.add_block({"weekday": b.weekday, "start": b.start, "end": b.end, "label": None})

    def get_settings(self) -> dict:
        return dict(self._settings)

    def update_settings(self, data: dict) -> dict:
        self._settings = dict(data)
        return self.get_settings()

    def list_blocks(self) -> list[dict]:
        return _sorted([dict(b) for b in self._blocks])

    def add_block(self, data: dict) -> dict:
        block = {"id": max((b["id"] for b in self._blocks), default=0) + 1, **data}
        self._blocks.append(block)
        return dict(block)

    def delete_block(self, block_id: int) -> bool:
        before = len(self._blocks)
        self._blocks = [b for b in self._blocks if b["id"] != block_id]
        return len(self._blocks) < before


def _to_time(value) -> time:
    # pymssql returns TIME columns as text such as "09:00:00.0000000".
    return value if isinstance(value, time) else time.fromisoformat(str(value)[:8])


class SqlScheduleRepository:
    """my_settings and my_busy_blocks in the overlap database (migration 002)."""

    def __init__(self, connect: Callable):
        self._connect = connect

    @contextmanager
    def _cursor(self) -> Iterator:
        try:
            conn = self._connect()
        except (pymssql.OperationalError, pymssql.InterfaceError, OSError) as exc:
            raise DatabaseUnavailable(str(exc)) from exc
        try:
            cursor = conn.cursor(as_dict=True)
            yield cursor
            conn.commit()
        finally:
            conn.close()

    def get_settings(self) -> dict:
        with self._cursor() as cur:
            cur.execute("SELECT time_zone, sleep_start, sleep_end FROM my_settings WHERE id = 1")
            row = cur.fetchone()
        return {
            "time_zone": row["time_zone"],
            "sleep_start": _to_time(row["sleep_start"]),
            "sleep_end": _to_time(row["sleep_end"]),
        }

    def update_settings(self, data: dict) -> dict:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE my_settings SET time_zone = %s, sleep_start = %s, sleep_end = %s "
                "WHERE id = 1",
                (data["time_zone"], data["sleep_start"], data["sleep_end"]),
            )
        return self.get_settings()

    def list_blocks(self) -> list[dict]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, weekday, start_time, end_time, label FROM my_busy_blocks "
                "ORDER BY weekday, start_time"
            )
            rows = cur.fetchall()
        return [
            {
                "id": r["id"],
                "weekday": r["weekday"],
                "start": _to_time(r["start_time"]),
                "end": _to_time(r["end_time"]),
                "label": r["label"],
            }
            for r in rows
        ]

    def add_block(self, data: dict) -> dict:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO my_busy_blocks (weekday, start_time, end_time, label) "
                "OUTPUT INSERTED.id VALUES (%s, %s, %s, %s)",
                (data["weekday"], data["start"], data["end"], data["label"]),
            )
            new_id = cur.fetchone()["id"]
        return {"id": new_id, **data}

    def delete_block(self, block_id: int) -> bool:
        with self._cursor() as cur:
            cur.execute("DELETE FROM my_busy_blocks WHERE id = %s", (block_id,))
            return cur.rowcount > 0
