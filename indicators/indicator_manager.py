"""Pengelola registrasi indikator."""
from typing import Dict, Type, List
import pandas as pd

from .base import BaseIndicator

_registry: Dict[str, Type[BaseIndicator]] = {}


def register_indicator(cls: Type[BaseIndicator]) -> Type[BaseIndicator]:
    _registry[cls.name] = cls
    return cls


def compute_indicators(df: pd.DataFrame, indicators: List[str], params: Dict[str, Dict]) -> pd.DataFrame:
    for name in indicators:
        cls = _registry.get(name)
        if not cls:
            continue
        indicator = cls(**params.get(name, {}))
        result = indicator.compute(df)
        if isinstance(result, pd.Series):
            df[result.name] = result
        else:
            df = df.join(result)
    return df
