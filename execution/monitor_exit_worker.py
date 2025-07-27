import threading
import time
import datetime
from typing import Dict, Any

from execution.order_router import safe_close_order_market
from risk_management.position_manager import apply_trailing_sl, check_exit_condition
from utils.state_manager import load_state, save_state
from notifications.notifier import kirim_notifikasi_exit
from database.sqlite_logger import log_trade
from models.trade import Trade
from execution.ws_listener import shared_price


def process_exit_positions(client, symbol_steps: Dict[str, Any]):
    active = load_state()
    changed = False
    for trade in active[:]:
        symbol = trade["symbol"]
        price = shared_price.get(symbol)
        if price is None:
            continue

        trade["trailing_sl"] = apply_trailing_sl(
            price,
            trade["entry_price"],
            trade["side"],
            trade.get("trailing_sl", trade["sl"]),
            trade.get("trigger_threshold", 0.5),
            trade.get("trailing_offset", 0.25),
        )

        if check_exit_condition(
            price,
            trade["trailing_sl"],
            trade["tp"],
            trade["sl"],
            direction=trade["side"],
        ):
            safe_close_order_market(
                client,
                symbol,
                "SELL" if trade["side"] == "long" else "BUY",
                trade["size"],
                symbol_steps,
            )
            trade["exit_price"] = price
            trade["exit_time"] = datetime.datetime.now(datetime.UTC).isoformat()
            trade["pnl"] = (
                (price - trade["entry_price"]) * trade["size"]
                if trade["side"] == "long"
                else (trade["entry_price"] - price) * trade["size"]
            )
            kirim_notifikasi_exit(symbol, price, trade["pnl"], trade.get("order_id"))
            log_trade(Trade(**trade))
            active.remove(trade)
            changed = True

    if changed:
        save_state(active)


def start_exit_monitor(client, symbol_steps: Dict[str, Any] | None = None, interval: float = 1.0):
    if symbol_steps is None:
        symbol_steps = {}

    def _worker():
        while True:
            process_exit_positions(client, symbol_steps)
            time.sleep(interval)

    th = threading.Thread(target=_worker, daemon=True)
    th.start()
    return th
