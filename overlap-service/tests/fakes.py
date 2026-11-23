"""Stand-ins for contacts-service, Nager.Date and the database, so tests make no real calls."""

from app.contacts_client import ContactsUnavailable
from app.holidays import HolidaysUnavailable


class FakeContacts:
    def __init__(self, contacts):
        self._contacts = contacts

    def fetch_contacts(self):
        return self._contacts


class DownContacts:
    def fetch_contacts(self):
        raise ContactsUnavailable("contacts-service timed out")


class FakeHolidaySource:
    """Nager.Date stand-in: holidays by (country, year), counting how often it is asked."""

    def __init__(self, data=None, down=False):
        self.data = data or {}
        self.down = down
        self.calls = []

    def fetch(self, country, year):
        self.calls.append((country, year))
        if self.down:
            raise HolidaysUnavailable("Nager.Date timed out")
        return list(self.data.get((country, year), []))


class InMemoryHolidayStore:
    """Database cache stand-in. Set fail_load / fail_save to simulate a broken database."""

    def __init__(self, data=None, fail_load=False, fail_save=False):
        self.data = dict(data or {})
        self.fail_load = fail_load
        self.fail_save = fail_save
        self.loads = []

    def load(self, country, year):
        self.loads.append((country, year))
        if self.fail_load:
            raise ConnectionError("database down")
        return self.data.get((country, year))

    def save(self, country, year, holidays):
        if self.fail_save:
            raise ConnectionError("database down")
        self.data[(country, year)] = list(holidays)
