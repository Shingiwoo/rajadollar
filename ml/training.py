import os
import json
import pickle
import datetime
import argparse
from typing import List

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import schedule
import threading
import time

from notifications.notifier import kirim_notifikasi_ml_training
from utils.logger import LOG_DIR

DATA_DIR = "data/training_data"
MODEL_DIR = "models"
FEATURE_COLS = ["ema", "sma", "macd", "rsi"]
MIN_DATA = 100
MIN_ACCURACY = 0.6


def _load_dataset(symbol: str) -> pd.DataFrame | None:
    path = os.path.join(DATA_DIR, f"{symbol}.csv")
    if not os.path.exists(path):
        print(f"[ML] Data {path} tidak ditemukan")
        return None
    df = pd.read_csv(path)
    df = df.dropna(subset=FEATURE_COLS + ["label"])
    return df


def train_model(symbol: str) -> float:
    """Latih model untuk satu simbol dan kembalikan akurasinya."""
    df = _load_dataset(symbol)
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
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_tr, y_tr)

    preds = model.predict(X_te)
    acc = accuracy_score(y_te, preds)

    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
    msg = (
        f"✅ *ML Training Selesai* {symbol}\n"
        f"• Akurasi: `{acc:.2%}`\n"
        f"• Data valid: `{valid}` baris\n"
        f"• Jam: `{now}`"
    )
    kirim_notifikasi_ml_training(msg)

    if acc >= MIN_ACCURACY:
        os.makedirs(MODEL_DIR, exist_ok=True)
        with open(os.path.join(MODEL_DIR, f"{symbol}_scalping.pkl"), "wb") as f:
            pickle.dump(model, f)
    else:
        print(
            f"[ML] Akurasi {acc:.2%} di bawah ambang {MIN_ACCURACY:.0%}, model tidak disimpan"
        )

    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(
        LOG_DIR,
        f"ml_training_{symbol}_{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d_%H%M%S')}.txt",
    )
    with open(log_path, "w") as f:
        json.dump({"timestamp": now, "accuracy": acc, "data": valid}, f, indent=2)

    print(f"[ML] {symbol} selesai dengan akurasi {acc:.2%}")
    return acc


def train_all(symbols: List[str] | None = None) -> None:
    if symbols is None:
        if not os.path.isdir(DATA_DIR):
            print(f"[ML] Folder {DATA_DIR} tidak ada")
            return
        files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
        symbols = [os.path.splitext(f)[0] for f in files]
    for sym in symbols:
        train_model(sym)


def run_training_scheduler(symbols: List[str] | None = None) -> None:
    def train_job():
        print("[SCHEDULE] Melatih model otomatis...")
        train_all(symbols)
        print("[SCHEDULE] ✅ Model berhasil diperbarui (mingguan)")

    schedule.every().monday.at("06:00").do(train_job)

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
    args = parser.parse_args()

    if args.symbol.lower() == "all":
        train_all()
    else:
        train_model(args.symbol.upper())


if __name__ == "__main__":
    main()
