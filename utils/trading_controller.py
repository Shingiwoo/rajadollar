from functools import partial
from typing import Dict, Any
import streamlit as st
import logging

from execution.ws_listener import (
    start_price_stream,
    stop_price_stream,
    is_price_stream_running,
)
from execution.ws_signal_listener import (
    start_signal_stream,
    stop_signal_stream,
    register_signal_handler,
    is_signal_stream_running,
)
from execution.exit_monitor import start_exit_monitor
from execution.signal_entry import on_signal
from utils.data_provider import load_symbol_filters, get_futures_balance
import utils.bot_flags as bot_flags
from utils.resume_helper import handle_resume, sync_with_binance
from notifications.notifier import kirim_notifikasi_telegram
from strategies_base.strategy_manager import StrategyManager

log = logging.getLogger(__name__)


def start_bot(cfg: Dict[str, Any], publisher=None) -> Dict[str, Any]:
    """Mulai semua komponen trading dan kembalikan handle."""
    handles: Dict[str, Any] = {}
    balance = (
        get_futures_balance(cfg["client"])
        if cfg.get("auto_sync")
        else cfg.get("capital", 1000.0)
    )
    if balance == 0.0 or not bot_flags.IS_READY:
        st.error("❌ Balance invalid, bot not started")
        return {}
    strategy_name = cfg.get("strategy", "ScalpingStrategy")
    StrategyManager.get(strategy_name)  # inisiasi dan validasi
    log.info(f"Strategi aktif: {strategy_name}")
    if not is_price_stream_running():
        handles["price_ws"] = start_price_stream(
            cfg["client"], cfg["symbols"]
        )
    else:
        handles["price_ws"] = None

    if not is_signal_stream_running():
        start_signal_stream(
            cfg["client"], cfg["symbols"], cfg["strategy_params"], cfg.get("timeframe", "5m")
        )
    symbol_steps = load_symbol_filters(cfg["client"], cfg["symbols"])
    ev, th = start_exit_monitor(
        cfg["client"], symbol_steps, notif_exit=cfg.get("notif_exit", True), loss_limit=cfg.get("loss_limit", -50.0)
    )
    handles["stop_event"] = ev
    handles["exit_thread"] = th
    for sym in cfg["symbols"]:
        cb = partial(
            on_signal,
            client=cfg["client"],
            strategy_params=cfg["strategy_params"],
            capital=balance,
            leverage=cfg["leverage"],
            risk_pct=cfg["risk_pct"],
            max_pos=cfg["max_pos"],
            max_sym=cfg["max_sym"],
            max_slip=cfg["max_slip"],
            notif_entry=cfg.get("notif_entry", True),
            notif_error=cfg.get("notif_error", True),
        )
        if publisher:
            def combined(symbol, row, cb=cb):
                publisher(
                    {
                        "symbol": symbol,
                        "score": float(row.get("score", 0)),
                        "long_signal": bool(row.get("long_signal")),
                        "short_signal": bool(row.get("short_signal")),
                        "skip_reason": row.get("skip_reason", ""),
                    }
                )
                cb(symbol, row)
            register_signal_handler(sym, combined)
        else:
            register_signal_handler(sym, cb)
    active_positions = handle_resume(
        cfg.get("resume_flag", False), cfg.get("notif_resume", False)
    )
    if cfg.get("resume_flag"):
        sync_with_binance(cfg["client"])
    if active_positions:
        filtered = [t for t in active_positions if t.get("symbol") in cfg["symbols"]]
        if len(filtered) != len(active_positions):
            kirim_notifikasi_telegram(
                "⚠️ Orphan positions ignored: "
                + ", ".join(t.get("symbol") for t in active_positions if t not in filtered)
            )
        active_positions = filtered
    handles["active_positions"] = active_positions
    return handles


def stop_bot(handles: Dict[str, Any]) -> None:
    """Hentikan semua komponen trading."""
    if not handles:
        return
    stop_price_stream(handles.get("price_ws"))
    stop_signal_stream()
    ev = handles.get("stop_event")
    if ev:
        ev.set()

