import asyncio
import nest_asyncio
from binance import AsyncClient, BinanceSocketManager
import streamlit as st
import logging
from utils.data_provider import fetch_latest_data
from strategies_base.strategy_manager import StrategyManager
from ml.predictor import predict_ml
from database.signal_logger import log_signal, init_db
import utils.bot_flags as bot_flags
from binance.client import Client
from notifications.notifier import laporkan_error, kirim_notifikasi_telegram

log = logging.getLogger(__name__)
_loop: asyncio.AbstractEventLoop | None = None
event_publisher = None  # fungsi untuk broadcast ke WS

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
client_global: Client | None = None
_tasks: dict[str, asyncio.Task] = {}


def apply_indicators(df, params):
    strat = StrategyManager.get("ScalpingStrategy")
    strat.load_config(params)
    log.info(f"Menggunakan strategi {strat.__class__.__name__}")
    return strat.apply_indicators(df)


def generate_signals_pythontrading_style(df, params, symbol: str = ""):
    strat = StrategyManager.get("ScalpingStrategy")
    strat.load_config(params)
    return strat.generate_signals(df, symbol)


def _higher_tf_trend(symbol: str, params: dict) -> tuple[bool, bool]:
    """Validasi arah tren pada timeframe 1H dan 4H."""
    long_ok = short_ok = False
    if client_global is None:
        log.warning(f"[TF] Binance client_global belum siap, skip filter higher TF untuk {symbol}")
        return True, True  # fallback: tidak blok sinyal
    try:
        df1h = fetch_latest_data(symbol, client_global, interval="1h", limit=100)
        df1h = apply_indicators(df1h, params)
        long1 = df1h['ema'].iloc[-1] > df1h['sma'].iloc[-1]
        short1 = df1h['ema'].iloc[-1] < df1h['sma'].iloc[-1]

        df4h = fetch_latest_data(symbol, client_global, interval="4h", limit=100)
        df4h = apply_indicators(df4h, params)
        long4 = df4h['ema'].iloc[-1] > df4h['sma'].iloc[-1]
        short4 = df4h['ema'].iloc[-1] < df4h['sma'].iloc[-1]

        long_ok = long1 and long4
        short_ok = short1 and short4
    except Exception as e:  # pragma: no cover - kegagalan data
        logging.warning(f"Gagal cek higher TF {symbol}: {e}")
        long_ok = short_ok = True
    return long_ok, short_ok


def register_signal_handler(symbol: str, callback):
    signal_callbacks[symbol.upper()] = callback


async def _socket_runner(symbol: str, strategy_params: dict, timeframe: str):
    assert ws_manager is not None
    socket = ws_manager.kline_socket(symbol=symbol.lower(), interval=timeframe)
    async with socket as s:
        idle_notified = False
        logging.info(f"\ud83d\udcf1 {symbol} Loop aktif - menunggu sinyal....")
        while True:
            try:
                if client_global is None:
                    log.warning(f"[WS] Binance client belum tersedia, abaikan sinyal {symbol}")
                    continue
                msg = await s.recv()
                if st.session_state.get("stop_signal"):
                    break
                if msg["k"]["x"]:
                    df = fetch_latest_data(symbol, client_global, interval=timeframe, limit=100)
                    df = apply_indicators(df, strategy_params[symbol])
                    params = strategy_params[symbol]
                    try:
                        ml_sig, ml_conf = predict_ml(df, symbol)
                        df.loc[df.index[-1], 'ml_signal'] = ml_sig
                        df.loc[df.index[-1], 'ml_confidence'] = ml_conf
                    except Exception as e:  # pragma: no cover - fallback jika ML gagal
                        log.warning(f"ML signal {symbol} gagal: {e}")
                        df.loc[df.index[-1], 'ml_signal'] = 1
                        df.loc[df.index[-1], 'ml_confidence'] = 0.0
                    df = generate_signals_pythontrading_style(df, params, symbol)
                    signal_result = df.iloc[-1]
                    if signal_result.get("long_signal") or signal_result.get("short_signal"):
                        tipe = "LONG" if signal_result.get("long_signal") else "SHORT"
                        log.info(
                            f"[LIVE] Sinyal {symbol} ➜ {tipe} | Skor: {signal_result.get('score', '-')}"
                        )
                        log.info(f"[CHECK] signal_result: {signal_result}")
                    long_ok, short_ok = _higher_tf_trend(symbol, strategy_params[symbol])
                    last = signal_result
                    last_long = bool(last.get("long_signal")) and long_ok
                    last_short = bool(last.get("short_signal")) and short_ok
                    last["long_signal"], last["short_signal"] = last_long, last_short
                    if last_long:
                        log_signal(symbol, "long", float(last.get("score_long", 0)))
                    elif last_short:
                        log_signal(symbol, "short", float(last.get("score_short", 0)))
                    if event_publisher:
                        try:
                            event_publisher(
                                {
                                    "symbol": symbol,
                                    "score": float(last.get("score", 0)),
                                    "long_signal": bool(last_long),
                                    "short_signal": bool(last_short),
                                    "skip_reason": last.get("skip_reason", ""),
                                }
                            )
                        except Exception as e:
                            log.warning(f"Publish event gagal: {e}")
                    if symbol in signal_callbacks:
                        signal_callbacks[symbol](symbol, last)
                    if not last.get("long_signal") and not last.get("short_signal"):
                        logging.info(f"Skipped {symbol} - {last.get('skip_reason', 'wait')}")
                        if not idle_notified:
                            kirim_notifikasi_telegram(f"Menunggu sinyal {symbol}...")
                            idle_notified = True
                    else:
                        idle_notified = False
            except asyncio.CancelledError:
                break
            except Exception as e:  # pragma: no cover
                laporkan_error(f"WS signal error: {e}")
                break


def start_signal_stream(client, symbols: list[str], strategy_params, timeframe: str = "5m"):
    """Mulai stream sinyal berdasarkan kline."""
    global ws_manager, client_global, _tasks, async_client
    if not bot_flags.IS_READY or _tasks:
        if not bot_flags.IS_READY:
            print("Bot belum siap, signal stream tidak dimulai")
        return
    client_global = client
    init_db()
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
            _tasks[sym] = loop.create_task(_socket_runner(sym, strategy_params, timeframe))
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
