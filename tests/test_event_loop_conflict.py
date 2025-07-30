import asyncio
from types import SimpleNamespace
import utils.bot_flags as bot_flags
from execution import ws_listener as wl

class DummySocket:
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass
    async def recv(self):
        await asyncio.sleep(0.01)
        return {"s": "BTCUSDT", "c": "1"}

class DummyBSM(SimpleNamespace):
    def symbol_ticker_socket(self, symbol):
        return DummySocket()

async def runner():
    bot_flags.IS_READY = True
    monkeypatch = __import__('types').SimpleNamespace(setattr=lambda *a, **k: None)
    wl.AsyncClient.create = lambda *a, **k: SimpleNamespace(close_connection=lambda: None)
    wl.BinanceSocketManager = lambda client: DummyBSM()
    client = SimpleNamespace(API_KEY="a", API_SECRET="b", testnet=True)
    wl.start_price_stream(client, ["BTCUSDT"])
    await asyncio.sleep(0.02)
    wl.stop_price_stream(None)

def test_event_loop_conflict():
    asyncio.run(runner())
