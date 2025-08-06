import pytest

from utils.strategy_config import validate_manual_params


def test_validate_manual_params_ok():
    params = {
        "ema_period": 5,
        "sma_period": 22,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "rsi_period": 14,
        "bb_window": 20,
        "atr_window": 14,
        "score_threshold": 1.8,
    }
    assert validate_manual_params(params)


def test_validate_manual_params_fail():
    params = {"ema_period": 0}
    with pytest.raises(ValueError):
        validate_manual_params(params)
