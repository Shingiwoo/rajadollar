import os
import json
import pickle
import datetime
import argparse
import logging
from pathlib import Path
from typing import List

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import (
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from sklearn.metrics import accuracy_score
import schedule
import threading
import time

from notifications.notifier import kirim_notifikasi_ml_training
from utils.logger import LOG_DIR
from utils.config_loader import load_global_config
from .feature_generator import prepare_features

DATA_DIR = Path("data/training_data")
MODEL_DIR = Path("models")
FEATURE_COLS = ["ema", "sma", "macd", "rsi", "atr", "bb_width", "volume"]
MIN_DATA = 100
MIN_ACCURACY = 0.6


def _get_tf(tf: str | None) -> str:
    cfg = load_global_config()
    return tf or cfg.get("selected_timeframe", "5m")


def _load_dataset(symbol: str, timeframe: str) -> pd.DataFrame | None:
    data_dir = Path(DATA_DIR)
    path = data_dir / f"{symbol}_{timeframe}.csv"
    if not path.exists():
        print(f"[ML] Data {path} tidak ditemukan")
        return None
    try:
        df = pd.read_csv(path)
    except Exception as e:
        logging.error(f"[ML] Error membaca {path}: {e}")
        return None
    if "label" not in df.columns:
        print(f"[ML] Data {path} tidak memiliki kolom 'label'")
        return None

    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        df = prepare_features(df)
        missing = [c for c in FEATURE_COLS if c not in df.columns]
        if missing:
            raise ValueError(
                f"Kolom fitur berikut tidak ditemukan di DataFrame: {missing}"
            )

    df = df.dropna(subset=FEATURE_COLS + ["label"])
    df = df[df["label"].isin([0, 1])]
    df["label"] = df["label"].astype(int)
    return df


def _ensure_labeled(symbol: str, timeframe: str) -> bool:
    """Pastikan dataset memiliki kolom label, jika tidak jalankan labeling."""
    data_dir = Path(DATA_DIR)
    path = data_dir / f"{symbol}_{timeframe}.csv"

    needs_label = True
    if path.exists():
        try:
            df_check = pd.read_csv(path, nrows=1)
            needs_label = "label" not in df_check.columns
        except Exception as e:
            logging.error(f"[ML] Gagal membaca {path}: {e}")
            return False

    if needs_label:
        try:
            from ml.historical_trainer import label_and_save
            logging.info(f"[ML] Melabeli data {symbol}...")
            label_and_save(symbol, timeframe)
        except Exception as e:
            logging.error(f"[ML] Proses labeling {symbol} gagal: {e}")
            return False

    if not path.exists():
        logging.warning(f"[ML] File {path} belum ada setelah labeling")
        return False
    try:
        df_check = pd.read_csv(path, nrows=1)
    except Exception as e:
        logging.error(f"[ML] Gagal membaca {path} setelah labeling: {e}")
        return False
    if "label" not in df_check.columns:
        logging.warning(f"[ML] Kolom 'label' masih belum ada di {path}")
        return False
    return True


def train_model(symbol: str, timeframe: str | None = None) -> float:
    """Latih model untuk satu simbol dan kembalikan akurasinya."""
    tf = _get_tf(timeframe)
    if not _ensure_labeled(symbol, tf):
        print(f"[ML] Data {symbol} belum siap, training dilewati")
        return 0.0
    try:
        df = _load_dataset(symbol, tf)
    except ValueError as e:
        logging.error(f"[ML] {e}")
        return 0.0
    if df is None:
        return 0.0

    valid = len(df)
    if valid < MIN_DATA:
        msg = f"⚠️ Data {symbol} kurang dari {MIN_DATA} baris, dilewati."
        print(f"[ML] {msg}")
        kirim_notifikasi_ml_training(msg)
        return 0.0

    X = df[FEATURE_COLS]
    y = df["label"]
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    scores: list[float] = []
    try:
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
        acc = float(scores.mean())
        model.fit(X, y)
    except Exception as e:
        logging.error(f"[ML] Training model {symbol} error: {e}")
        msg = f"⚠️ *ML Training Gagal* {symbol}\n• Error: `{e}`"
        kirim_notifikasi_ml_training(msg)
        return 0.0

    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
    msg = (
         f"✅ *ML Training Selesai* {symbol}\n"
         f"• Akurasi: `{acc:.2%}`\n"
         f"• Data valid: `{valid}` baris\n"
         f"• Jam: `{now}`"
    )
    kirim_notifikasi_ml_training(msg)

    if acc >= MIN_ACCURACY:
        model_dir = Path(MODEL_DIR)
        model_dir.mkdir(parents=True, exist_ok=True)
        if not os.access(model_dir, os.W_OK):
            logging.error("[ML] Folder %s tidak bisa ditulis, model tidak disimpan", model_dir)
        else:
            model_path = model_dir / f"{symbol}_scalping_{tf}.pkl"
            with model_path.open("wb") as f:
                pickle.dump(model, f)
    else:
        print(
            f"[ML] Akurasi {acc:.2%} di bawah ambang {MIN_ACCURACY:.0%}, model tidak disimpan"
        )

    log_dir = Path(LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    if not os.access(log_dir, os.W_OK):
        logging.error("[ML] Folder %s tidak bisa ditulis, log tidak disimpan", log_dir)
    else:
        log_path = log_dir / (
            f"ml_training_{symbol}_{tf}_{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d_%H%M%S')}.txt"
        )
        with log_path.open("w") as f:
            json.dump(
                {
                    "timestamp": now,
                    "accuracy": float(acc),
                    "cv_scores": [float(s) for s in scores],
                    "data": valid,
                },
                f,
                indent=2,
            )

    print(f"[ML] {symbol} selesai dengan akurasi {acc:.2%}")
    return float(acc)

def train_all(symbols: List[str] | None = None, timeframe: str | None = None) -> None:
    tf = _get_tf(timeframe)
    if symbols is None:
        data_dir = Path(DATA_DIR)
        if not data_dir.is_dir():
            print(f"[ML] Folder {data_dir} tidak ada")
            return
        files = list(data_dir.glob(f"*_{tf}.csv"))
        symbols = [p.stem.split("_")[0] for p in files]
    for sym in symbols:
        train_model(sym, tf)


def evaluate_model(symbol: str, timeframe: str | None = None) -> float:
    """Evaluasi model yang sudah tersimpan terhadap data terbaru."""
    tf = _get_tf(timeframe)
    model_path = Path(MODEL_DIR) / f"{symbol}_scalping_{tf}.pkl"
    if not model_path.exists():
        return 0.0
    df = _load_dataset(symbol, tf)
    if df is None:
        return 0.0
    X = df[FEATURE_COLS]
    y = df["label"]
    try:
        _, X_te, _, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
        with model_path.open("rb") as f:
            model = pickle.load(f)
        preds = model.predict(X_te)
        preds = preds.astype(int)
        acc = accuracy_score(y_te, preds)
    except Exception as e:
        logging.error(f"[ML] Evaluasi model {symbol} error: {e}")
        return 0.0

    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    if os.access(log_dir, os.W_OK):
        log_path = log_dir / (
            f"ml_eval_{symbol}_{tf}_{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d_%H%M%S')}.txt"
        )
        with log_path.open("w") as f:
            json.dump({"timestamp": now, "accuracy": float(acc)}, f, indent=2)

    return float(acc)


def monitor_models(symbols: List[str] | None = None, timeframe: str | None = None) -> None:
    """Pantau akurasi model dan retrain jika menurun."""
    tf = _get_tf(timeframe)
    if symbols is None:
        data_dir = Path(DATA_DIR)
        if not data_dir.is_dir():
            return
        files = list(data_dir.glob(f"*_{tf}.csv"))
        symbols = [p.stem.split("_")[0] for p in files]
    for sym in symbols:
        acc = evaluate_model(sym, tf)
        if acc < MIN_ACCURACY:
            logging.info("[ML] Akurasi %s %.2f%% di bawah ambang, retrain", sym, acc * 100)
            train_model(sym, tf)


def run_training_scheduler(symbols: List[str] | None = None, timeframe: str | None = None) -> None:
    def monitor_job():
        print("[SCHEDULE] Memantau model otomatis...")
        monitor_models(symbols, timeframe)
        print("[SCHEDULE] ✅ Monitoring selesai")

    schedule.every().day.at("06:00").do(monitor_job)

    def loop():
        while True:
            schedule.run_pending()
            time.sleep(60)

    threading.Thread(target=loop, daemon=True).start()


def main():
    parser = argparse.ArgumentParser(description="Training model ML per simbol")
    parser.add_argument(
        "--symbol",
        "-s",
        default="all",
        help="Simbol untuk dilatih, gunakan 'all' untuk semua",
    )
    parser.add_argument("--timeframe", "-t", default=None, help="Timeframe data, mis. 5m")
    args = parser.parse_args()

    if args.symbol.lower() == "all":
        train_all(timeframe=args.timeframe)
    else:
        train_model(args.symbol.upper(), args.timeframe)


if __name__ == "__main__":
    main()
