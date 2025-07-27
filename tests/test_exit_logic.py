from risk_management.position_manager import check_exit_condition

def test_check_exit_tp():
    current_price = 105
    trailing_sl = 98
    tp = 104
    sl = 95
    result = check_exit_condition(current_price, trailing_sl, tp, sl, direction="long")
    assert result is True  # Harus exit karena TP tercapai

def test_check_exit_sl():
    current_price = 93
    trailing_sl = 94
    tp = 104
    sl = 95
    result = check_exit_condition(current_price, trailing_sl, tp, sl, direction="long")
    assert result is True  # Harus exit karena SL/trailing breach

def test_check_no_exit():
    current_price = 101
    trailing_sl = 98
    tp = 110
    sl = 95
    result = check_exit_condition(current_price, trailing_sl, tp, sl, direction="long")
    assert result is False  # Belum kena TP/SL
