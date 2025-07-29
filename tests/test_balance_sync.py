import streamlit as st
from utils.data_provider import get_futures_balance

class DummyST:
    def __init__(self):
        self.warned = False
        self.errored = False
    def warning(self, msg):
        self.warned = True
    def error(self, msg):
        self.errored = True


def test_get_balance_testnet(monkeypatch):
    st_dummy = DummyST()
    monkeypatch.setattr('utils.data_provider.st', st_dummy)
    called = {}
    monkeypatch.setattr('utils.data_provider.safe_api_call_with_retry', lambda func: func())
    monkeypatch.setattr('utils.data_provider.kirim_notifikasi_telegram', lambda msg: called.setdefault('msg', msg))
    monkeypatch.setattr('utils.data_provider.set_ready', lambda val: called.setdefault('ready', val))

    class Client:
        def futures_account_balance(self):  # Ubah ke futures_account_balance
            return [{'asset': 'USDT', 'balance': '55.5'}]  # Format response baru
    balance = get_futures_balance(Client())
    assert balance == 55.5
    assert called.get('ready') is True


def test_balance_returns_zero_on_html_response(monkeypatch):
    st_dummy = DummyST()
    monkeypatch.setattr('utils.data_provider.st', st_dummy)
    monkeypatch.setattr('utils.data_provider.safe_api_call_with_retry', lambda func: func())
    monkeypatch.setattr('utils.data_provider.kirim_notifikasi_telegram', lambda msg: None)
    monkeypatch.setattr('utils.data_provider.set_ready', lambda val: None)

    class Client:
        def futures_account(self):
            return '<html><body>Not Found</body></html>'
    result = get_futures_balance(Client())
    assert result == 0.0
    assert st_dummy.errored
