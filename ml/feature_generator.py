import pandas as pd
from ta.trend import EMAIndicator, SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange, BollingerBands


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if not {"close", "high", "low"}.issubset(df.columns):
        return df

    close = pd.to_numeric(df["close"], errors="coerce")
    high = pd.to_numeric(df["high"], errors="coerce")
    low = pd.to_numeric(df["low"], errors="coerce")

    df["ema"] = EMAIndicator(close, window=14).ema_indicator()
    df["sma"] = SMAIndicator(close, window=14).sma_indicator()
    macd = MACD(close)
    df["macd"] = macd.macd()
    df["rsi"] = RSIIndicator(close, window=14).rsi()

    atr = AverageTrueRange(high, low, close, window=14).average_true_range()
    df["atr"] = atr

    bb = BollingerBands(close, window=20, window_dev=2)
    df["bb_width"] = (bb.bollinger_hband() - bb.bollinger_lband()) / close

    return df
