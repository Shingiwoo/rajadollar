from execution.order_router import adjust_quantity_to_min

def test_adjust_quantity_to_min():
    symbol_filters = {
        "BTCUSDT": {"minQty": 0.001, "stepSize": 0.001, "minNotional": 5}
    }
    qty = adjust_quantity_to_min("BTCUSDT", 0.0004, 30000, symbol_filters)
    assert qty >= 0.001  # minQty
    print("Qty after adjustment:", qty)

if __name__ == "__main__":
    test_adjust_quantity_to_min()
