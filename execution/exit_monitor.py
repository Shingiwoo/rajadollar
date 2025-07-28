import threading
import time
from datetime import datetime
from typing import Dict

from execution.order_router import safe_close_order_market
from execution.ws_listener import shared_price
from risk_management.position_manager import apply_trailing_sl, check_exit_condition
from utils.state_manager import load_state, save_state
from notifications.notifier import kirim_notifikasi_exit
from database.sqlite_logger import log_trade
from models.trade import Trade


def check_and_close_positions(client, symbol_steps: Dict[str, Dict], notif_exit: bool = True):
    """Cek semua posisi aktif dan tutup jika kena SL/TP/trailing."""
    active = load_state()
    updated = []
    for trade_data in active:
        symbol = trade_data["symbol"]
        side = trade_data["side"]
        price = shared_price.get(symbol)
        if price is None:
            updated.append(trade_data)
            continue

        trade_data["trailing_sl"] = apply_trailing_sl(
            price,
            trade_data["entry_price"],
            side,
            trade_data.get("trailing_sl", trade_data["sl"]),
            trade_data.get("trigger_threshold") or 0.5,
            trade_data.get("trailing_offset") or 0.25,
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
            trade.exit_time = datetime.utcnow().isoformat()
            trade.pnl = (
                (exit_price - trade.entry_price) * trade.size
                if side == "long"
                else (trade.entry_price - exit_price) * trade.size
            )
            log_trade(trade)
            if notif_exit:
                kirim_notifikasi_exit(symbol, exit_price, trade.pnl, trade.order_id)
        else:
            updated.append(trade_data)

    if updated != active:
        save_state(updated)
    return updated


def start_exit_monitor(client, symbol_steps: Dict[str, Dict], interval: float = 1.0, notif_exit: bool = True):
    stop_event = threading.Event()

    def loop():
        while not stop_event.is_set():
            check_and_close_positions(client, symbol_steps, notif_exit)
            time.sleep(interval)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return stop_event, thread