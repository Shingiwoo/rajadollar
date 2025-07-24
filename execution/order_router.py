from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_MARKET, ORDER_TYPE_LIMIT, TIME_IN_FORCE_GTC

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
