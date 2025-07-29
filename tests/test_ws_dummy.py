import asyncio
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
        monkeypatch.setattr(wsl, "BinanceSocketManager", lambda client=None: DummyBSM(msgs))
        monkeypatch.setattr(wsl, "fetch_latest_data", lambda *a, **k: __import__('pandas').DataFrame({'close':[1]}))
        monkeypatch.setattr(wsl, "apply_indicators", lambda df, params: df)
        monkeypatch.setattr(wsl, "generate_signals", lambda df, thr: df)

        called = {}
        wsl.register_signal_handler("BTCUSDT", lambda s, row: called.setdefault('s', s))

        wsl.start_signal_stream(None, ["BTCUSDT"], {"BTCUSDT": {"score_threshold": 0}})
        await asyncio.sleep(0.05)
        wsl.stop_signal_stream()
        assert called.get('s') == 'BTCUSDT'

    asyncio.run(runner())

