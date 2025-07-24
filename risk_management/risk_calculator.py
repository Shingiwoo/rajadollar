def calculate_order_qty(symbol, entry_price, sl, capital, risk_per_trade, leverage):
    """
    Menghitung ukuran order (qty) berbasis modal, risk per trade (%), dan risk pip.
    """
    risk_amount = capital * risk_per_trade
    risk_per_pip = abs(entry_price - sl) * leverage
    if risk_per_pip == 0:
        return 0
    qty = risk_amount / risk_per_pip
    return max(0, qty)
