import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import pickle
import os
import schedule
import time
import threading
import json
import pandas as pd
import os, json
from datetime import datetime
from notifications.notifier import kirim_notifikasi_ml_training

def train_model():
    df = pd.read_csv("data/training_data.csv")  # sesuaikan dengan pathmu
    feature_cols = ["ema", "sma", "macd", "rsi"]  # sesuaikan
    X = df[feature_cols]
    y = df["label"]

    # Split dataset
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train model
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train, y_train)

    # Eval
    acc = model.score(X_test, y_test)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"✅ *ML Training Selesai*\n• Akurasi: `{acc:.2%}`\n• Data: `{len(X)}` baris\n• Jam: `{now}`"
    kirim_notifikasi_ml_training(msg)

    # Simpan log
    os.makedirs("logs", exist_ok=True)
    log_path = f"logs/ml_training_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(log_path, "w") as f:
        log_data = {
            "timestamp": now,
            "accuracy": acc,
            "train_size": len(X_train),
            "test_size": len(X_test)
        }
        json.dump(log_data, f, indent=2)

def run_training_scheduler():
    def train_job():
        print("[SCHEDULE] Melatih model otomatis...")
        dummy_data = pd.DataFrame({
            'close': [100 + i + (i%5) for i in range(200)],
            'rsi': [50 + (i%10) for i in range(200)],
            'macd': [0.1 * (i % 5) for i in range(200)],
            'atr': [1.5 for _ in range(200)],
            'bb_width': [0.02 for _ in range(200)]
        })
        train_model(dummy_data) # type: ignore
        print("[SCHEDULE] ✅ Model berhasil diperbarui (mingguan)")

    schedule.every().monday.at("06:00").do(train_job)
    def loop():
        while True:
            schedule.run_pending()
            time.sleep(60)

    threading.Thread(target=loop, daemon=True).start()