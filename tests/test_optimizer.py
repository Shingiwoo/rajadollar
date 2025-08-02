from backtest.optimizer import optimize_strategy


def test_optimize_strategy_runs():
    params, metrics = optimize_strategy("BTCUSDT", n_iter=1)
    assert "ema_period" in params
    assert "Rasio Sharpe" in metrics


if __name__ == "__main__":
    test_optimize_strategy_runs()
