import os
import logging
import datetime as dt
import pickle
from pathlib import Path
from typing import Tuple, Optional
import argparse

import pandas as pd
from ta.trend import EMAIndicator, SMAIndicator, MACD
from ta.momentum import RSIIndicator
from sklearn.metrics import accuracy_score

from ml import training
from notifications.notifier import kirim_notifikasi_ml_training
from utils.config_loader import load_global_config
from utils.historical_data import load_historical_data, MAX_DAYS
def _apply_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close = pd.to_numeric(df["close"], errors="coerce")
    df["ema"] = EMAIndicator(close, window=14).ema_indicator()
    df["sma"] = SMAIndicator(close, window=14).sma_indicator()
    macd = MACD(close)
    df["macd"] = macd.macd()
    df["rsi"] = RSIIndicator(close, window=14).rsi()
    logging.info("[ML] Indikator dihitung")
    return df


def _label_data(df: pd.DataFrame) -> pd.DataFrame:
    future_high = df["high"].shift(-1).rolling(3).max().shift(-2)
    future_low = df["low"].shift(-1).rolling(3).min().shift(-2)
    up_thresh = df["close"] * 1.005
    down_thresh = df["close"] * 0.995
    df["label"] = pd.NA
    df.loc[future_high >= up_thresh, "label"] = 1
    df.loc[(future_low <= down_thresh) & (future_high < up_thresh), "label"] = 0
    logging.info("[ML] Label dibuat")
    return df


def label_and_save(
    symbol: str,
    timeframe: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> bool:
    """Pastikan data CSV suatu simbol memiliki kolom label."""
    data_dir = Path("data/training_data")
    data_dir.mkdir(parents=True, exist_ok=True)
    tf = timeframe or load_global_config().get("selected_timeframe", "5m")
    csv_path = data_dir / f"{symbol.upper()}_{tf}.csv"

    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            logging.error("[ML] Gagal membaca %s: %s", csv_path, e)
            return False
        if "label" in df.columns:
            logging.info("[ML] %s sudah memiliki kolom label", csv_path)
            return True
        required = {"open", "high", "low", "close", "volume"}
        if not required.issubset(df.columns):
            logging.error("[ML] Kolom wajib tidak lengkap di %s", csv_path)
            return False
    else:
        if end_date is None:
            end_date = dt.datetime.utcnow().date().isoformat()
        if start_date is None:
            start_date = (pd.to_datetime(end_date) - pd.Timedelta(days=30)).date().isoformat()
        df = load_historical_data(symbol, tf, start_date, end_date)
        if df.empty:
            logging.error("[ML] Data %s tidak tersedia untuk labeling", symbol)
            return False
        df = df.reset_index().rename(columns={"timestamp": "time"})

    df = _apply_indicators(df)
    df = _label_data(df)
    df = df.dropna(subset=["ema", "sma", "macd", "rsi", "label"])
    df = df[df["label"].isin([0, 1])]
    if df.empty:
        logging.error("[ML] Labeling %s menghasilkan data kosong", symbol)
        return False
    df["label"] = df["label"].astype(int)
    df.to_csv(csv_path, index=False)
    logging.info("[ML] Data berlabel disimpan ke %s", csv_path)
    return True


def _prepare_training_data(
    symbol: str, timeframe: str, start_date: str, end_date: str
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    df = load_historical_data(symbol, timeframe, start_date, end_date)
    if df.empty:
        logging.error("Data %s tidak tersedia", symbol)
        return pd.DataFrame(), pd.DataFrame()

    df = df.copy()
    df.reset_index(inplace=True)
    df.rename(columns={"timestamp": "time"}, inplace=True)
    num_cols = ["open", "high", "low", "close", "volume"]
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=["time"] + num_cols)

    df = _apply_indicators(df)
    df = _label_data(df)    
    df = df.dropna(subset=["ema", "sma", "macd", "rsi", "label"])
    df = df[df["label"].isin([0, 1])]
    df["label"] = df["label"].astype(int)
    if len(df) < 10:
        logging.error("Data %s terlalu sedikit setelah diproses", symbol)
        return pd.DataFrame(), pd.DataFrame()

    cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=7)
    train_df = df[df["time"] < cutoff]
    eval_df = df[df["time"] >= cutoff]
    logging.info("[ML] Data training %s: %d baris, evaluasi: %d baris", symbol, len(train_df), len(eval_df))
    return train_df, eval_df


def train_from_history(
    symbol: str,
    timeframe: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Optional[dict]:
    """Unduh data historis, latih model, dan kembalikan hasil."""
    tf = timeframe or load_global_config().get("selected_timeframe", "5m")
    if end_date is None:
        end_date = dt.datetime.utcnow().date().isoformat()
    if start_date is None:
        start_date = (
            pd.to_datetime(end_date) - pd.Timedelta(days=MAX_DAYS.get(tf, 30))
        ).date().isoformat()
    logging.info("[ML] Mulai proses training %s %s", symbol.upper(), tf)
    train_df, eval_df = _prepare_training_data(symbol, tf, start_date, end_date)
    if train_df.empty:
        msg = f"Data training {symbol.upper()} tidak mencukupi"
        logging.error(msg)
        kirim_notifikasi_ml_training(msg)
        return None

    data_dir = Path("data/training_data")
    data_dir.mkdir(parents=True, exist_ok=True)
    if not os.access(data_dir, os.W_OK):
        logging.error("Folder %s tidak bisa ditulis, data tidak disimpan", data_dir)
        return None
    csv_path = data_dir / f"{symbol.upper()}_{tf}.csv"
    pd.concat([train_df, eval_df]).to_csv(csv_path, index=False)
    logging.info("[ML] Data disimpan ke %s", csv_path)

    acc_train = training.train_model(symbol.upper(), tf)
    model_path = Path("models") / f"{symbol.upper()}_scalping_{tf}.pkl"

    acc_eval = None
    if model_path.exists() and not eval_df.empty:
        with model_path.open("rb") as f:
            model = pickle.load(f)
        preds = model.predict(eval_df[["ema", "sma", "macd", "rsi"]])
        preds = preds.astype(int)
        assert set(eval_df["label"].unique()).issubset({0, 1})
        assert set(preds).issubset({0, 1})
        acc_eval = accuracy_score(eval_df["label"], preds)
        logging.info("[ML] Akurasi evaluasi %s: %.2f%%", symbol.upper(), acc_eval * 100)

    info = {
        "train_accuracy": acc_train,
        "eval_accuracy": acc_eval,
        "model": str(model_path) if model_path.exists() else None,
    }
    kirim_notifikasi_ml_training(
        f"{symbol.upper()} train {acc_train:.2%}" + (f", eval {acc_eval:.2%}" if acc_eval is not None else "")
    )
    return info


def main():
    parser = argparse.ArgumentParser(description="Labeling data historis untuk ML")
    parser.add_argument("--symbol", required=True, help="Simbol, mis. BTCUSDT")
    parser.add_argument("--timeframe", "-t", default=None, help="Timeframe data")
    parser.add_argument("--start", required=False, help="Tanggal mulai (YYYY-MM-DD)")
    parser.add_argument("--end", required=False, help="Tanggal akhir (YYYY-MM-DD)")
    args = parser.parse_args()
    if not label_and_save(args.symbol.upper(), args.timeframe, args.start, args.end):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
