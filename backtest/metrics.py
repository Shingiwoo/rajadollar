"""Perhitungan metrik kinerja hasil backtest."""

from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_metrics(
    trades: list,
    equity_curve: pd.DataFrame | pd.Series | None = None,
):
    """Hitung berbagai metrik kinerja.

    Parameter
    ---------
    trades:
        Daftar objek *Trade* yang sudah selesai.
    equity_curve:
        Deret saldo ekuitas dari waktu ke waktu. Opsional.

    Returns
    -------
    dict | tuple(dict, pd.DataFrame)
        Jika *equity_curve* diberikan, fungsi juga mengembalikan
        DataFrame berisi kurva ekuitas beserta drawdown-nya.
    """

    if not trades:
        return ({}, None) if equity_curve is not None else {}

    df = pd.DataFrame([t.to_dict() for t in trades])

    # ---------------- Metrik dasar ----------------
    total = len(df)
    menang = df[df["pnl"] > 0]
    kalah = df[df["pnl"] <= 0]

    metrik: dict[str, object] = {
        "Total Transaksi": int(total),
        "Persentase Menang": len(menang) / total * 100,
        "Total PnL": df["pnl"].sum(),
        "Rata-rata PnL": df["pnl"].mean(),
        "Rata-rata Profit": menang["pnl"].mean() if not menang.empty else 0.0,
        "Rata-rata Rugi": kalah["pnl"].mean() if not kalah.empty else 0.0,
    }

    # --------------- Profit Factor ---------------
    total_profit = menang["pnl"].sum()
    total_loss = abs(kalah["pnl"].sum())
    if total_loss == 0:
        metrik["Profit Factor"] = float("inf")
    else:
        metrik["Profit Factor"] = total_profit / total_loss

    # --------------- Waktu tahan rata-rata ---------------
    if "exit_time" in df.columns and df["exit_time"].notna().any():
        masuk = pd.to_datetime(df["entry_time"])
        keluar = pd.to_datetime(df["exit_time"])
        durasi = (keluar - masuk).dropna()
        if not durasi.empty:
            metrik["Rata-rata Waktu Tahan"] = durasi.mean()

    # --------------- Rasio Sharpe & Drawdown ---------------
    if equity_curve is not None and not equity_curve.empty:
        eq = (
            equity_curve["equity"]
            if isinstance(equity_curve, pd.DataFrame)
            else equity_curve
        )

        ret = eq.pct_change().dropna()
        if not ret.empty and ret.std() != 0:
            metrik["Rasio Sharpe"] = (
                ret.mean() / ret.std() * np.sqrt(len(ret))
            )
        else:
            metrik["Rasio Sharpe"] = 0.0

        puncak = eq.cummax()
        drawdown = (eq - puncak) / puncak
        metrik["Maksimal Drawdown"] = drawdown.min()

        kurva = pd.DataFrame({"equity": eq, "drawdown": drawdown})
        return metrik, kurva

    return metrik

