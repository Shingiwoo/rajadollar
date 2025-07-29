import asyncio
from binance.streams import BinanceSocketManager
import threading
from typing import Dict, Optional

# Variabel global dengan type hint dan penamaan jelas
price_data: Dict[str, float] = {}
price_lock = threading.Lock()
_bsm: BinanceSocketManager | None = None
_tasks: Dict[str, asyncio.Task] = {}

def get_price(symbol: str) -> Optional[float]:
    """Ambil harga terakhir untuk symbol tertentu.
    
    Args:
        symbol: Pair trading (contoh: 'BTCUSDT')
    
    Returns:
        Harga terakhir (float) atau None jika symbol tidak ditemukan
    """
    with price_lock:
        return price_data.get(symbol)

def update_price(symbol: str, price: float) -> None:
    """Perbarui harga untuk symbol tertentu.
    
    Args:
        symbol: Pair trading 
        price: Harga terbaru
    """
    with price_lock:
        price_data[symbol] = price

def clear_prices() -> None:
    """Reset semua data harga yang tersimpan."""
    with price_lock:
        price_data.clear()

def start_price_stream(api_key, api_secret, symbols):
    from binance.client import Client
    from binance.streams import BinanceSocketManager

    client = Client(api_key, api_secret)
    bsm = BinanceSocketManager(client)

    tasks = {}

    async def socket_runner(sock):
        async with sock as stream:
            async for msg in stream:
                print("Price stream:", msg)

    for symbol in symbols:
        sock = bsm.kline_socket(symbol.lower(), interval="5m")
        loop = asyncio.get_event_loop()
        tasks[symbol] = loop.create_task(socket_runner(sock))
    return tasks

    _bsm = BinanceSocketManager(client=client)

    async def socket_runner(socket):
        async with socket as s:
            while True:
                try:
                    msg = await s.recv()
                    symbol = msg["s"]
                    price = float(msg["c"])
                    update_price(symbol, price)
                except Exception as e:  # pragma: no cover
                    print(f"WS price error: {e}")

    for symbol in symbols:
        sock = _bsm.symbol_ticker_socket(symbol.lower())
        _tasks[symbol] = asyncio.create_task(socket_runner(sock))

    return _bsm


def stop_price_stream(twm: BinanceSocketManager | None) -> None:
    """Hentikan stream harga jika aktif."""
    global _tasks
    for task in _tasks.values():
        task.cancel()
    _tasks.clear()


def is_price_stream_running() -> bool:
    """Periksa apakah price stream sedang aktif."""
    return bool(_tasks)

