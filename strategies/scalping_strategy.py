import pandas as pd
from ta.trend import EMAIndicator, SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from sklearn.base import ClassifierMixin
import pickle
import os
import logging

from utils.config_loader import load_global_config
from utils.historical_data import MAX_DAYS

MODEL_PATH = "models/model_scalping.pkl"
_ml_models: dict[str, ClassifierMixin | None] = {}
_auto_trained: set[str] = set()

def _get_model_path(symbol: str, timeframe: str | None = None) -> str:
    cfg = load_global_config()
    tf = timeframe or cfg.get("selected_timeframe", "5m")
    return (
        os.path.join("models", f"{symbol.upper()}_scalping_{tf}.pkl")
        if symbol
        else MODEL_PATH
    )

def load_ml_model(symbol: str, path: str | None = None, timeframe: str | None = None) -> ClassifierMixin | None:
    """Muat model ML per simbol sekali saat startup."""
    global _ml_models, MODEL_PATH, _auto_trained
    if path:
        MODEL_PATH = path
    if symbol in _ml_models:
        return _ml_models[symbol]

    model_path = _get_model_path(symbol, timeframe)
    if os.path.exists(model_path):
        with open(model_path, "rb") as f:
            _ml_models[symbol] = pickle.load(f)
        logging.info(f"Model ML {symbol or 'default'} berhasil dimuat.")
        return _ml_models[symbol]

    logging.error(f"Model ML untuk {symbol} tidak ditemukan di {model_path}.")

    # Auto-train jika MODE=test dan belum pernah
    if os.getenv("MODE") == "test" and symbol not in _auto_trained:
        logging.info(f"Auto-training model untuk {symbol}...")
        try:
            from ml import historical_trainer
            end = pd.Timestamp.utcnow().date().isoformat()
            start = (
                pd.Timestamp.utcnow() - pd.Timedelta(days=MAX_DAYS.get(tf, 30))
            ).date().isoformat()
            historical_trainer.train_from_history(symbol, tf, start, end)
        except Exception as e:  # pragma: no cover - training bisa gagal
            logging.error(f"Auto-training gagal: {e}")
        _auto_trained.add(symbol)
        if os.path.exists(model_path):
            with open(model_path, "rb") as f:
                _ml_models[symbol] = pickle.load(f)
            logging.info(f"Model ML {symbol} dimuat setelah auto-training.")
            return _ml_models[symbol]

    _ml_models[symbol] = None
    return None

load_ml_model("")

def generate_ml_signal(df, symbol: str = ""):
    """Prediksi sinyal ML untuk bar terakhir."""
    model = load_ml_model(symbol)
    if model is None:
        logging.warning(f"Prediksi ML gagal atau model tidak ada untuk {symbol}, default ml_signal=1")
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
            logging.error(f"Prediksi ML {symbol} gagal: {e}")
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


def confirm_by_higher_tf(df, config=None):
    """Konfirmasi sinyal memakai timeframe lebih besar (15m).

    Jika indeks bukan datetime atau interval bukan 5 menit,
    fungsi mengembalikan konfirmasi True agar tidak menghambat proses.
    """
    if config is None:
        config = {}
    if not isinstance(df.index, pd.DatetimeIndex) or len(df) < 3:
        return True, True

    try:
        delta = (df.index[-1] - df.index[-2]).total_seconds() / 60
    except Exception:
        return True, True
    if delta > 10:  # bukan data 5m
        return True, True

    ohlc = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
    }
    df15 = df.resample('15T').agg(ohlc).dropna()
    if df15.empty:
        return True, True

    min_window = max(
        config.get('ema_period', 20),
        config.get('sma_period', 20),
        config.get('rsi_period', 14),
        config.get('macd_slow', 26),
        20,
    )
    if len(df15) < min_window:
        logging.warning(
            "Data terlalu pendek untuk konfirmasi indikator di TF lebih besar. Tambah range data!"
        )
        return True, True

    try:
        df15 = apply_indicators(df15, config)
    except Exception as e:
        logging.warning(f"apply_indicators gagal (resample 15m): {e}")
        return True, True
    rsi_th = config.get('rsi_threshold', 40)
    long_ok = (
        (df15['ema'] > df15['sma'])
        & (df15['macd'] > df15['macd_signal'])
        & (df15['rsi'] > rsi_th)
    ).iloc[-1]
    short_ok = (
        (df15['ema'] < df15['sma'])
        & (df15['macd'] < df15['macd_signal'])
        & (df15['rsi'] < rsi_th)
    ).iloc[-1]
    return bool(long_ok), bool(short_ok)


def generate_signals(df, score_threshold=1.4, symbol: str = "", config=None):
    if config is None:
        config = {}
    rsi_th = config.get('rsi_threshold', 40)
    long_lower = rsi_th
    long_upper = min(rsi_th + 30, 100)
    short_lower = max(rsi_th - 10, 0)
    short_upper = min(rsi_th + 20, 100)

    # Hitung sinyal ML sebelum kalkulasi teknikal
    if 'ml_signal' not in df.columns:
        df['ml_signal'] = 1
    df = generate_ml_signal(df, symbol)

    # Long signal conditions
    cond_long1 = (df['ema'] > df['sma']) & (df['macd'] > df['macd_signal'])
    cond_long2 = (df['rsi'] > long_lower) & (df['rsi'] < long_upper)
    cond_long3 = df['ml_signal'] == 1

    score_long = (
        cond_long1.astype(float) +
        0.5 * cond_long2.astype(float) +
        cond_long3.astype(float)
    )
    df['score_long'] = score_long
    df['long_signal'] = score_long >= score_threshold

    # Short signal conditions
    cond_short1 = (df['ema'] < df['sma']) & (df['macd'] < df['macd_signal'])
    cond_short2 = (df['rsi'] > short_lower) & (df['rsi'] < short_upper)
    cond_short3 = df['ml_signal'] == 0

    score_short = (
        cond_short1.astype(float) +
        0.5 * cond_short2.astype(float) +
        cond_short3.astype(float)
    )
    df['score_short'] = score_short
    df['short_signal'] = score_short >= score_threshold

    # Konfirmasi timeframe lebih besar
    long_ok, short_ok = confirm_by_higher_tf(df, config)
    df['swing_long'] = df['long_signal'] & long_ok
    df['swing_short'] = df['short_signal'] & short_ok
    mode = 'swing' if df['swing_long'].iloc[-1] or df['swing_short'].iloc[-1] else 'scalp'
    df.loc[df.index[-1], 'signal_mode'] = mode

    reason = ""
    if not df['long_signal'].iloc[-1] and not df['short_signal'].iloc[-1]:
        if not cond_long1.iloc[-1] and not cond_short1.iloc[-1]:
            reason = "MA not aligned"
        else:
            reason = "Score below threshold"
        logging.info(
            f"Skor long {score_long.iloc[-1]:.2f}, short {score_short.iloc[-1]:.2f} < {score_threshold}"
        )
    else:
        logging.info(
            f"Skor long {score_long.iloc[-1]:.2f}, short {score_short.iloc[-1]:.2f}"
        )

    df.loc[df.index[-1], 'skip_reason'] = reason
    return df
