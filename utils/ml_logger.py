"""Pasif logger untuk data candlestick dan indikator teknikal."""

from collections import deque
from pathlib import Path
from typing import Dict, Deque, Any

import pandas as pd
from ta.trend import EMAIndicator, SMAIndicator, MACD
from ta.momentum import RSIIndicator


class MLLogger:
    """Logger pasif untuk menyimpan data training per simbol."""

    def __init__(self, window_size: int = 100, data_dir: str = "data/training_data"):
        self.window_size = window_size
        self.buffers: Dict[str, Deque[Dict[str, Any]]] = {}
        self.data_path = Path(data_dir)
        self.data_path.mkdir(parents=True, exist_ok=True)

    def _update_buffer(self, symbol: str, bar: Dict[str, Any]) -> pd.DataFrame:
        buf = self.buffers.setdefault(symbol, deque(maxlen=self.window_size))
        buf.append(bar)
        return pd.DataFrame(list(buf))

    def log_bar(self, symbol: str, bar: Dict[str, Any]) -> None:
        """Catat satu bar dan simpan ke CSV dengan indikator."""
        df = self._update_buffer(symbol, bar)

        close_series = pd.to_numeric(df["close"], errors="coerce")
        ema = EMAIndicator(close_series, window=14).ema_indicator()
        sma = SMAIndicator(close_series, window=14).sma_indicator()
        macd = MACD(close_series).macd()
        rsi = RSIIndicator(close_series, window=14).rsi()

        row = {
            "timestamp": bar.get("timestamp"),
            "open": bar.get("open"),
            "high": bar.get("high"),
            "low": bar.get("low"),
            "close": bar.get("close"),
            "volume": bar.get("volume"),
            "ema": float(ema.iloc[-1]) if not pd.isna(ema.iloc[-1]) else None,
            "sma": float(sma.iloc[-1]) if not pd.isna(sma.iloc[-1]) else None,
            "macd": float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else None,
            "rsi": float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None,
        }

        csv_path = self.data_path / f"{symbol.upper()}.csv"
        file_exists = csv_path.exists()
        pd.DataFrame([row]).to_csv(csv_path, mode="a", header=not file_exists, index=False)

