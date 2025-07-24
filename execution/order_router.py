import math
from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_MARKET, ORDER_TYPE_LIMIT, TIME_IN_FORCE_GTC
from execution.slippage_handler import verify_price_before_order
from risk_management.risk_checker import is_liquidation_risk

def adjust_to_step(value, step):
    return float(int(value / step) * step)

def safe_futures_create_order(client, symbol, side, type, quantity, symbol_steps, price=None, stopPrice=None, timeInForce=None, closePosition=None, recvWindow=10000):
    step = symbol_steps.get(symbol, {}).get("step", 1.0)
    tick = symbol_steps.get(symbol, {}).get("tick", 0.01)
    qty = adjust_to_step(quantity, step)
    params = {
        "symbol": symbol,
        "side": side,
        "type": type,
        "quantity": qty,
        "recvWindow": recvWindow
    }
    if price is not None:
        params["price"] = adjust_to_step(price, tick)
    if stopPrice is not None:
        params["stopPrice"] = adjust_to_step(stopPrice, tick)
    if timeInForce is not None:
        params["timeInForce"] = timeInForce
    if closePosition is not None:
        params["closePosition"] = closePosition
    return client.futures_create_order(**params)

def execute_entry(client, symbol, side, expected_price, size, leverage, symbol_steps, max_slippage=0.005):
    # Cek anti-slippage
    if not verify_price_before_order(client, symbol, side, expected_price, max_slippage):
        print("Slippage terlalu besar, order dibatalkan.")
        return None

    # Cek risiko likuidasi
    if is_liquidation_risk(expected_price, side, leverage):
        print("Risiko likuidasi tinggi, order dibatalkan.")
        return None

    # Kirim order seperti biasa
    return safe_futures_create_order(
        client, symbol, 'BUY' if side == 'long' else 'SELL', 'MARKET', size, symbol_steps
    )

def adjust_quantity_to_min(symbol, quantity, price, symbol_filters):
    filt = symbol_filters.get(symbol, {})
    min_qty = float(filt.get('minQty', 0.0))
    step = float(filt.get('stepSize', 0.0))
    min_notional = float(filt.get('minNotional', 0.0))
    qty = max(quantity, min_qty)
    precision = int(-math.log10(step)) if step > 0 else 0
    qty = math.floor(qty * (10 ** precision)) / (10 ** precision) if step > 0 else qty
    # pastikan nilai minNotional
    if min_notional > 0 and price * qty < min_notional:
        needed = min_notional / price
        qty = max(qty, needed)
        qty = math.floor(qty * (10 ** precision)) / (10 ** precision) if step > 0 else qty
    return qty
