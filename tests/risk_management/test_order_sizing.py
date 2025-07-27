import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from risk_management.risk_calculator import calculate_order_qty


def test_qty_basic():
    qty = calculate_order_qty(
        "BTCUSDT", entry_price=100, sl=99, capital=1000,
        risk_per_trade=0.02, leverage=20
    )
    assert round(qty, 6) == 1.0


def test_qty_zero_diff():
    qty = calculate_order_qty(
        "BTCUSDT", entry_price=100, sl=100, capital=1000,
        risk_per_trade=0.02, leverage=20
    )
    assert qty == 0


