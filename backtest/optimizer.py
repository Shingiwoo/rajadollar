"""Optimasi parameter strategi secara acak/grid."""

from __future__ import annotations

import json
import logging
import os
import random

from concurrent.futures import ThreadPoolExecutor, as_completed

from backtest.engine import run_backtest
from backtest.metrics import calculate_metrics
from utils.historical_data import load_historical_data
from utils.strategy_config import load_strategy_config
from tqdm import tqdm

try:  # streamlit opsional
    import streamlit as st
except Exception:  # pragma: no cover
    st = None


optimal_params_in_memory: dict[str, dict] = {}


# Nilai dasar bila simbol belum memiliki konfigurasi
DEFAULT_BASE = {
    "ema_period": 20,
    "sma_period": 20,
    "rsi_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "score_threshold": 2.0,
    "ml_weight": 1.0,
    "use_crossover_filter": True,
    "only_trend_15m": True,
    "trailing_mode": "pct",
    "atr_multiplier": 1.5,
    "breakeven_trigger_pct": 0.5,
    "trailing_offset_pct": 0.3,
    "trailing_trigger_pct": 1.0,
    "swing_atr_multiplier": 3.0,
    "swing_breakeven_trigger_pct": 1.0,
    "swing_trailing_offset_pct": 0.6,
    "swing_trailing_trigger_pct": 2.0,
}


def build_local_grid(base: dict, delta: float = 0.2) -> dict[str, list]:
    """Buat grid lokal ±delta dari nilai dasar."""
    grid: dict[str, list] = {}
    for k, v in base.items():
        if isinstance(v, bool):
            grid[k] = [v]
        elif isinstance(v, int):
            bawah = max(1, int(v * (1 - delta)))
            atas = max(bawah, int(v * (1 + delta)))
            grid[k] = list(range(bawah, atas + 1))
        elif isinstance(v, float):
            grid[k] = [round(v * (1 + s), 4) for s in (-delta, -delta / 2, 0, delta / 2, delta)]
    return grid


def _sample_params(grid: dict[str, list]) -> dict:
    """Ambil kombinasi parameter secara acak dari grid lokal."""
    return {k: random.choice(v) for k, v in grid.items()}


def optimize_strategy(
    symbol: str,
    tf: str,
    start: str,
    end: str,
    n_iter: int | None = None,
    initial_capital: float = 1000,
    n_jobs: int | None = None,
    max_bars: int | None = None,
    fast_mode: bool = False,
    early_stop: bool = False,
    use_optimizer: bool = True,
):
    """Cari kombinasi parameter terbaik dan simpan ke strategy_params.json.

    Prioritas seleksi berdasarkan winrate kemudian Profit Factor.
    Target minimum: winrate >= 75% dan Profit Factor > 3.
    """

    cfg_strategy = load_strategy_config()
    if not use_optimizer or not cfg_strategy.get("enable_optimizer", True):
        manual = cfg_strategy.get("manual_parameters", {})
        return manual.get(symbol, manual.get("DEFAULT", {})), {}

    n_iter = n_iter or int(os.getenv("N_ITER", 30))
    n_jobs = n_jobs or int(os.getenv("N_JOBS", 2))
    n_jobs = max(1, min(n_jobs, 2))
    max_bars = max_bars or int(os.getenv("MAX_BARS", 1000))

    df = load_historical_data(symbol, tf, start, end)
    if len(df) > max_bars:
        df = df.tail(max_bars)

    # Ambil parameter dasar dari file config
    path = os.path.join("config", "strategy_params.json")
    if os.path.exists(path):
        with open(path) as f:
            base_cfg = json.load(f)
    else:
        base_cfg = {}
    if symbol in optimal_params_in_memory:
        base_cfg[symbol] = optimal_params_in_memory[symbol]
    base_param = base_cfg.get(symbol, DEFAULT_BASE)
    grid = build_local_grid(base_param)

    terbaik_params: dict | None = None
    terbaik_metrik: dict | None = None
    overall_params: dict | None = None
    overall_metrik: dict | None = None
    tried: set[tuple] = set()

    MAX_TRADES = 200
    MIN_WR = 70.0
    MIN_PF = 3.0
    MIN_SHARPE = 1.0
    MIN_AVG = 0.0

    def single_trial(p: dict) -> tuple[dict, dict]:
        trades, equity, _ = run_backtest(
            df.copy(),
            symbol=symbol,
            initial_capital=initial_capital,
            config=p,
            score_threshold=p.get("score_threshold", 2.0),
            timeframe=tf,
            start=start,
            end=end,
        )
        hasil = calculate_metrics(trades, equity)
        metrik = hasil[0] if isinstance(hasil, tuple) else hasil
        metrik.setdefault("Rasio Sharpe", 0.0)
        return p, metrik

    futures = []
    with ThreadPoolExecutor(max_workers=n_jobs) as executor:
        while len(futures) < n_iter:
            params = _sample_params(grid)
            key = tuple(sorted(params.items()))
            if key in tried:
                continue
            tried.add(key)
            futures.append(executor.submit(single_trial, params))

        for fut in tqdm(as_completed(futures), total=len(futures), desc="Optimasi"):
            params, metrik = fut.result()
            winrate = metrik.get("Persentase Menang", 0.0)
            pf = metrik.get("Profit Factor", 0.0)
            sharpe = metrik.get("Rasio Sharpe", 0.0)
            avg = metrik.get("Rata-rata PnL", 0.0)

            if overall_params is None or winrate > overall_metrik.get("Persentase Menang", 0.0):
                overall_params, overall_metrik = params, metrik

            if (
                winrate < MIN_WR
                or pf < MIN_PF
                or sharpe < MIN_SHARPE
                or metrik.get("Total Transaksi", 0) > MAX_TRADES
                or avg < MIN_AVG
            ):
                continue

            if terbaik_params is None:
                terbaik_params, terbaik_metrik = params, metrik
            else:
                best_wr = terbaik_metrik.get("Persentase Menang", 0.0)
                best_pf = terbaik_metrik.get("Profit Factor", 0.0)
                best_sh = terbaik_metrik.get("Rasio Sharpe", 0.0)
                if (
                    winrate > best_wr
                    or (winrate == best_wr and pf > best_pf)
                    or (
                        winrate == best_wr
                        and pf == best_pf
                        and sharpe > best_sh
                    )
                ):
                    terbaik_params, terbaik_metrik = params, metrik

            if early_stop and winrate >= MIN_WR and pf >= MIN_PF:
                break

    if terbaik_params is None:
        logging.warning("Tidak ada kombinasi memenuhi kriteria minimum")
        return overall_params, overall_metrik

    terbaik_params["trailing_enabled"] = True
    base_cfg[symbol] = terbaik_params
    try:
        with open(path, "w") as f:
            json.dump(base_cfg, f, indent=2)
    except PermissionError as e:
        logging.warning(f"Gagal menyimpan ke {path}: {e}")
        if st:
            st.warning(
                f"Gagal menyimpan ke {path} (permission denied). Param optimal hanya tersedia di sesi ini."
            )
            st.info(
                "Perbaiki permission dengan: sudo chown -R 1000:1000 config; sudo chmod -R u+w config"
            )
        optimal_params_in_memory[symbol] = terbaik_params
    else:
        optimal_params_in_memory.pop(symbol, None)

    return terbaik_params, terbaik_metrik


__all__ = ["optimize_strategy", "optimal_params_in_memory"]

