import threading
import time
import logging
import streamlit as st
from datetime import datetime, timezone
from typing import Dict

from execution.order_router import safe_close_order_market
from execution.ws_listener import get_price
from risk_management.position_manager import apply_trailing_sl, check_exit_condition
from utils.state_manager import load_state, save_state
from utils.notifikasi import kirim_notifikasi_exit, kirim_notifikasi_telegram
from database.sqlite_logger import log_trade, get_all_trades
from models.trade import Trade
from risk_management.circuit_breaker import CircuitBreaker


def check_and_close_positions(client, symbol_steps: Dict[str, Dict], notif_exit: bool = True):
    """Cek semua posisi aktif dan tutup jika kena SL/TP/trailing."""
    active = load_state()
    updated = []
    for trade_data in active:
        symbol = trade_data["symbol"]
        side = trade_data["side"]
        price = get_price(symbol)
        if price is None:
            updated.append(trade_data)
            continue

        if trade_data.get("trailing_enabled", True):
            trade_data["trailing_sl"] = apply_trailing_sl(
                price,
                trade_data["entry_price"],
                side,
                trade_data.get("trailing_sl", trade_data["sl"]),
                trade_data.get("trailing_trigger_pct")
                or trade_data.get("trigger_threshold")
                or 0.5,
                trade_data.get("trailing_offset_pct")
                or trade_data.get("trailing_offset")
                or 0.25,
            )

        if check_exit_condition(price, trade_data["trailing_sl"], trade_data["tp"], 0, direction=side):
            order = safe_close_order_market(
                client,
                symbol,
                "SELL" if side == "long" else "BUY",
                trade_data["size"],
                symbol_steps,
            )
            exit_price = price
            trade = Trade(**trade_data)
            trade.exit_price = exit_price
            trade.exit_time = datetime.now(timezone.utc).isoformat()
            trade.pnl = (
                (exit_price - trade.entry_price) * trade.size
                if side == "long"
                else (trade.entry_price - exit_price) * trade.size
            )
            log_trade(trade)
            logging.info(
                f"Auto close {symbol} {side} @ {exit_price} PnL {trade.pnl:.2f}"
            )
            if notif_exit:
                kirim_notifikasi_exit(symbol, exit_price, trade.pnl, trade.order_id)
        else:
            updated.append(trade_data)

    if updated != active:
        save_state(updated)
    return updated


def start_exit_monitor(client, symbol_steps: Dict[str, Dict], interval: float = 1.0, notif_exit: bool = True, loss_limit: float = -50.0):
    stop_event = threading.Event()
    circuit = CircuitBreaker(loss_limit=loss_limit)

    def loop():
        while not stop_event.is_set() and not st.session_state.get("stop_signal"):
            try:
                check_and_close_positions(client, symbol_steps, notif_exit)
                if circuit.check(client, symbol_steps, stop_event):
                    break
            except Exception as e:
                logging.error(f"Exit monitor error: {e}", exc_info=True)
            time.sleep(interval)

    thread = threading.Thread(target=loop, daemon=True)
    try:
        thread.start()
    except Exception as e:
        logging.error(f"Gagal memulai exit monitor: {e}")
        return stop_event, None

    if not thread.is_alive():
        logging.error("Exit monitor thread tidak berjalan saat startup")

    def watcher():
        nonlocal thread
        while not stop_event.is_set() and not st.session_state.get("stop_signal"):
            if not thread.is_alive():
                logging.error("Thread exit monitor mati, restart...")
                thread = threading.Thread(target=loop, daemon=True)
                thread.start()
            time.sleep(5)

    threading.Thread(target=watcher, daemon=True).start()
    return stop_event, thread
