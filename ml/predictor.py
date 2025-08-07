import os
import pickle
import logging as log
from typing import Tuple

import numpy as np
import pandas as pd


def predict_ml(df: pd.DataFrame, symbol: str) -> Tuple[int, float]:
    """Prediksi sinyal ML untuk satu simbol."""
    model_path = f"models/{symbol}_scalping_5m.pkl"
    if not os.path.exists(model_path):
        log.warning(f"[ML] Model tidak ditemukan: {model_path}")
        return 1, 0.0
    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)
    except Exception as e:
        log.error(f"[ML] Gagal memuat model {symbol}: {e}")
        return 1, 0.0
    fitur = df[['ema','sma','macd','rsi','atr','bb_width','volume']].ffill().iloc[-1:]
    if fitur.isnull().values.any():
        log.warning("Fitur ML mengandung NaN, default ml_signal = 1")
        return 1, 0.0
    try:
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(fitur)[0]
            konf = float(np.max(proba))
            pred = int(np.argmax(proba))
        else:
            pred = int(model.predict(fitur)[0])
            konf = 0.5
    except Exception as e:
        log.error(f"[ML] Prediksi ML {symbol} gagal: {e}")
        return 1, 0.0
    return pred, konf
