"""HTTP client for contacts-service. Every failure becomes ContactsUnavailable."""

import httpx


class ContactsUnavailable(Exception):
    """contacts-service did not answer in time, was unreachable, or returned something unusable."""


class ContactsClient:
    def __init__(
        self,
        base_url: str,
        timeout_s: float,
        transport: httpx.BaseTransport | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        # One timeout applied to connecting, sending and reading, so a hung service
        # cannot hold a request open for long.
        self._http = httpx.Client(timeout=httpx.Timeout(timeout_s), transport=transport)

    def fetch_contacts(self) -> list[dict]:
        try:
            response = self._http.get(f"{self._base_url}/contacts")
            response.raise_for_status()
            contacts = response.json()
        except httpx.TimeoutException as exc:
            raise ContactsUnavailable("contacts-service timed out") from exc
        except httpx.HTTPError as exc:
            raise ContactsUnavailable(f"contacts-service request failed: {exc}") from exc
        except ValueError as exc:  # body is not valid JSON
            raise ContactsUnavailable("contacts-service returned invalid JSON") from exc
        if not isinstance(contacts, list):
            raise ContactsUnavailable("contacts-service returned an unexpected response")
        return contacts