import pytest
from risk_management.risk_calculator import calculate_order_qty

def test_calculate_order_qty():
    # Misal risk_per_trade 0.01, capital 1000, entry 30000, SL 29700, leverage 20
    qty = calculate_order_qty(
        "BTCUSDT", entry_price=30000, sl=29700,
        capital=1000, risk_per_trade=0.01, leverage=20
    )
    assert qty == pytest.approx(0.033333, rel=1e-3)

if __name__ == "__main__":
    test_calculate_order_qty()
