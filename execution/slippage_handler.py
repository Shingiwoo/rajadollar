from utils.safe_api import safe_api_call_with_retry


def verify_price_before_order(client, symbol, side, expected_price, max_slippage=0.005):
    """Verifikasi slippage harga sebelum order dieksekusi."""
    ticker = safe_api_call_with_retry(client.futures_symbol_ticker, symbol=symbol)
    if not ticker:
        print("Error getting price")
        return False
    current_price = float(ticker['price'])
    diff = abs(current_price - expected_price) / expected_price
    return diff <= max_slippage
