import asyncio
from types import SimpleNamespace
import utils.bot_flags as bot_flags
from execution import ws_signal_listener as wsl

class DummySocket:
    def __init__(self, messages):
        self.messages = messages
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass
    async def recv(self):
        if self.messages:
            return self.messages.pop(0)
        await asyncio.sleep(0.01)
        return {}

class DummyBSM:
    def __init__(self, messages):
        self.messages = messages
    def kline_socket(self, symbol, interval="5m"):
        return DummySocket(self.messages)


def test_ws_dummy(monkeypatch):
    async def runner():
        bot_flags.IS_READY = True
        msgs = [{"s": "BTCUSDT", "k": {"x": True}}]
        monkeypatch.setattr(wsl, "BinanceSocketManager", lambda *a, **k: DummyBSM(msgs))
        async def dummy_create(*a, **k):
            async def close_connection():
                pass
            return SimpleNamespace(close_connection=close_connection)
        monkeypatch.setattr(wsl.AsyncClient, "create", dummy_create)
        monkeypatch.setattr(wsl, "fetch_latest_data", lambda *a, **k: __import__('pandas').DataFrame({'close':[1]}))
        monkeypatch.setattr(wsl, "apply_indicators", lambda df, params: df)
        monkeypatch.setattr(wsl, "generate_signals", lambda df, thr: df)

        called = {}
        wsl.register_signal_handler("BTCUSDT", lambda s, row: called.setdefault('s', s))

        dummy_client = type("C", (), {"API_KEY": "a", "API_SECRET": "b", "testnet": True})()
        wsl.start_signal_stream(dummy_client, ["BTCUSDT"], {"BTCUSDT": {"score_threshold": 0}})
        await asyncio.sleep(0.05)
        wsl.stop_signal_stream()
        assert called.get('s') == 'BTCUSDT'

    asyncio.run(runner())

