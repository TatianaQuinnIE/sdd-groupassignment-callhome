"""HTTP client for Nager.Date (free public-holiday API, no key).

Every failure raises HolidaysUnavailable.
"""

import httpx

from app.holidays import Holiday, HolidaysUnavailable, parse_nager


class NagerClient:
    def __init__(
        self,
        base_url: str,
        timeout_s: float,
        transport: httpx.BaseTransport | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._http = httpx.Client(timeout=httpx.Timeout(timeout_s), transport=transport)

    def fetch(self, country: str, year: int) -> list[Holiday]:
        if len(country) != 2 or not country.isalpha():
            return []  # not a country code, and never put it into a URL
        url = f"{self._base_url}/PublicHolidays/{int(year)}/{country.upper()}"
        try:
            response = self._http.get(url)
        except httpx.TimeoutException as exc:
            raise HolidaysUnavailable("Nager.Date timed out") from exc
        except httpx.HTTPError as exc:
            raise HolidaysUnavailable(f"Nager.Date request failed: {exc}") from exc

        if response.status_code in (204, 404):
            return []  # no holiday data for this country and year
        try:
            response.raise_for_status()
            return parse_nager(response.json())
        except httpx.HTTPError as exc:
            raise HolidaysUnavailable(f"Nager.Date returned an error: {exc}") from exc
        except ValueError as exc:  # invalid JSON, or not a list
            raise HolidaysUnavailable("Nager.Date returned an unusable response") from exc
