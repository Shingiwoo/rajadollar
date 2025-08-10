"""Kumpulan indikator teknikal standar."""
from ta.trend import EMAIndicator as _EMA, SMAIndicator as _SMA, MACD as _MACD
from ta.momentum import RSIIndicator as _RSI
from ta.volatility import BollingerBands as _BB, AverageTrueRange as _ATR
import pandas as pd

from .base import BaseIndicator
from .indicator_manager import register_indicator


@register_indicator
class EMAIndicator(BaseIndicator):
    name = "ema"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        window = self.params.get("window", 14)
        return _EMA(close=df["close"], window=window).ema_indicator().rename(self.name)


@register_indicator
class SMAIndicator(BaseIndicator):
    name = "sma"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        window = self.params.get("window", 14)
        return _SMA(close=df["close"], window=window).sma_indicator().rename(self.name)


@register_indicator
class RSIIndicator(BaseIndicator):
    name = "rsi"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        window = self.params.get("window", 14)
        return _RSI(close=df["close"], window=window).rsi().rename(self.name)


@register_indicator
class MACDIndicator(BaseIndicator):
    name = "macd"

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        fast = self.params.get("fast", 12)
        slow = self.params.get("slow", 26)
        signal = self.params.get("signal", 9)
        macd = _MACD(close=df["close"], window_fast=fast, window_slow=slow, window_sign=signal)
        result = pd.DataFrame({
            "macd": macd.macd(),
            "macd_signal": macd.macd_signal(),
        })
        return result


@register_indicator
class BollingerBandsIndicator(BaseIndicator):
    name = "bb"

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        window = self.params.get("window", 20)
        dev = self.params.get("dev", 2)
        bb = _BB(df["close"], window=window, window_dev=dev)
        return pd.DataFrame({
            "bb_upper": bb.bollinger_hband(),
            "bb_lower": bb.bollinger_lband(),
            "bb_width": (bb.bollinger_hband() - bb.bollinger_lband()) / df["close"],
        })


@register_indicator
class ATRIndicator(BaseIndicator):
    name = "atr"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        window = self.params.get("window", 14)
        atr = _ATR(df["high"], df["low"], df["close"], window=window)
        return atr.average_true_range().rename(self.name)
