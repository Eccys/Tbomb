import bomber
import utils.provider as provider
from utils.provider import APIProvider


class DummyResponse:
    def __init__(self, text):
        self.text = text


def test_format_phone_and_version():
    assert bomber.format_phone("+91 (987)-654-3210") == "919876543210"
    assert bomber.format_phone("abc") == ""
    assert isinstance(bomber.get_version(), str)
    assert "91" in bomber.readisdc()["isdcodes"]


def test_api_provider_hit_when_status_false_does_not_raise_lock_error():
    api = APIProvider("91", "9876543210", "sms", delay=0)
    APIProvider.status = False
    # Previously raised RuntimeError: release unlocked lock / UnboundLocalError
    assert api.hit() is None
    assert not api.lock.locked()


def test_api_provider_selects_first_index_and_handles_removal(monkeypatch):
    api = APIProvider("91", "9876543210", "sms", delay=0)
    APIProvider.api_providers = [
        {"name": "p0", "url": "https://example.com/{cc}/{target}", "method": "GET", "identifier": "ok"},
        {"name": "p1", "url": "https://example.com/2/{target}", "method": "GET", "identifier": "ok"},
    ]

    called_urls = []

    def fake_request(**kwargs):
        called_urls.append(kwargs["url"])
        return DummyResponse("ok" if "2/" in kwargs["url"] else "fail")

    monkeypatch.setattr(provider.requests, "request", fake_request)

    # First hit tries index 0 ('p0'), fails, and removes 'p0'
    assert api.hit() is False
    assert called_urls == ["https://example.com/91/9876543210"]
    assert len(APIProvider.api_providers) == 1

    # Next hit tries 'p1' (now at index 0) and succeeds
    assert api.hit() is True
    assert called_urls[-1] == "https://example.com/2/9876543210"


def test_api_provider_removes_provider_on_network_exception(monkeypatch):
    api = APIProvider("91", "9876543210", "sms", delay=0)
    APIProvider.api_providers = [
        {"name": "dead", "url": "https://dead.invalid/{target}", "method": "GET", "identifier": "ok"},
        {"name": "alive", "url": "https://alive.example/{target}", "method": "GET", "identifier": "ok"},
    ]

    def fake_request(**kwargs):
        if "dead.invalid" in kwargs["url"]:
            raise RuntimeError("Connection timeout")
        return DummyResponse("ok")

    monkeypatch.setattr(provider.requests, "request", fake_request)

    assert api.hit() is False
    assert len(APIProvider.api_providers) == 1
    assert APIProvider.api_providers[0]["name"] == "alive"
    assert api.hit() is True

