import os
import logging
import time
import datetime as dt
import pickle
from typing import Tuple, Optional

import pandas as pd
import requests
from ta.trend import EMAIndicator, SMAIndicator, MACD
from ta.momentum import RSIIndicator
from sklearn.metrics import accuracy_score

from ml import training


BINANCE_URL = "https://api.binance.com/api/v3/klines"
INTERVAL = "1m"
LIMIT = 1000


def _fetch_historical_klines(symbol: str, days: int = 30) -> pd.DataFrame:
    """Unduh data klines Binance selama `days` hari."""
    end_ts = int(dt.datetime.utcnow().timestamp() * 1000)
    start_ts = end_ts - days * 24 * 60 * 60 * 1000
    all_klines = []
    current = start_ts

    while current < end_ts and len(all_klines) < days * 1440:
        params = {
            "symbol": symbol.upper(),
            "interval": INTERVAL,
            "limit": LIMIT,
            "startTime": current,
        }
        try:
            resp = requests.get(BINANCE_URL, params=params, timeout=10)
            if resp.status_code != 200:
                logging.error("Gagal request Binance: %s", resp.text)
                return pd.DataFrame()
            data = resp.json()
        except Exception as exc:
            logging.error("Error koneksi ke Binance: %s", exc)
            return pd.DataFrame()

        if not data:
            break
        all_klines.extend(data)
        last_open = data[-1][0]
        current = last_open + 60_000
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
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    numeric_cols = ["open", "high", "low", "close", "volume"]
    df[numeric_cols] = df[numeric_cols].astype(float)
    return df


def _apply_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close = pd.to_numeric(df["close"], errors="coerce")
    df["ema"] = EMAIndicator(close, window=14).ema_indicator()
    df["sma"] = SMAIndicator(close, window=14).sma_indicator()
    macd = MACD(close)
    df["macd"] = macd.macd()
    df["rsi"] = RSIIndicator(close, window=14).rsi()
    return df


def _label_data(df: pd.DataFrame) -> pd.DataFrame:
    future_high = df["high"].shift(-1).rolling(3).max().shift(-2)
    future_low = df["low"].shift(-1).rolling(3).min().shift(-2)
    up_thresh = df["close"] * 1.005
    down_thresh = df["close"] * 0.995
    df["label"] = pd.NA
    df.loc[future_high >= up_thresh, "label"] = 1
    df.loc[(future_low <= down_thresh) & (future_high < up_thresh), "label"] = 0
    return df


def _prepare_training_data(symbol: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    df = _fetch_historical_klines(symbol)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    df = _apply_indicators(df)
    df = _label_data(df)
    df = df.dropna(subset=["ema", "sma", "macd", "rsi", "label"])

    cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=7)
    train_df = df[df["time"] < cutoff]
    eval_df = df[df["time"] >= cutoff]
    return train_df, eval_df


def train_from_history(symbol: str) -> Optional[dict]:
    """Unduh data historis, latih model, dan kembalikan hasil."""
    train_df, eval_df = _prepare_training_data(symbol)
    if train_df.empty:
        logging.error("Data training %s tidak mencukupi", symbol)
        return None

    os.makedirs("data/training_data", exist_ok=True)
    csv_path = os.path.join("data/training_data", f"{symbol.upper()}.csv")
    train_df.to_csv(csv_path, index=False)

    acc_train = training.train_model(symbol.upper())
    model_path = os.path.join("models", f"{symbol.upper()}_scalping.pkl")

    acc_eval = None
    if os.path.exists(model_path) and not eval_df.empty:
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        preds = model.predict(eval_df[["ema", "sma", "macd", "rsi"]])
        acc_eval = accuracy_score(eval_df["label"], preds)

    return {"train_accuracy": acc_train, "eval_accuracy": acc_eval, "model": model_path if os.path.exists(model_path) else None}
