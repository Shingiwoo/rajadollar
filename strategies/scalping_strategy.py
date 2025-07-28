import pandas as pd
from ta.trend import EMAIndicator, SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
import pickle
import os
import logging

MODEL_PATH = "models/model_scalping.pkl"
_ml_model = None

def load_ml_model(path: str | None = None):
    """Muat model ML dari file .pkl sekali saat startup."""
    global _ml_model, MODEL_PATH
    if path:
        MODEL_PATH = path
        _ml_model = None
    if _ml_model is None:
        if os.path.exists(MODEL_PATH):
            with open(MODEL_PATH, "rb") as f:
                _ml_model = pickle.load(f)
            logging.info("ML model loaded successfully.")
        else:
            logging.warning("ML model not found. Defaulting ml_signal = 1")
    return _ml_model

load_ml_model()

def generate_ml_signal(df):
    """Prediksi sinyal ML untuk bar terakhir."""
    model = load_ml_model()
    if model is None:
        df.loc[df.index[-1], 'ml_signal'] = 1
        return df
    features = df[['ema', 'sma', 'macd', 'rsi']].ffill().iloc[-1:]
    if features.isnull().values.any():
        logging.warning("Fitur ML mengandung NaN, default ml_signal = 1")
        pred = 1
    else:
        try:
            pred = int(model.predict(features)[0])
        except Exception as e:
            logging.error(f"Prediksi ML gagal: {e}")
            pred = 1
    df.loc[df.index[-1], 'ml_signal'] = pred
    return df

def apply_indicators(df, config=None, bb_std=2):
    if config is None:
        config = {}
    ema_period = config.get('ema_period', 14)
    sma_period = config.get('sma_period', 14)
    rsi_period = config.get('rsi_period', 14)
    
    # Tambahan: konfigurable MACD param
    macd_fast = config.get('macd_fast', 12)
    macd_slow = config.get('macd_slow', 26)
    macd_signal = config.get('macd_signal', 9)

    # EMA & SMA
    df['ema'] = EMAIndicator(close=df['close'], window=ema_period).ema_indicator()
    df['sma'] = SMAIndicator(close=df['close'], window=sma_period).sma_indicator()

    # MACD (dengan parameter)
    macd_obj = MACD(close=df['close'], window_fast=macd_fast, window_slow=macd_slow, window_sign=macd_signal)
    df['macd'] = macd_obj.macd()
    df['macd_signal'] = macd_obj.macd_signal()

    # RSI
    df['rsi'] = RSIIndicator(close=df['close'], window=rsi_period).rsi()

    # Bollinger Bands & Width
    bb = BollingerBands(df['close'], window=20, window_dev=bb_std)
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_lower'] = bb.bollinger_lband()
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['close']

    # ATR
    df['atr'] = AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()

    return df


def generate_signals(df, score_threshold=1.4):
    # Hitung sinyal ML sebelum kalkulasi teknikal
    if 'ml_signal' not in df.columns:
        df['ml_signal'] = 1
    df = generate_ml_signal(df)

    # Long signal conditions
    cond_long1 = (df['ema'] > df['sma']) & (df['macd'] > df['macd_signal'])
    cond_long2 = (df['rsi'] > 40) & (df['rsi'] < 70)
    cond_long3 = df['ml_signal'] == 1

    df['long_signal'] = (
        cond_long1.astype(int) +
        0.5 * cond_long2.astype(int) +
        cond_long3.astype(int)
    ) >= score_threshold

    # Short signal conditions
    cond_short1 = (df['ema'] < df['sma']) & (df['macd'] < df['macd_signal'])
    cond_short2 = (df['rsi'] > 30) & (df['rsi'] < 60)
    cond_short3 = df['ml_signal'] == 0

    df['short_signal'] = (
        cond_short1.astype(int) +
        0.5 * cond_short2.astype(int) +
        cond_short3.astype(int)
    ) >= score_threshold

    return df
