import asyncio
import nest_asyncio
from binance import AsyncClient, BinanceSocketManager
import threading
from typing import Dict, Optional

# memastikan loop bisa ditumpuk (untuk Streamlit/tests)
nest_asyncio.apply()
# data harga terakhir
price_data: Dict[str, float] = {}
price_lock = threading.Lock()

_bsm: BinanceSocketManager | None = None
_async_client: AsyncClient | None = None
_tasks: Dict[str, asyncio.Task] = {}


def get_price(symbol: str) -> Optional[float]:
    """Mengambil harga terakhir dari memori."""
    with price_lock:
        return price_data.get(symbol)


def update_price(symbol: str, price: float) -> None:
    """Memperbarui harga pada memori bersama."""
    with price_lock:
        price_data[symbol] = price


def clear_prices() -> None:
    """Mengosongkan data harga."""
    with price_lock:
        price_data.clear()


async def _socket_runner(symbol: str) -> None:
    assert _bsm is not None
    socket = _bsm.symbol_ticker_socket(symbol.lower())
    async with socket as s:
        while True:
            try:
                msg = await s.recv()
                sym = msg["s"]
                price = float(msg["c"])
                update_price(sym, price)
            except asyncio.CancelledError:
                break
            except Exception as e:  # pragma: no cover
                print(f"WS price error: {e}")
                break


def start_price_stream(client, symbols):
    """Memulai websocket harga."""
    global _bsm, _tasks, _async_client
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    try:
        _async_client = loop.run_until_complete(
            AsyncClient.create(
                api_key=client.API_KEY,
                api_secret=client.API_SECRET,
                testnet=client.testnet,
            )
        )
        _bsm = BinanceSocketManager(_async_client)
    except Exception as e:  # pragma: no cover - init error
        print(f"WS init error: {e}")
        return None

    for sym in symbols:
        _tasks[sym] = asyncio.create_task(_socket_runner(sym))
    return _bsm


def stop_price_stream(_: BinanceSocketManager | None) -> None:
    """Menghentikan websocket harga."""
    global _tasks, _bsm, _async_client
    for task in _tasks.values():
        task.cancel()
    _tasks.clear()
    if _async_client:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_async_client.close_connection())
    _bsm = None
    _async_client = None


def is_price_stream_running() -> bool:
    """Mengecek status stream harga."""
    return bool(_tasks)
