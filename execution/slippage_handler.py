def verify_price_before_order(client, symbol, side, expected_price, max_slippage=0.005):
    """
    Verifikasi slippage harga sebelum order dieksekusi.
    """
    try:
        ticker = client.futures_symbol_ticker(symbol=symbol)
        current_price = float(ticker['price'])
    except Exception as e:
        print(f"Error getting price: {e}")
        return False
    diff = abs(current_price - expected_price) / expected_price
    return diff <= max_slippage
