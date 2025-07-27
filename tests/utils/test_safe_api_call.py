import logging
from utils.safe_api import safe_api_call_with_retry, ClientError


def test_safe_api_call_with_retry(monkeypatch):
    calls = {"n": 0}

    def fake_api():
        calls["n"] += 1
        if calls["n"] < 2:
            raise ClientError("429", None)
        return 42

    monkeypatch.setattr("time.sleep", lambda x: None)
    result = safe_api_call_with_retry(fake_api, retries=3, delay=0)
    assert result == 42
    assert calls["n"] == 2


def test_safe_api_call_with_retry_fail(monkeypatch):
    def fake_api():
        raise ClientError("429", None)

    monkeypatch.setattr("time.sleep", lambda x: None)
    result = safe_api_call_with_retry(fake_api, retries=2, delay=0)
    assert result is None

