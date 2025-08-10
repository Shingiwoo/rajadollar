"""Kelas dasar indikator."""
from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd


class BaseIndicator(ABC):
    name: str = ""

    def __init__(self, **params: Any) -> None:
        self.params: Dict[str, Any] = params

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.Series | pd.DataFrame:
        raise NotImplementedError
