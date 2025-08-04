"""Optimasi parameter strategi secara acak/grid."""

from __future__ import annotations

import json
import logging
import os
import random

from backtest.engine import run_backtest
from backtest.metrics import calculate_metrics
from utils.historical_data import load_historical_data


GRID: dict[str, list] = {
    "ema_period": list(range(5, 51, 5)),
    "sma_period": list(range(5, 51, 5)),
    "rsi_period": list(range(10, 31, 5)),
    "macd_fast": [8, 12, 16],
    "macd_slow": [20, 26, 36],
    "macd_signal": [7, 9, 12],
    "score_threshold": [1.2, 1.5, 1.7, 2.0, 2.2],
    "trailing_offset_pct": [0.15, 0.20, 0.25, 0.30],
    "trailing_trigger_pct": [0.4, 0.5, 0.6, 0.7],
}


def _sample_params() -> dict:
    """Ambil kombinasi parameter secara acak dari GRID."""
    return {k: random.choice(v) for k, v in GRID.items()}


def optimize_strategy(
    symbol: str,
    tf: str,
    start: str,
    end: str,
    n_iter: int = 200,
    initial_capital: float = 1000,
):
    """Cari kombinasi parameter terbaik dan simpan ke strategy_params.json.

    Prioritas seleksi berdasarkan winrate kemudian Profit Factor.
    Target minimum: winrate >= 70% dan Profit Factor > 3.
    """

    df = load_historical_data(symbol, tf, start, end)

    terbaik_params: dict | None = None
    terbaik_metrik: dict | None = None
    overall_params: dict | None = None
    overall_metrik: dict | None = None

    for _ in range(n_iter):
        params = _sample_params()
        trades, equity, _ = run_backtest(
            df.copy(),
            symbol=symbol,
            initial_capital=initial_capital,
            config=params,
            score_threshold=params["score_threshold"],
            timeframe=tf,
            start=start,
            end=end,
        )

        hasil = calculate_metrics(trades, equity)
        metrik = hasil[0] if isinstance(hasil, tuple) else hasil
        metrik.setdefault("Rasio Sharpe", 0.0)
        winrate = metrik.get("Persentase Menang", 0.0)
        pf = metrik.get("Profit Factor", 0.0)

        if overall_params is None or winrate > overall_metrik.get("Persentase Menang", 0.0):
            overall_params, overall_metrik = params, metrik

        if winrate < 70.0 or pf <= 3:
            continue

        if terbaik_params is None:
            terbaik_params, terbaik_metrik = params, metrik
            continue

        best_wr = terbaik_metrik.get("Persentase Menang", 0.0)
        best_pf = terbaik_metrik.get("Profit Factor", 0.0)
        if winrate > best_wr or (winrate == best_wr and pf > best_pf):
            terbaik_params, terbaik_metrik = params, metrik

    if terbaik_params is None:
        logging.warning("Tidak ada kombinasi memenuhi winrate >=70% dan PF>3")
        return overall_params, overall_metrik

    terbaik_params["trailing_enabled"] = True

    path = os.path.join("config", "strategy_params.json")
    if os.path.exists(path):
        with open(path) as f:
            strategi = json.load(f)
    else:
        strategi = {}
    strategi[symbol] = terbaik_params
    with open(path, "w") as f:
        json.dump(strategi, f, indent=2)

    return terbaik_params, terbaik_metrik


__all__ = ["optimize_strategy"]

