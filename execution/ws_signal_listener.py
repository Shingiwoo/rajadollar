import asyncio
from binance.streams import BinanceSocketManager
import streamlit as st
from utils.data_provider import fetch_latest_data
from strategies.scalping_strategy import apply_indicators, generate_signals
import utils.bot_flags as bot_flags

signal_callbacks = {}
ws_manager: BinanceSocketManager | None = None
client_global = None
_tasks: dict[str, asyncio.Task] = {}

def register_signal_handler(symbol: str, callback):
    signal_callbacks[symbol.upper()] = callback

def start_signal_stream(api_key, api_secret, client, symbols: list[str], strategy_params):
    global ws_manager, client_global, _tasks
    if not bot_flags.IS_READY or _tasks:
        if not bot_flags.IS_READY:
            print("Bot belum siap, signal stream tidak dimulai")
        return
    client_global = client
    ws_manager = BinanceSocketManager(api_key=api_key, api_secret=api_secret)

    async def socket_runner(socket):
        async with socket as s:
            while True:
                msg = await s.recv()
                if st.session_state.get("stop_signal"):
                    continue
                symbol = msg["s"]
                if msg["k"]["x"]:
                    df = fetch_latest_data(symbol, client_global, interval="5m", limit=100)
                    df = apply_indicators(df, strategy_params[symbol])
                    df = generate_signals(df, strategy_params[symbol]["score_threshold"])
                    last = df.iloc[-1]
                    if symbol in signal_callbacks:
                        signal_callbacks[symbol](symbol, last)

    for sym in symbols:
        sock = ws_manager.kline_socket(symbol=sym.lower(), interval="5m")
        _tasks[sym] = asyncio.create_task(socket_runner(sock))


def stop_signal_stream() -> None:
    """Hentikan stream sinyal jika aktif."""
    global ws_manager, _tasks
    for task in _tasks.values():
        task.cancel()
    _tasks.clear()
    ws_manager = None


def is_signal_stream_running() -> bool:
    """Periksa apakah signal stream sedang aktif."""
    return bool(_tasks)


