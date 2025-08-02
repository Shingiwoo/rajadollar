import random
from backtest.data_loader import load_csv
from backtest.engine import run_backtest
from backtest.metrics import calculate_metrics


def optimize_strategy(
    symbol: str,
    n_iter: int = 50,
    step: int = 5,
    start: str | None = None,
    end: str | None = None,
    initial_capital: float = 1000,
):
    """Cari kombinasi parameter terbaik menggunakan pencarian acak."""
    ema_range = list(range(5, 51, step))
    sma_range = list(range(5, 51, step))
    rsi_range = list(range(30, 71, step))

    filepath = f"data/historical_data/1h/{symbol}_1h.csv"
    df = load_csv(filepath, start=start, end=end)

    terbaik_params = None
    terbaik_metrik = None
    terbaik_sharpe = float("-inf")

    for _ in range(n_iter):
        ema = random.choice(ema_range)
        sma = random.choice(sma_range)
        rsi_th = random.choice(rsi_range)
        config = {
            "ema_period": ema,
            "sma_period": sma,
            "rsi_threshold": rsi_th,
        }
        trades, equity, _ = run_backtest(
            df.copy(),
            initial_capital=initial_capital,
            symbol=symbol,
            config=config,
        )
        hasil = calculate_metrics(trades, equity)
        if isinstance(hasil, tuple):
            metrik, _ = hasil
        else:
            metrik = hasil
        sharpe = metrik.get("Rasio Sharpe", float("-inf"))
        if sharpe > terbaik_sharpe:
            terbaik_sharpe = sharpe
            terbaik_params = config
            terbaik_metrik = metrik

    return terbaik_params, terbaik_metrik

