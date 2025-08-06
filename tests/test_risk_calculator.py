from risk_management.risk_calculator import calculate_order_qty


def test_calculate_order_qty():
    """Pastikan ukuran order sesuai formula baru tanpa undertrade."""
    qty = calculate_order_qty(
        "BTCUSDT",
        entry_price=30000,
        sl=29700,
        capital=1000,
        risk_per_trade=0.01,
        leverage=20,
    )
    # Selisih harga 300 dengan risiko 1% modal (10 USDT) -> qty ≈ 0.0333
    assert round(qty, 6) == round(10 / 300, 6)


if __name__ == "__main__":
    test_calculate_order_qty()
