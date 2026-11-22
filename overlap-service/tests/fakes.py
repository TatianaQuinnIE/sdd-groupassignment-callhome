"""Stand-ins for contacts-service so tests never make real HTTP calls."""

from app.contacts_client import ContactsUnavailable


class FakeContacts:
    def __init__(self, contacts):
        self._contacts = contacts

    def fetch_contacts(self):
        return self._contacts


class DownContacts:
    def fetch_contacts(self):
        raise ContactsUnavailable("contacts-service timed out")
