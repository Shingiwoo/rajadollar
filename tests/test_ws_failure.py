import asyncio
import utils.bot_flags as bot_flags
from types import SimpleNamespace
from execution import ws_listener as wl
from execution import ws_signal_listener as sl

class DummyClient(SimpleNamespace):
    pass

class DummySocket:
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass
    async def recv(self):
        await asyncio.sleep(0.01)
        return {"s": "BTCUSDT", "c": "0"}

def test_ws_price_fail(monkeypatch):
    bot_flags.IS_READY = True
    monkeypatch.setattr(wl.AsyncClient, "create", lambda *a, **k: (_ for _ in ()).throw(Exception("fail")))
    client = DummyClient(API_KEY="a", API_SECRET="b", testnet=True)
    res = wl.start_price_stream(client, ["BTCUSDT"])
    assert res is None

def test_ws_signal_fail(monkeypatch):
    bot_flags.IS_READY = True
    monkeypatch.setattr(sl.AsyncClient, "create", lambda *a, **k: (_ for _ in ()).throw(Exception("fail")))
    client = DummyClient(API_KEY="a", API_SECRET="b", testnet=True)
    sl.start_signal_stream(client, ["BTCUSDT"], {"BTCUSDT": {"score_threshold":0, "hybrid_fallback": False}})
    assert not sl.is_signal_stream_running()
