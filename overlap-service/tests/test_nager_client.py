from datetime import date

import httpx
import pytest

from app.holidays import Holiday, HolidaysUnavailable
from app.nager_client import NagerClient

PAYLOAD = [
    {"date": "2026-12-25", "localName": "Weihnachtstag", "name": "Christmas Day", "global": True},
    {"date": "2026-03-17", "localName": "Regional", "name": "Regional Day", "global": False},
]


def client_for(handler):
    return NagerClient(
        "https://nager.test/api/v3", timeout_s=3, transport=httpx.MockTransport(handler)
    )


def test_fetches_and_parses_holidays():
    def handler(request):
        assert str(request.url) == "https://nager.test/api/v3/PublicHolidays/2026/DE"
        return httpx.Response(200, json=PAYLOAD)

    assert client_for(handler).fetch("DE", 2026) == [
        Holiday(date(2026, 12, 25), "Christmas Day", "Weihnachtstag")
    ]


def test_country_code_is_upper_cased_in_the_url():
    def handler(request):
        assert request.url.path.endswith("/2026/KR")
        return httpx.Response(200, json=[])

    assert client_for(handler).fetch("kr", 2026) == []


@pytest.mark.parametrize("status", [204, 404])
def test_no_data_for_a_country_means_no_holidays(status):
    assert client_for(lambda request: httpx.Response(status)).fetch("ZZ", 2026) == []


@pytest.mark.parametrize("country", ["", "K", "KOR", "../", "K1", "a/b"])
def test_values_that_are_not_country_codes_never_reach_the_network(country):
    def handler(request):
        raise AssertionError("no request should be made")

    assert client_for(handler).fetch(country, 2026) == []


def test_timeout_becomes_holidays_unavailable():
    def handler(request):
        raise httpx.ReadTimeout("too slow", request=request)

    with pytest.raises(HolidaysUnavailable, match="timed out"):
        client_for(handler).fetch("DE", 2026)


def test_connection_error_becomes_holidays_unavailable():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(HolidaysUnavailable):
        client_for(handler).fetch("DE", 2026)


@pytest.mark.parametrize("status", [429, 500, 503])
def test_error_status_becomes_holidays_unavailable(status):
    with pytest.raises(HolidaysUnavailable):
        client_for(lambda request: httpx.Response(status)).fetch("DE", 2026)


def test_invalid_json_becomes_holidays_unavailable():
    with pytest.raises(HolidaysUnavailable, match="unusable"):
        client_for(lambda request: httpx.Response(200, text="<html>")).fetch("DE", 2026)


def test_a_response_that_is_not_a_list_becomes_holidays_unavailable():
    with pytest.raises(HolidaysUnavailable, match="unusable"):
        client_for(lambda request: httpx.Response(200, json={"error": "x"})).fetch("DE", 2026)
