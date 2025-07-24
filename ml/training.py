import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import pickle
import os
import schedule
import time
import threading

def train_model(df, output_path="./models/model_scalping.pkl"):
    df['lag_ret'] = df['close'].pct_change().shift(1)
    df['vol'] = df['close'].rolling(20).std().shift(1)
    features = ['rsi', 'macd', 'atr', 'bb_width', 'lag_ret', 'vol']
    ml_df = df[features].dropna()
    target = (df['close'].shift(-5) > df['close']).astype(int).loc[ml_df.index]

    model = RandomForestClassifier(n_estimators=100)
    model.fit(ml_df, target)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        pickle.dump(model, f)

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
        train_model(dummy_data)
        print("[SCHEDULE] ✅ Model berhasil diperbarui (mingguan)")

    schedule.every().monday.at("06:00").do(train_job)
    def loop():
        while True:
            schedule.run_pending()
            time.sleep(60)

    threading.Thread(target=loop, daemon=True).start()