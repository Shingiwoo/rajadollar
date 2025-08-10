"""Modul indikator teknikal."""
from .indicator_manager import register_indicator, compute_indicators

# Impor indikator standar agar otomatis terdaftar
def _load_standard() -> None:
    from . import standard  # noqa: F401


try:
    _load_standard()
except Exception:
    pass

__all__ = ["register_indicator", "compute_indicators"]
