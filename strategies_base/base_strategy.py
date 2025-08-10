"""Kelas dasar untuk semua strategi trading."""
from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd


class BaseStrategy(ABC):
    """Strategi dasar dengan dukungan konfigurasi dinamis."""

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        self.config: Dict[str, Any] = config or {}

    def load_config(self, config: Dict[str, Any]) -> None:
        self.config.update(config)

    def apply_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Terapkan indikator ke DataFrame. Override jika perlu."""
        return df

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Hasilkan sinyal trading dari DataFrame."""
        raise NotImplementedError

    def post_process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Langkah opsional setelah sinyal dihasilkan."""
        return df
