"""Apply versioned .sql migration files in order, once each, on startup.

Applied versions are recorded in the schema_migrations table, so restarting the
container never re-runs a migration.
"""

import logging
import time
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger("contacts.migrations")

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

CREATE_TRACKING_TABLE = """
IF OBJECT_ID('schema_migrations', 'U') IS NULL
CREATE TABLE schema_migrations (
    version NVARCHAR(100) NOT NULL PRIMARY KEY,
    applied_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
)
"""


def list_migration_files(directory: Path = MIGRATIONS_DIR) -> list[Path]:
    """Return migration files sorted by their numeric prefix (001_, 002_, ...)."""
    return sorted(directory.glob("*.sql"), key=lambda p: p.name)


def apply_migrations(conn, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply every migration not yet recorded. Returns the versions applied now."""
    cursor = conn.cursor()
    cursor.execute(CREATE_TRACKING_TABLE)
    conn.commit()

    cursor.execute("SELECT version FROM schema_migrations")
    done = {row[0] for row in cursor.fetchall()}

    applied = []
    for path in list_migration_files(directory):
        version = path.stem
        if version in done:
            continue
        logger.info("applying migration %s", version)
        cursor.execute(path.read_text(encoding="utf-8"))
        cursor.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
        conn.commit()
        applied.append(version)
    return applied


def run_with_retry(
    connect: Callable, attempts: int = 10, delay: float = 6.0, sleep: Callable = time.sleep
) -> list[str]:
    """Connect and migrate, retrying while the database starts or resumes from auto-pause."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            conn = connect()
            try:
                return apply_migrations(conn)
            finally:
                conn.close()
        except Exception as exc:  # database not ready yet
            last_error = exc
            logger.warning("database not ready (attempt %d/%d): %s", attempt, attempts, exc)
            sleep(delay)
    raise RuntimeError("could not apply migrations") from last_error
