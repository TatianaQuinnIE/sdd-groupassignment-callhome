from datetime import UTC, datetime, time

import pymssql
import pytest

from app import repository
from app.repository import DatabaseUnavailable, SqlContactsRepository

ROW = {
    "id": 1,
    "name": "Mum",
    "city": "Seoul",
    "time_zone": "Asia/Seoul",
    "country_code": "KR",
    "sleep_start": "22:30:00.0000000",  # older drivers return strings
    "sleep_end": time(6, 30),
    "call_minutes": 45,
    "call_every_days": 7,
    "created_at": datetime(2026, 11, 17, 10, 0),
    "updated_at": "2026-11-17 10:00:00.1234567",
}

DATA = {k: v for k, v in ROW.items() if k in repository.FIELDS} | {"sleep_start": time(22, 30)}


class FakeCursor:
    def __init__(self, rows, rowcount=1):
        self.rows = rows
        self.rowcount = rowcount
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConn:
    def __init__(self, cursor):
        self.cur = cursor
        self.committed = False
        self.closed = False

    def cursor(self, as_dict=False):
        assert as_dict is True
        return self.cur

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def make_repo(rows=None, rowcount=1):
    conn = FakeConn(FakeCursor([dict(ROW)] if rows is None else rows, rowcount))
    return SqlContactsRepository(lambda: conn), conn


def test_list_converts_types():
    repo, conn = make_repo()
    [contact] = repo.list_contacts()
    assert contact["sleep_start"] == time(22, 30)
    assert contact["created_at"] == datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
    assert contact["updated_at"].tzinfo is UTC
    assert conn.committed and conn.closed


def test_get_found_and_missing():
    repo, conn = make_repo()
    assert repo.get_contact(1)["name"] == "Mum"
    assert conn.cur.calls[0][1] == (1,)
    repo, _ = make_repo(rows=[])
    assert repo.get_contact(2) is None


def test_create_sends_values_in_column_order():
    repo, conn = make_repo()
    repo.create_contact(DATA)
    sql, params = conn.cur.calls[0]
    assert sql.strip().startswith("INSERT INTO contacts")
    assert params == ("Mum", "Seoul", "Asia/Seoul", "KR", "22:30:00", "06:30:00", 45, 7)


def test_update_found_and_missing():
    repo, conn = make_repo()
    assert repo.update_contact(1, DATA)["id"] == 1
    assert conn.cur.calls[0][1][-1] == 1  # id goes last, for WHERE
    repo, _ = make_repo(rows=[])
    assert repo.update_contact(9, DATA) is None


def test_delete_uses_rowcount():
    repo, _ = make_repo(rowcount=1)
    assert repo.delete_contact(1) is True
    repo, _ = make_repo(rowcount=0)
    assert repo.delete_contact(1) is False


def test_connection_failure_becomes_database_unavailable():
    def connect():
        raise pymssql.OperationalError("cannot connect")

    with pytest.raises(DatabaseUnavailable):
        SqlContactsRepository(connect).list_contacts()


def test_connection_closed_even_on_error():
    repo, conn = make_repo()

    def boom(sql, params=None):
        raise RuntimeError("bad query")

    conn.cur.execute = boom
    with pytest.raises(RuntimeError):
        repo.list_contacts()
    assert conn.closed and not conn.committed
