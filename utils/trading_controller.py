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
from utils.state_manager import load_state
from execution.order_router import safe_close_order_market
from risk_management.resume_state import save_resume_state

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
    ev, th, circuit = start_exit_monitor(
        cfg["client"],
        symbol_steps,
        notif_exit=cfg.get("notif_exit", True),
        max_dd=cfg.get("max_dd", 50.0),
        max_losses=cfg.get("max_consecutive_losses", 3),
    )
    handles["stop_event"] = ev
    handles["exit_thread"] = th
    handles["circuit_breaker"] = circuit
    handles["client"] = cfg["client"]
    handles["symbol_steps"] = symbol_steps
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
        def handler(symbol, row, cb=cb):
            if publisher:
                publisher(
                    {
                        "symbol": symbol,
                        "score": float(row.get("score", 0)),
                        "long_signal": bool(row.get("long_signal")),
                        "short_signal": bool(row.get("short_signal")),
                        "skip_reason": row.get("skip_reason", ""),
                    }
                )
            if handles["circuit_breaker"].paused or bot_flags.PAUSED:
                return
            cb(symbol, row)

        register_signal_handler(sym, handler)
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


def cut_all(handles: Dict[str, Any]) -> None:
    client = handles.get("client")
    steps = handles.get("symbol_steps", {})
    for trade in load_state():
        safe_close_order_market(
            client,
            trade["symbol"],
            "SELL" if trade["side"] == "long" else "BUY",
            trade["size"],
            steps,
        )
    bot_flags.set_paused(True)
    save_resume_state({"daily_drawdown": 0.0, "consecutive_losses": 0, "paused": True})

