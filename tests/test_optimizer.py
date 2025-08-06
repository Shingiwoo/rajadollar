import json

from backtest.optimizer import optimize_strategy
from utils import strategy_config


def test_optimize_strategy_runs():
    params, metrics = optimize_strategy(
        "BTCUSDT", "1h", "2025-07-01", "2025-07-02", n_iter=1
    )
    assert "ema_period" in params
    assert "Rasio Sharpe" in metrics


def test_optimize_strategy_manual(monkeypatch, tmp_path):
    cfg = {
        "enable_optimizer": False,
        "manual_parameters": {
            "BTCUSDT": {
                "ema_period": 5,
                "sma_period": 22,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
                "rsi_period": 14,
                "bb_window": 20,
                "atr_window": 14,
                "score_threshold": 2.0,
            }
        },
    }
    cfg_path = tmp_path / "strategy.json"
    cfg_path.write_text(json.dumps(cfg))
    monkeypatch.setattr(strategy_config, "STRATEGY_CFG_PATH", str(cfg_path))

    from backtest import optimizer as opt_mod

    def fail(*a, **k):
        raise AssertionError("harusnya tidak jalan")

    monkeypatch.setattr(opt_mod, "load_historical_data", fail)

    params, metrics = opt_mod.optimize_strategy(
        "BTCUSDT", "1h", "2025-07-01", "2025-07-02", n_iter=1
    )
    assert params == cfg["manual_parameters"]["BTCUSDT"]
    assert metrics == {}


if __name__ == "__main__":
    test_optimize_strategy_runs()
