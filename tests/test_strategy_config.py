import pytest

from utils.strategy_config import validate_manual_params
from utils import strategy_config


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
        "score_threshold": 2.0,
        "ml_weight": 1.0,
        "use_crossover_filter": True,
        "only_trend_15m": True,
    }
    assert validate_manual_params(params)


def test_validate_manual_params_fail():
    params = {"ema_period": 0}
    with pytest.raises(ValueError):
        validate_manual_params(params)


def test_load_strategy_config_default(monkeypatch, tmp_path):
    cfg_path = tmp_path / "strategy.json"
    monkeypatch.setattr(strategy_config, "STRATEGY_CFG_PATH", str(cfg_path))
    cfg = strategy_config.load_strategy_config()
    assert "DEFAULT" in cfg["manual_parameters"]
    assert cfg["manual_parameters"]["DEFAULT"]["ema_period"] == 5


def test_save_and_load_multi_symbol(monkeypatch, tmp_path):
    cfg_path = tmp_path / "strategy.json"
    monkeypatch.setattr(strategy_config, "STRATEGY_CFG_PATH", str(cfg_path))
    cfg_in = {
        "enable_optimizer": False,
        "manual_parameters": {"BTCUSDT": {"ema_period": 10, "sma_period": 20}},
    }
    strategy_config.save_strategy_config(cfg_in)
    cfg_out = strategy_config.load_strategy_config()
    assert cfg_out["manual_parameters"]["BTCUSDT"]["ema_period"] == 10
    assert cfg_out["enable_optimizer"] is False
