import math, logging
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

    # round down to valid step size first
    if step > 0:
        qty = math.floor(qty / step) * step

    # ensure notional requirement after rounding
    if min_notional > 0 and price * qty < min_notional:
        needed = min_notional / price
        if step > 0:
            qty = math.ceil(needed / step) * step
        else:
            qty = needed
        qty = max(qty, min_qty)

    # final rounding to the allowed precision
    if step > 0:
        qty = round(qty, precision)

    return qty

def get_mark_price(client, symbol):
    """Ambil harga mark price futures untuk eksekusi close/stop yang aman."""
    try:
        result = client.futures_mark_price(symbol=symbol)
        return float(result['markPrice'])
    except Exception as e:
        logging.error(f"Gagal dapat mark price {symbol}: {e}")
        return None

def get_current_mark_price(client, symbol):
    """Ambil mark price terbaru dari Binance Futures untuk close/stop order."""
    try:
        ticker = client.futures_mark_price(symbol=symbol)
        return float(ticker['markPrice'])
    except Exception as e:
        print(f"[ERROR] Gagal ambil mark price {symbol}: {e}")
        return None

def safe_close_order_market(client, symbol, side, qty, symbol_steps, max_slippage=0.005):
    """Order market close di harga MARK PRICE, aman dari error -4131."""
    mark_price = get_current_mark_price(client, symbol)
    if mark_price is None:
        print(f"[ERROR] Tidak bisa ambil mark price, skip close {symbol}.")
        return None
    # Cek slippage (optional)
    current_price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
    diff = abs(mark_price - current_price) / current_price
    if diff > max_slippage:
        print(f"[WARNING] Mark price {mark_price} terlalu jauh dari harga pasar {current_price}, slippage {diff*100:.2f}%")
    # Patch: Eksekusi order market di harga mark_price (pakai quantity valid)
    try:
        qty_adj = adjust_to_step(qty, symbol_steps[symbol]['step'])
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='MARKET',
            quantity=qty_adj
        )
        return order
    except Exception as e:
        print(f"[ERROR] Gagal close market order {symbol}: {e}")
        return None

