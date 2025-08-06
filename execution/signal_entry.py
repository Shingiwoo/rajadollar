import time
import logging
from datetime import datetime, UTC
from typing import Dict, Any, List
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
from notifications.notifier import (
    kirim_notifikasi_entry,
    laporkan_error,
    catat_error,
)
from utils.data_provider import load_symbol_filters
import utils.bot_flags as bot_flags
from execution.ws_listener import get_price  # Ganti shared_price dengan get_price

def on_signal(
    symbol: str,
    row: Dict[str, Any],
    client: Any,
    strategy_params: Dict[str, Dict[str, float]],
    capital: float,
    leverage: int,
    risk_pct: float,
    max_pos: int,
    max_sym: int,
    max_slip: float,
    notif_entry: bool = True,
    notif_error: bool = True
) -> None:
    """Handle new trading signal entry.
    
    Args:
        symbol: Trading symbol (e.g. 'BTCUSDT')
        row: DataFrame row containing signal data
        client: Binance client instance
        strategy_params: Strategy configuration parameters
        capital: Available trading capital
        leverage: Leverage to use
        risk_pct: Risk percentage per trade
        max_pos: Maximum positions allowed
        max_sym: Maximum symbols allowed
        max_slip: Maximum slippage allowed
        notif_entry: Whether to send entry notifications
        notif_error: Whether to send error notifications
    """
    if not bot_flags.IS_READY:
        return
    try:
        params = strategy_params.get(symbol, {})
        filters = load_symbol_filters(client, [symbol])
        active = load_state()
        open_pos: List[Dict[str, Any]] = []
        
        # Perbaikan di sini: gunakan get_price() bukan shared_price
        current_price = get_price(symbol)
        price = current_price if current_price is not None else row.get('close')

        if price is None or not isinstance(price, (int, float)):
            pesan = f"Harga invalid untuk {symbol}, skip order"
            if notif_error:
                laporkan_error(pesan)
            else:
                catat_error(pesan)
            return

        for side in ['long', 'short']:
            signal_flag = row.get('long_signal' if side == 'long' else 'short_signal', False)
            if not signal_flag:
                logging.info(f"Skipped {symbol} - signal_flag False for {side}")
                continue

            if not can_open_new_position(symbol, max_pos, max_sym, open_pos):
                logging.info(f"Skipped {symbol} - max position reached")
                continue

            if is_position_open(active, symbol, side):
                logging.info(f"Skipped {symbol} - position already open")
                continue

            if is_liquidation_risk(price, side, leverage):
                logging.info(f"Skipped {symbol} - liquidation risk")
                continue

            order_side = "BUY" if side == 'long' else "SELL"
            if not verify_price_before_order(client, symbol, order_side, price, max_slip / 100):
                logging.info(f"Skipped {symbol} - price slippage")
                continue

            try:
                client.futures_change_leverage(symbol=symbol, leverage=leverage)
            except Exception as e:
                logging.warning(f"Gagal set leverage {symbol}: {e}")

            # Hitung SL adaptif
            atr_val = row.get('atr', 0) or 0
            min_pct = params.get('sl_min_pct', 1.0) / 100
            sl_atr_mult = params.get('sl_atr_multiplier', 1.5)
            rr = params.get('tp_rr', 2.0)
            sl_dist = max(price * min_pct, atr_val * sl_atr_mult)
            stop_price = price - sl_dist if side == 'long' else price + sl_dist

            qty = calculate_order_qty(symbol, price, stop_price, capital, risk_pct, leverage)
            qty = adjust_quantity_to_min(symbol, qty, price, filters)

            # Execute order
            order = safe_futures_create_order(
                client, symbol, order_side, "MARKET", qty, filters
            )

            if order:
                oid = order.get("orderId", str(int(time.time())))
                now = datetime.now(UTC).isoformat()
                sl = stop_price
                tp = price + rr * sl_dist if side == 'long' else price - rr * sl_dist
                trailing_enabled = params.get("trailing_enabled", True)
                tr_off = params.get("trailing_offset_pct", 0.3)
                trg_thr = params.get("trailing_trigger_pct", 1.0)
                mode = params.get("trailing_mode", "pct")
                atr_mult = params.get("atr_multiplier")
                breakeven_pct = params.get("breakeven_trigger_pct")

                trade = Trade(
                    symbol=symbol,
                    side=side,
                    entry_time=now,
                    entry_price=price,
                    size=qty,
                    sl=sl,
                    tp=tp,
                    trailing_sl=sl,
                    order_id=oid,
                    trailing_offset=tr_off,
                    trigger_threshold=trg_thr,
                    trailing_mode=mode,
                    atr_multiplier=atr_mult,
                    breakeven_threshold=breakeven_pct,
                    atr=atr_val,
                    trailing_enabled=trailing_enabled
                )
                
                active.append(trade.to_dict())
                save_state(active)
                update_open_positions(symbol, side, qty, price, 'open', open_pos)

                if notif_entry:
                    kirim_notifikasi_entry(symbol, price, sl, tp, qty, oid)

    except Exception as e:
        pesan = f"[Signal Entry] {symbol} error: {str(e)}"
        if notif_error:
            laporkan_error(pesan)
        else:
            catat_error(pesan)
        logging.exception(f"Signal entry error for {symbol}")