"""Manajer untuk menemukan dan menginisiasi strategi."""
from importlib import import_module
from pkgutil import iter_modules
from typing import Dict, Type

from .base_strategy import BaseStrategy

_registry: Dict[str, Type[BaseStrategy]] = {}


def discover_strategies() -> None:
    """Temukan semua subclass BaseStrategy di paket strategies."""
    for module_info in iter_modules(['strategies']):
        module = import_module(f'strategies.{module_info.name}')
        for attr in dir(module):
            obj = getattr(module, attr)
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseStrategy)
                and obj is not BaseStrategy
            ):
                _registry[obj.__name__] = obj


# Jalankan penemuan saat modul diimport
try:
    discover_strategies()
except Exception:
    # Biarkan sunyi jika paket strategies belum siap
    pass


def get_strategy(name: str) -> BaseStrategy:
    """Dapatkan instance strategi berdasarkan nama kelas."""
    cls = _registry.get(name)
    if not cls:
        raise KeyError(f"Strategi {name} tidak ditemukan")
    return cls()


class StrategyManager:
    """Fasad sederhana untuk mengambil instance strategi."""

    @staticmethod
    def get(name: str) -> BaseStrategy:
        return get_strategy(name)
