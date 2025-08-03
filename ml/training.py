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
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import schedule
import threading
import time

from notifications.notifier import kirim_notifikasi_ml_training
from utils.logger import LOG_DIR

DATA_DIR = Path("data/training_data")
MODEL_DIR = Path("models")
FEATURE_COLS = ["ema", "sma", "macd", "rsi"]
MIN_DATA = 100
MIN_ACCURACY = 0.6


def _load_dataset(symbol: str) -> pd.DataFrame | None:
    data_dir = Path(DATA_DIR)
    path = data_dir / f"{symbol}.csv"
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
    df = df.dropna(subset=FEATURE_COLS + ["label"])
    df = df[df["label"].isin([0, 1])]
    df["label"] = df["label"].astype(int)
    return df


def _ensure_labeled(symbol: str) -> bool:
    """Pastikan dataset memiliki kolom label, jika tidak jalankan labeling."""
    data_dir = Path(DATA_DIR)
    path = data_dir / f"{symbol}.csv"

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
            label_and_save(symbol)
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


def train_model(symbol: str) -> float:
    """Latih model untuk satu simbol dan kembalikan akurasinya."""
    if not _ensure_labeled(symbol):
        print(f"[ML] Data {symbol} belum siap, training dilewati")
        return 0.0
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
    try:
        model.fit(X_tr, y_tr)
        preds = model.predict(X_te)
        preds = preds.astype(int)
        assert set(y_te.unique()).issubset({0, 1})
        assert set(preds).issubset({0, 1})
        acc = accuracy_score(y_te, preds)
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
            model_path = model_dir / f"{symbol}_scalping.pkl"
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
            f"ml_training_{symbol}_{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d_%H%M%S')}.txt"
        )
        with log_path.open("w") as f:
            json.dump({"timestamp": now, "accuracy": float(acc), "data": valid}, f, indent=2)

    print(f"[ML] {symbol} selesai dengan akurasi {acc:.2%}")
    return float(acc)

def train_all(symbols: List[str] | None = None) -> None:
    if symbols is None:
        data_dir = Path(DATA_DIR)
        if not data_dir.is_dir():
            print(f"[ML] Folder {data_dir} tidak ada")
            return
        files = list(data_dir.glob("*.csv"))
        symbols = [p.stem for p in files]
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
