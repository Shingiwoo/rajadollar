import time
import logging
import datetime
from models.trade import Trade
from utils.state_manager import save_state, load_state
from risk_management.position_manager import (
    update_open_positions,
    can_open_new_position,
    is_position_open
)
from risk_management.risk_checker import is_liquidation_risk
from risk_management.risk_calculator import calculate_order_qty
from execution.order_router import (
    safe_futures_create_order,
    adjust_quantity_to_min
)
from execution.slippage_handler import verify_price_before_order
from utils.safe_api import safe_api_call_with_retry
from notifications.notifier import (
    kirim_notifikasi_entry,
    kirim_notifikasi_telegram,
    laporkan_error,
    catat_error,
)
from utils.data_provider import load_symbol_filters
from execution.ws_listener import shared_price

def on_signal(
    symbol, row, client, strategy_params, capital,
    leverage, risk_pct, max_pos, max_sym, max_slip,
    notif_entry=True, notif_error=True
):
    try:
        params = strategy_params[symbol]
        filters = load_symbol_filters(client, [symbol])
        active = load_state()
        open_pos = []
        price = shared_price.get(symbol, row['close'])

        for side in ['long', 'short']:
            signal_flag = row['long_signal'] if side == 'long' else row['short_signal']
            if not signal_flag: continue
            if not can_open_new_position(symbol, max_pos, max_sym, open_pos): continue
            if is_position_open(active, symbol, side): continue
            if is_liquidation_risk(price, side, leverage): continue
            if not verify_price_before_order(client, symbol, "BUY" if side == 'long' else "SELL", price, max_slip / 100): continue

            qty = calculate_order_qty(symbol, price, price * (0.99 if side == 'long' else 1.01), capital, risk_pct, leverage)
            qty = adjust_quantity_to_min(symbol, qty, price, filters)

            order = safe_api_call_with_retry(
                safe_futures_create_order, client, symbol,
                "BUY" if side == 'long' else "SELL", "MARKET", qty, filters
            )

            if order:
                oid = order.get("orderId", str(int(time.time())))
                now = datetime.datetime.now(datetime.UTC).isoformat()
                sl = price * (0.99 if side == 'long' else 1.01)
                tp = price * (1.02 if side == 'long' else 0.98)
                tr_off = params.get("trailing_offset", 0.25)
                trg_thr = params.get("trigger_threshold", 0.5)

                trade = Trade(
                    symbol, side, now, price, qty, sl, tp, sl,
                    order_id=oid,
                    trailing_offset=tr_off,
                    trigger_threshold=trg_thr
                )
                active.append(trade.to_dict())
                save_state(active)
                update_open_positions(symbol, side, qty, price, 'open', open_pos)

                if notif_entry:
                    kirim_notifikasi_entry(symbol, price, sl, tp, qty, oid)

    except Exception as e:
        pesan = f"[WebSocket Entry] {symbol} error: {e}"
        if notif_error:
            laporkan_error(pesan)
        else:
            catat_error(pesan)
        logging.exception(f"on_signal error for {symbol}: {e}")