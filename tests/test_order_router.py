from execution.order_router import adjust_quantity_to_min

def test_adjust_quantity_to_min():
    symbol_filters = {
        "BTCUSDT": {"minQty": 0.001, "stepSize": 0.001, "minNotional": 5}
    }
    qty = adjust_quantity_to_min("BTCUSDT", 0.0004, 30000, symbol_filters)
    assert qty >= 0.001  # minQty
    print("Qty after adjustment:", qty)

def test_adjust_quantity_to_min_notional():
    symbol_filters = {
        "ETHUSDT": {"minQty": 0.001, "stepSize": 0.001, "minNotional": 5}
    }
    qty = adjust_quantity_to_min("ETHUSDT", 0.0025, 2000, symbol_filters)
    assert qty * 2000 >= 5  # meets minNotional
    assert qty == 0.003
    print("Qty with notional check:", qty)

if __name__ == "__main__":
    test_adjust_quantity_to_min()
