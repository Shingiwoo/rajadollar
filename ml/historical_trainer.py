import os
import logging
import pickle
import pandas as pd
from ta.trend import EMAIndicator, SMAIndicator, MACD
from ta.momentum import RSIIndicator
from sklearn.ensemble import RandomForestClassifier


def _apply_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close = pd.to_numeric(df["close"], errors="coerce")
    df["ema"] = EMAIndicator(close, window=14).ema_indicator()
    df["sma"] = SMAIndicator(close, window=14).sma_indicator()
    macd = MACD(close)
    df["macd"] = macd.macd()
    df["rsi"] = RSIIndicator(close, window=14).rsi()
    return df


def train_from_history(symbol: str) -> None:
    """Latih model sederhana dari data historis untuk simbol."""
    path = f"data/historical_data/1h/{symbol.upper()}_1h.csv"
    if not os.path.exists(path):
        logging.error(f"Historical data {path} tidak ditemukan")
        return
    df = pd.read_csv(path)
    df.columns = [c.lower() for c in df.columns]
    df = _apply_indicators(df)
    df["label"] = (df["close"].shift(-1) > df["close"]).astype(int)
    df = df.dropna(subset=["ema", "sma", "macd", "rsi", "label"])
    if len(df) < 50:
        logging.warning(f"Data {symbol} terlalu sedikit untuk training")
        return
    X = df[["ema", "sma", "macd", "rsi"]]
    y = df["label"]
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    os.makedirs("models", exist_ok=True)
    with open(f"models/{symbol.upper()}_scalping.pkl", "wb") as f:
        pickle.dump(model, f)
    logging.info(f"Model {symbol} berhasil dibuat dari data historis")
