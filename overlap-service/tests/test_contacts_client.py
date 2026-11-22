import httpx
import pytest

from app.contacts_client import ContactsClient, ContactsUnavailable


def client_for(handler, base_url="http://contacts:8000"):
    return ContactsClient(base_url, timeout_s=3, transport=httpx.MockTransport(handler))


def test_returns_the_contact_list():
    def handler(request):
        assert request.url.path == "/contacts"
        return httpx.Response(200, json=[{"id": 1, "name": "Mum"}])

    assert client_for(handler).fetch_contacts() == [{"id": 1, "name": "Mum"}]


def test_trailing_slash_in_base_url_is_fine():
    def handler(request):
        assert str(request.url) == "http://contacts:8000/contacts"
        return httpx.Response(200, json=[])

    assert client_for(handler, "http://contacts:8000/").fetch_contacts() == []


def test_timeout_becomes_contacts_unavailable():
    def handler(request):
        raise httpx.ReadTimeout("too slow", request=request)

    with pytest.raises(ContactsUnavailable, match="timed out"):
        client_for(handler).fetch_contacts()


def test_connection_error_becomes_contacts_unavailable():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(ContactsUnavailable):
        client_for(handler).fetch_contacts()


@pytest.mark.parametrize("status", [404, 500, 503])
def test_error_status_becomes_contacts_unavailable(status):
    with pytest.raises(ContactsUnavailable):
        client_for(lambda request: httpx.Response(status)).fetch_contacts()


def test_invalid_json_becomes_contacts_unavailable():
    with pytest.raises(ContactsUnavailable, match="invalid JSON"):
        client_for(lambda request: httpx.Response(200, text="<html>")).fetch_contacts()


def test_non_list_json_becomes_contacts_unavailable():
    with pytest.raises(ContactsUnavailable, match="unexpected"):
        client_for(lambda request: httpx.Response(200, json={"detail": "x"})).fetch_contacts()
