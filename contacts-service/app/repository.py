"""Data access for contacts. All SQL for this service lives here.

The API layer only talks to a repository, so tests can swap in an in-memory one.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, time
from typing import Any, Protocol

import pymssql


class DatabaseUnavailable(Exception):
    """The database could not be reached (down, starting, or resuming from auto-pause)."""


class ContactsRepository(Protocol):
    def list_contacts(self) -> list[dict]: ...
    def get_contact(self, contact_id: int) -> dict | None: ...
    def create_contact(self, data: dict) -> dict: ...
    def update_contact(self, contact_id: int, data: dict) -> dict | None: ...
    def delete_contact(self, contact_id: int) -> bool: ...
    def list_calls(self, contact_id: int) -> list[dict] | None: ...
    def add_call(self, contact_id: int, data: dict) -> dict | None: ...
    def delete_call(self, contact_id: int, call_id: int) -> bool: ...


SELECT_ALL = """
SELECT c.id, c.name, c.city, c.time_zone, c.country_code, c.sleep_start, c.sleep_end,
       c.call_minutes, c.call_every_days, c.created_at, c.updated_at,
       (SELECT MAX(l.called_at) FROM call_logs l WHERE l.contact_id = c.id) AS last_called
FROM contacts c
ORDER BY c.name, c.id
"""

SELECT_ONE = """
SELECT c.id, c.name, c.city, c.time_zone, c.country_code, c.sleep_start, c.sleep_end,
       c.call_minutes, c.call_every_days, c.created_at, c.updated_at,
       (SELECT MAX(l.called_at) FROM call_logs l WHERE l.contact_id = c.id) AS last_called
FROM contacts c
WHERE c.id = %s
"""

INSERT = """
INSERT INTO contacts (name, city, time_zone, country_code, sleep_start, sleep_end,
                      call_minutes, call_every_days)
OUTPUT INSERTED.id, INSERTED.name, INSERTED.city, INSERTED.time_zone,
       INSERTED.country_code, INSERTED.sleep_start, INSERTED.sleep_end,
       INSERTED.call_minutes, INSERTED.call_every_days,
       INSERTED.created_at, INSERTED.updated_at
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""

UPDATE = """
UPDATE contacts
SET name = %s, city = %s, time_zone = %s, country_code = %s, sleep_start = %s,
    sleep_end = %s, call_minutes = %s, call_every_days = %s,
    updated_at = SYSUTCDATETIME()
WHERE id = %s
"""

DELETE = "DELETE FROM contacts WHERE id = %s"

CONTACT_EXISTS = "SELECT id FROM contacts WHERE id = %s"

SELECT_CALLS = """
SELECT id, contact_id, called_at, minutes, note
FROM call_logs
WHERE contact_id = %s
ORDER BY called_at DESC, id DESC
"""

INSERT_CALL = """
INSERT INTO call_logs (contact_id, called_at, minutes, note)
OUTPUT INSERTED.id, INSERTED.contact_id, INSERTED.called_at, INSERTED.minutes, INSERTED.note
VALUES (%s, COALESCE(%s, SYSUTCDATETIME()), %s, %s)
"""

DELETE_CALL = "DELETE FROM call_logs WHERE id = %s AND contact_id = %s"

FIELDS = (
    "name",
    "city",
    "time_zone",
    "country_code",
    "sleep_start",
    "sleep_end",
    "call_minutes",
    "call_every_days",
)


def to_time(value: Any) -> time:
    """Accept a time, or a string like '23:00:00.0000000' from older drivers."""
    if isinstance(value, time):
        return value
    return time.fromisoformat(str(value)[:8])


def to_utc(value: Any) -> datetime:
    """Database timestamps are stored in UTC without a zone; mark them as UTC."""
    if not isinstance(value, datetime):
        value = datetime.fromisoformat(str(value)[:26])
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def row_to_contact(row: dict) -> dict:
    contact = dict(row)
    contact["sleep_start"] = to_time(row["sleep_start"])
    contact["sleep_end"] = to_time(row["sleep_end"])
    contact["created_at"] = to_utc(row["created_at"])
    contact["updated_at"] = to_utc(row["updated_at"])
    last = row.get("last_called")
    contact["last_called"] = to_utc(last) if last is not None else None
    return contact


def row_to_call(row: dict) -> dict:
    return {**row, "called_at": to_utc(row["called_at"])}


def utc_param(value: datetime | None) -> str | None:
    """Send a UTC timestamp to DATETIME2 as plain text, without a zone."""
    if value is None:
        return None
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")


def params_from(data: dict) -> tuple:
    return tuple(
        data[f].strftime("%H:%M:%S") if isinstance(data[f], time) else data[f] for f in FIELDS
    )


class SqlContactsRepository:
    """Contacts stored in SQL Server / Azure SQL. One connection per call."""

    def __init__(self, connect: Callable):
        self._connect = connect

    @contextmanager
    def _cursor(self) -> Iterator:
        try:
            conn = self._connect()
        except (pymssql.OperationalError, pymssql.InterfaceError, OSError) as exc:
            raise DatabaseUnavailable(str(exc)) from exc
        try:
            yield conn.cursor(as_dict=True)
            conn.commit()
        finally:
            conn.close()

    def list_contacts(self) -> list[dict]:
        with self._cursor() as cur:
            cur.execute(SELECT_ALL)
            return [row_to_contact(r) for r in cur.fetchall()]

    def get_contact(self, contact_id: int) -> dict | None:
        with self._cursor() as cur:
            cur.execute(SELECT_ONE, (contact_id,))
            row = cur.fetchone()
        return row_to_contact(row) if row else None

    def create_contact(self, data: dict) -> dict:
        with self._cursor() as cur:
            cur.execute(INSERT, params_from(data))
            row = cur.fetchone()
        return row_to_contact(row)  # a new contact has no calls yet

    def update_contact(self, contact_id: int, data: dict) -> dict | None:
        with self._cursor() as cur:
            cur.execute(UPDATE, (*params_from(data), contact_id))
            if cur.rowcount == 0:
                return None
            cur.execute(SELECT_ONE, (contact_id,))
            row = cur.fetchone()
        return row_to_contact(row) if row else None

    def delete_contact(self, contact_id: int) -> bool:
        with self._cursor() as cur:
            cur.execute(DELETE, (contact_id,))
            return cur.rowcount > 0

    def _contact_exists(self, cur, contact_id: int) -> bool:
        cur.execute(CONTACT_EXISTS, (contact_id,))
        return cur.fetchone() is not None

    def list_calls(self, contact_id: int) -> list[dict] | None:
        """Newest first. None means the contact does not exist."""
        with self._cursor() as cur:
            if not self._contact_exists(cur, contact_id):
                return None
            cur.execute(SELECT_CALLS, (contact_id,))
            return [row_to_call(r) for r in cur.fetchall()]

    def add_call(self, contact_id: int, data: dict) -> dict | None:
        """None means the contact does not exist."""
        with self._cursor() as cur:
            if not self._contact_exists(cur, contact_id):
                return None
            params = (contact_id, utc_param(data.get("called_at")), data.get("minutes"))
            cur.execute(INSERT_CALL, (*params, data.get("note")))
            return row_to_call(cur.fetchone())

    def delete_call(self, contact_id: int, call_id: int) -> bool:
        with self._cursor() as cur:
            cur.execute(DELETE_CALL, (call_id, contact_id))
            return cur.rowcount > 0
