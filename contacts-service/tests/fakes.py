"""An in-memory repository so API tests run without a database."""

from datetime import UTC, datetime

from app.repository import DatabaseUnavailable


class InMemoryRepository:
    def __init__(self):
        self.rows: dict[int, dict] = {}
        self.next_id = 1

    def list_contacts(self):
        return sorted(self.rows.values(), key=lambda c: (c["name"], c["id"]))

    def get_contact(self, contact_id):
        return self.rows.get(contact_id)

    def create_contact(self, data):
        now = datetime.now(UTC)
        row = {**data, "id": self.next_id, "created_at": now, "updated_at": now}
        self.rows[self.next_id] = row
        self.next_id += 1
        return row

    def update_contact(self, contact_id, data):
        if contact_id not in self.rows:
            return None
        self.rows[contact_id] = {
            **self.rows[contact_id],
            **data,
            "updated_at": datetime.now(UTC),
        }
        return self.rows[contact_id]

    def delete_contact(self, contact_id):
        return self.rows.pop(contact_id, None) is not None


class DownRepository:
    """Behaves like a database that cannot be reached."""

    def __getattr__(self, name):
        def fail(*args, **kwargs):
            raise DatabaseUnavailable("connection refused")

        return fail
