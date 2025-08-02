"""Laporan hasil backtest."""

from __future__ import annotations

import pandas as pd


def generate_report(trades: list, equity: pd.DataFrame) -> dict:
    """Buat ringkasan laporan backtest.

    Fungsi ini hanya placeholder dan dapat dikembangkan
    lebih lanjut sesuai kebutuhan.
    """
    return {"total_trades": len(trades), "final_equity": equity["equity"].iloc[-1]}
