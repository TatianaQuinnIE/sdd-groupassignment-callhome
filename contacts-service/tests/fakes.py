"""An in-memory repository so API tests run without a database."""

from datetime import UTC, datetime

from app.repository import DatabaseUnavailable


class InMemoryRepository:
    def __init__(self):
        self.rows: dict[int, dict] = {}
        self.next_id = 1
        self.calls: dict[int, dict] = {}
        self.next_call_id = 1

    def _with_last_called(self, contact):
        times = [c["called_at"] for c in self.calls.values() if c["contact_id"] == contact["id"]]
        return {**contact, "last_called": max(times) if times else None}

    def list_contacts(self):
        rows = [self._with_last_called(c) for c in self.rows.values()]
        return sorted(rows, key=lambda c: (c["name"], c["id"]))

    def get_contact(self, contact_id):
        row = self.rows.get(contact_id)
        return self._with_last_called(row) if row else None

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
        return self._with_last_called(self.rows[contact_id])

    def delete_contact(self, contact_id):
        self.calls = {k: v for k, v in self.calls.items() if v["contact_id"] != contact_id}
        return self.rows.pop(contact_id, None) is not None

    def list_calls(self, contact_id):
        if contact_id not in self.rows:
            return None
        mine = [c for c in self.calls.values() if c["contact_id"] == contact_id]
        return sorted(mine, key=lambda c: (c["called_at"], c["id"]), reverse=True)

    def add_call(self, contact_id, data):
        if contact_id not in self.rows:
            return None
        call = {
            "id": self.next_call_id,
            "contact_id": contact_id,
            "called_at": data.get("called_at") or datetime.now(UTC),
            "minutes": data.get("minutes"),
            "note": data.get("note"),
        }
        self.calls[self.next_call_id] = call
        self.next_call_id += 1
        return call

    def delete_call(self, contact_id, call_id):
        call = self.calls.get(call_id)
        if call is None or call["contact_id"] != contact_id:
            return False
        del self.calls[call_id]
        return True


class DownRepository:
    """Behaves like a database that cannot be reached."""

    def __getattr__(self, name):
        def fail(*args, **kwargs):
            raise DatabaseUnavailable("connection refused")

        return fail
