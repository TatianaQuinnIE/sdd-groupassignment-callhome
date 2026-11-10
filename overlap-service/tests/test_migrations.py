import pytest

from app import migrations


class FakeCursor:
    def __init__(self, done):
        self.done = set(done)
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append(sql)
        if params:
            self.done.add(params[0])

    def fetchall(self):
        return [(v,) for v in self.done]


class FakeConn:
    def __init__(self, done=()):
        self.cur = FakeCursor(done)
        self.commits = 0
        self.closed = False

    def cursor(self):
        return self.cur

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


@pytest.fixture
def migration_dir(tmp_path):
    (tmp_path / "002_second.sql").write_text("CREATE TABLE b (id INT);")
    (tmp_path / "001_first.sql").write_text("CREATE TABLE a (id INT);")
    return tmp_path


def test_files_sorted_by_version(migration_dir):
    names = [p.name for p in migrations.list_migration_files(migration_dir)]
    assert names == ["001_first.sql", "002_second.sql"]


def test_applies_pending_in_order(migration_dir):
    conn = FakeConn()
    assert migrations.apply_migrations(conn, migration_dir) == ["001_first", "002_second"]


def test_skips_already_applied(migration_dir):
    conn = FakeConn(done={"001_first"})
    assert migrations.apply_migrations(conn, migration_dir) == ["002_second"]
    assert "CREATE TABLE a (id INT);" not in conn.cur.executed


def test_real_migrations_folder_has_files():
    assert migrations.list_migration_files()[0].name == "001_create_holiday_cache.sql"


def test_real_migration_does_not_touch_tracking_table():
    sql = migrations.list_migration_files()[0].read_text(encoding="utf-8")
    assert "schema_migrations" not in sql


def test_retry_until_database_ready():
    calls = {"n": 0}
    conn = FakeConn(done={p.stem for p in migrations.list_migration_files()})

    def connect():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("starting")
        return conn

    assert migrations.run_with_retry(connect, attempts=5, sleep=lambda _: None) == []
    assert calls["n"] == 3 and conn.closed


def test_retry_gives_up():
    def connect():
        raise ConnectionError("down")

    with pytest.raises(RuntimeError):
        migrations.run_with_retry(connect, attempts=2, sleep=lambda _: None)
