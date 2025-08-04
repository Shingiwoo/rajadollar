import os
import logging
import time
import datetime as dt
from pathlib import Path
from typing import Dict

import pandas as pd
import requests

BINANCE_URL = "https://api.binance.com/api/v3/klines"
LIMIT = 1000

MAX_DAYS: Dict[str, int] = {"1m": 60, "5m": 90, "15m": 120, "1h": 180}

TF_ORDER = ["1m", "5m", "15m", "1h"]
TF_TO_PANDAS = {"1m": "1T", "5m": "5T", "15m": "15T", "1h": "1H"}


def _download_binance(symbol: str, tf: str, start_dt: pd.Timestamp, end_dt: pd.Timestamp) -> pd.DataFrame:
    """Unduh data historis dari Binance sesuai rentang waktu."""
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)
    mult = 1
    if tf.endswith("m"):
        mult = int(tf.rstrip("m"))
    elif tf.endswith("h"):
        mult = int(tf.rstrip("h")) * 60

    all_klines = []
    current = start_ts
    while current < end_ts:
        params = {
            "symbol": symbol.upper(),
            "interval": tf,
            "limit": LIMIT,
            "startTime": current,
            "endTime": end_ts,
        }
        try:
            resp = requests.get(BINANCE_URL, params=params, timeout=10)
            if resp.status_code != 200:
                logging.error("Gagal request Binance: %s", resp.text)
                break
            data = resp.json()
        except Exception as exc:  # pragma: no cover - jaringan
            logging.error("Error koneksi ke Binance: %s", exc)
            break
        if not data:
            break
        all_klines.extend(data)
        current = data[-1][0] + mult * 60_000
        time.sleep(0.1)

    if not all_klines:
        return pd.DataFrame()

    df = pd.DataFrame(
        all_klines,
        columns=[
            "time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore",
        ],
    )
    df = df[["time", "open", "high", "low", "close", "volume"]]
    df["timestamp"] = pd.to_datetime(df["time"], unit="ms")
    df.drop(columns=["time"], inplace=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.set_index("timestamp", inplace=True)
    return df


def load_historical_data(symbol: str, tf: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Muat data historis sesuai aturan folder dan validasi rentang."""
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    if tf not in MAX_DAYS:
        raise ValueError(f"Timeframe tidak didukung: {tf}")
    if (end_dt - start_dt).days > MAX_DAYS[tf]:
        raise ValueError(
            f"Rentang tanggal terlalu panjang untuk TF {tf}. Maksimum {MAX_DAYS[tf]} hari."
        )

    folder = Path("data") / "historical_data" / tf
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception as e:
        logging.error(f"Gagal membuat folder '{folder}': {e}")
        raise RuntimeError(
            f"Permission error. Pastikan folder {folder} dapat ditulis user docker. Jalankan: sudo chown -R 1000:1000 data/historical_data"
        )

    filepath = folder / f"{symbol}_{tf}.csv"
    if filepath.exists():
        try:
            df = pd.read_csv(filepath, parse_dates=["timestamp"], index_col="timestamp")
        except Exception:
            df = pd.DataFrame()
        else:
            if not df.empty and df.index.min() <= start_dt and df.index.max() >= end_dt:
                return df.loc[start_dt:end_dt]

    idx = TF_ORDER.index(tf)
    for smaller in TF_ORDER[:idx]:
        src = Path("data") / "historical_data" / smaller / f"{symbol}_{smaller}.csv"
        if src.exists():
            try:
                df_small = pd.read_csv(src, parse_dates=["timestamp"], index_col="timestamp")
            except Exception:
                continue
            df_resampled = (
                df_small
                .resample(TF_TO_PANDAS[tf])
                .agg({
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                })
                .dropna()
            )
            df_resampled.to_csv(filepath)
            if df_resampled.index.min() <= start_dt and df_resampled.index.max() >= end_dt:
                return df_resampled.loc[start_dt:end_dt]

    df_dl = _download_binance(symbol, tf, start_dt, end_dt)
    if df_dl.empty:
        return df_dl
    df_dl.to_csv(filepath)
    return df_dl.loc[start_dt:end_dt]

__all__ = ["load_historical_data", "MAX_DAYS"]
