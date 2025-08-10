import pandas as pd
import pickle
import os
import logging
import numpy as np
from typing import Any

from strategies_base.base_strategy import BaseStrategy
from indicators.indicator_manager import compute_indicators
from utils.config_loader import load_global_config
from utils.historical_data import MAX_DAYS

MODEL_PATH = "models/model_scalping.pkl"
_ml_models: dict[str, Any] = {}
_auto_trained: set[str] = set()

def _get_model_path(symbol: str, timeframe: str | None = None) -> str:
    cfg = load_global_config()
    tf = timeframe or cfg.get("selected_timeframe", "5m")
    return (
        os.path.join("models", f"{symbol.upper()}_scalping_{tf}.pkl")
        if symbol
        else MODEL_PATH
    )

def load_ml_model(symbol: str, path: str | None = None, timeframe: str | None = None) -> Any:
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
            cfg = load_global_config()
            end = pd.Timestamp.utcnow().date().isoformat()
            tf = timeframe or cfg.get("selected_timeframe", "5m")
            start = (
                pd.Timestamp.utcnow() - pd.Timedelta(days=MAX_DAYS.get(tf, 30))
            ).date().isoformat()
            historical_trainer.train_from_history(symbol, timeframe, start, end)
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
    """Prediksi sinyal ML dan confidence untuk bar terakhir."""
    model = load_ml_model(symbol)
    if model is None:
        logging.warning(f"Prediksi ML gagal atau model tidak ada untuk {symbol}, default ml_signal=1")
        df.loc[df.index[-1], 'ml_signal'] = 1
        df.loc[df.index[-1], 'ml_confidence'] = 0.0
        return df

    features = df[
        ['ema', 'sma', 'macd', 'rsi', 'atr', 'bb_width', 'volume']
    ].ffill().iloc[-1:]
    if features.isnull().values.any():
        logging.warning("Fitur ML mengandung NaN, default ml_signal = 1")
        pred = 1
        conf = 0.0
    else:
        try:
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(features)[0]
                conf = float(np.max(proba))
                pred = int(np.argmax(proba))
            else:
                pred = int(model.predict(features)[0])
                conf = 0.5
        except Exception as e:
            logging.error(f"Prediksi ML {symbol} gagal: {e}")
            pred = 1
            conf = 0.0
    df.loc[df.index[-1], 'ml_signal'] = pred
    df.loc[df.index[-1], 'ml_confidence'] = conf
    return df

class ScalpingStrategy(BaseStrategy):
    """Strategi scalping dengan dukungan indikator standar."""

    def apply_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        params = self.config
        ind_list = ["ema", "sma", "macd", "rsi", "bb", "atr"]
        ind_params = {
            "ema": {"window": params.get("ema_period", 14)},
            "sma": {"window": params.get("sma_period", 14)},
            "macd": {
                "fast": params.get("macd_fast", 12),
                "slow": params.get("macd_slow", 26),
                "signal": params.get("macd_signal", 9),
            },
            "rsi": {"window": params.get("rsi_period", 14)},
            "bb": {
                "window": params.get("bb_window", 20),
                "dev": params.get("bb_std", 2),
            },
            "atr": {"window": params.get("atr_period", 14)},
        }
        return compute_indicators(df, ind_list, ind_params)

    def generate_signals(self, df: pd.DataFrame, symbol: str = "") -> pd.DataFrame:
        cfg = self.config
        rsi_th = cfg.get("rsi_threshold", 40)
        long_lower = rsi_th
        long_upper = min(rsi_th + 30, 100)
        short_lower = max(rsi_th - 10, 0)
        short_upper = min(rsi_th + 20, 100)

        ml_conf_th = cfg.get("ml_conf_threshold", 0.7)
        use_hybrid = cfg.get("hybrid_fallback", True)
        ml_weight = cfg.get("ml_weight", 1.0)
        use_crossover = cfg.get("use_crossover_filter", True)
        score_threshold = cfg.get("score_threshold", 2.0)

        if "ml_signal" not in df.columns:
            df["ml_signal"] = 1
        if "ml_confidence" not in df.columns:
            df["ml_confidence"] = 0.0
        df = generate_ml_signal(df, symbol)

        cross_up = (df["ema"] > df["sma"]) & (df["ema"].shift(1) <= df["sma"].shift(1))
        cross_down = (df["ema"] < df["sma"]) & (df["ema"].shift(1) >= df["sma"].shift(1))

        macd_long = df["macd"] > df["macd_signal"]
        macd_short = df["macd"] < df["macd_signal"]
        rsi_long = (df["rsi"] > long_lower) & (df["rsi"] < long_upper)
        rsi_short = (df["rsi"] > short_lower) & (df["rsi"] < short_upper)

        cond_long_ml = (df["ml_signal"] == 1).astype(float)
        cond_short_ml = (df["ml_signal"] == 0).astype(float)

        if use_hybrid and df["ml_confidence"].iloc[-1] < ml_conf_th:
            cond_long_ml.iloc[-1] = 0.0
            cond_short_ml.iloc[-1] = 0.0

        trend_long = cross_up.astype(float) if use_crossover else (df["ema"] > df["sma"]).astype(float)
        trend_short = cross_down.astype(float) if use_crossover else (df["ema"] < df["sma"]).astype(float)

        score_long = (
            trend_long + 0.5 * macd_long.astype(float) + 0.5 * rsi_long.astype(float) + ml_weight * cond_long_ml
        )
        score_short = (
            trend_short + 0.5 * macd_short.astype(float) + 0.5 * rsi_short.astype(float) + ml_weight * cond_short_ml
        )

        df["score_long"] = score_long
        df["score_short"] = score_short
        df["long_signal"] = score_long >= score_threshold
        df["short_signal"] = score_short >= score_threshold

        reason = ""
        min_bb = cfg.get("min_bb_width", 0)
        if df["bb_width"].iloc[-1] < min_bb:
            df.loc[df.index[-1], "long_signal"] = False
            df.loc[df.index[-1], "short_signal"] = False
            reason = "Volatilitas rendah"

        ml_conf = df["ml_confidence"].iloc[-1]
        if use_hybrid and ml_conf < ml_conf_th and not reason:
            if not df["long_signal"].iloc[-1] and not df["short_signal"].iloc[-1]:
                reason = "Confidence ML rendah"
        elif not df["long_signal"].iloc[-1] and not df["short_signal"].iloc[-1] and not reason:
            reason = "Menunggu konfirmasi indikator"

        long_raw = df["long_signal"].copy()
        short_raw = df["short_signal"].copy()
        long_raw_last = bool(long_raw.iloc[-1])
        short_raw_last = bool(short_raw.iloc[-1])

        long_ok, short_ok = confirm_by_higher_tf(df, cfg)
        df["swing_long"] = long_raw & long_ok
        df["swing_short"] = short_raw & short_ok
        if cfg.get("only_trend_15m", True):
            if (long_raw_last and not long_ok) or (short_raw_last and not short_ok):
                reason = "Tidak searah trend 15m"
            df["long_signal"] = long_raw & long_ok
            df["short_signal"] = short_raw & short_ok
        mode = "swing" if df["swing_long"].iloc[-1] or df["swing_short"].iloc[-1] else "scalp"
        df.loc[df.index[-1], "signal_mode"] = mode

        if not df["long_signal"].iloc[-1] and not df["short_signal"].iloc[-1]:
            if not reason:
                if cfg.get("only_trend_15m", True) and (long_raw_last or short_raw_last) and (not long_ok or not short_ok):
                    reason = "Tidak searah trend 15m"
                elif not (df["ema"].iloc[-1] > df["sma"].iloc[-1]) and not (df["ema"].iloc[-1] < df["sma"].iloc[-1]):
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

        df.loc[df.index[-1], "skip_reason"] = reason
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
    df15 = df.resample('15min').agg(ohlc).dropna()
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



def generate_signals_pythontrading_style(df, params: dict | None = None):
    if params is None:
        params = {}
    threshold = params.get('score_threshold', 2.0)
    rsi_low = params.get('rsi_low', 40)
    rsi_high = params.get('rsi_high', 70)
    ml_weight = params.get('ml_weight', 1.0)

    if 'ml_signal' not in df.columns:
        df['ml_signal'] = 1

    trend = (df['ema'] > df['sma']) & (df['macd'] > df['macd_signal'])
    rsi_ok = (df['rsi'] > rsi_low) & (df['rsi'] < rsi_high)
    ml_ok = (df['ml_signal'] == 1)
    score = trend.astype(float) + rsi_ok.astype(float) * 0.5 + ml_ok.astype(float) * ml_weight
    df['long_signal'] = score >= threshold

    trend_s = (df['ema'] < df['sma']) & (df['macd'] < df['macd_signal'])
    rsi_s = (df['rsi'] < (100 - rsi_low)) & (df['rsi'] > (100 - rsi_high))
    ml_s = (df['ml_signal'] == 0)
    score_s = trend_s.astype(float) + rsi_s.astype(float) * 0.5 + ml_s.astype(float) * ml_weight
    df['short_signal'] = score_s >= threshold

    return df


def apply_indicators(df: pd.DataFrame, config: dict | None = None) -> pd.DataFrame:
    strat = ScalpingStrategy(config)
    return strat.apply_indicators(df)


def generate_signals(
    df: pd.DataFrame, score_threshold: float = 2.0, symbol: str = "", config: dict | None = None
) -> pd.DataFrame:
    cfg = config.copy() if config else {}
    cfg.setdefault("score_threshold", score_threshold)
    strat = ScalpingStrategy(cfg)
    return strat.generate_signals(df, symbol)


def generate_signals_legacy(
    df: pd.DataFrame, score_threshold: float = 2.0, symbol: str = "", config: dict | None = None
) -> pd.DataFrame:
    return generate_signals(df, score_threshold, symbol, config)
