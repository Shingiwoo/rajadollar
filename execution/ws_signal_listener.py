import asyncio
import nest_asyncio
from binance import AsyncClient, BinanceSocketManager
import streamlit as st
from utils.data_provider import fetch_latest_data
from strategies.scalping_strategy import apply_indicators, generate_signals
import utils.bot_flags as bot_flags
from notifications.notifier import laporkan_error

_loop: asyncio.AbstractEventLoop | None = None

def _ensure_loop() -> asyncio.AbstractEventLoop:
    global _loop
    try:
        _loop = asyncio.get_running_loop()
    except RuntimeError:
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    else:
        nest_asyncio.apply()
    return _loop

signal_callbacks = {}
ws_manager: BinanceSocketManager | None = None
async_client: AsyncClient | None = None
client_global = None
_tasks: dict[str, asyncio.Task] = {}


def register_signal_handler(symbol: str, callback):
    signal_callbacks[symbol.upper()] = callback


async def _socket_runner(symbol: str, strategy_params: dict):
    assert ws_manager is not None
    socket = ws_manager.kline_socket(symbol=symbol.lower(), interval="5m")
    async with socket as s:
        while True:
            try:
                msg = await s.recv()
                if st.session_state.get("stop_signal"):
                    continue
                if msg["k"]["x"]:
                    df = fetch_latest_data(symbol, client_global, interval="5m", limit=100)
                    df = apply_indicators(df, strategy_params[symbol])
                    df = generate_signals(df, strategy_params[symbol]["score_threshold"])
                    last = df.iloc[-1]
                    if symbol in signal_callbacks:
                        signal_callbacks[symbol](symbol, last)
            except asyncio.CancelledError:
                break
            except Exception as e:  # pragma: no cover
                laporkan_error(f"WS signal error: {e}")
                break


def start_signal_stream(client, symbols: list[str], strategy_params):
    """Mulai stream sinyal berdasarkan kline."""
    global ws_manager, client_global, _tasks, async_client
    if not bot_flags.IS_READY or _tasks:
        if not bot_flags.IS_READY:
            print("Bot belum siap, signal stream tidak dimulai")
        return
    client_global = client
    loop = _ensure_loop()
    try:
        async_client = loop.run_until_complete(
            AsyncClient.create(
                api_key=client.API_KEY,
                api_secret=client.API_SECRET,
                testnet=client.testnet,
            )
        )
        ws_manager = BinanceSocketManager(async_client)
    except Exception as e:  # pragma: no cover
        laporkan_error(f"WS signal init error: {e}")
        return

    for sym in symbols:
        try:
            _tasks[sym] = loop.create_task(_socket_runner(sym, strategy_params))
        except Exception as e:
            laporkan_error(f"WS signal task error {sym}: {e}")


def stop_signal_stream() -> None:
    """Hentikan stream sinyal jika aktif."""
    global ws_manager, _tasks, async_client
    for task in _tasks.values():
        task.cancel()
    _tasks.clear()
    loop = _loop or asyncio.get_event_loop()
    if async_client:
        loop.run_until_complete(async_client.close_connection())
    ws_manager = None
    async_client = None


def is_signal_stream_running() -> bool:
    """Periksa apakah signal stream sedang aktif."""
    return bool(_tasks)
