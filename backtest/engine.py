import json
import os
import pandas as pd
import logging

from strategies_base.strategy_manager import StrategyManager
from strategies.scalping_strategy import confirm_by_higher_tf
from risk_management.position_manager import apply_trailing_sl
from execution.order_monitor import check_exit_condition
from risk_management.risk_calculator import calculate_order_qty
from models.trade import Trade
from .data_loader import load_csv
from .metrics import calculate_metrics


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = 22,
    score_threshold: float = 2.0,
    symbol: str = "",
    direction: str = "both",
    start: str | None = None,
    end: str | None = None,
    config: dict | None = None,
    timeframe: str = "5m",
    risk_per_trade: float = 1.0,
    leverage: int = 14,
):
    """Jalankan backtest bar-per-bar secara modular.

    Parameter start dan end dapat berupa string waktu yang dapat
    diubah ke pandas.Timestamp.
    """

    df = df.sort_index()
    if start:
        df = df[df.index >= pd.to_datetime(start)]
    if end:
        df = df[df.index <= pd.to_datetime(end)]

    config = config or {}
    config.setdefault("score_threshold", score_threshold)
    strategy = StrategyManager.get("ScalpingStrategy")
    strategy.load_config(config)
    logging.getLogger(__name__).info(
        f"Backtest menggunakan strategi {strategy.__class__.__name__}"
    )
    df = strategy.apply_indicators(df)

    capital = initial_capital
    risk_pct = risk_per_trade / 100
    trades: list[Trade] = []
    active_trade: Trade | None = None
    equity: list[float] = []
    hold = 0
    trade_count: dict[tuple[str, str], int] = {}

    for i in range(len(df)):
        df_slice = df.iloc[: i + 1].copy()
        df_slice = strategy.generate_signals(df_slice, symbol)
        row = df_slice.iloc[-1]
        price = row["close"]
        time = df_slice.index[-1].isoformat()

        if active_trade:
            hold += 1
            step = (
                active_trade.atr_multiplier
                if active_trade.trailing_mode == "atr"
                else active_trade.trailing_offset
            )
            active_trade.trailing_sl = apply_trailing_sl(
                price,
                active_trade.entry_price,
                active_trade.side,
                active_trade.trailing_sl,
                active_trade.trigger_threshold,
                step,
                mode=active_trade.trailing_mode,
                atr=row.get("atr"),
                breakeven_pct=active_trade.breakeven_threshold,
            )

            long_ok, short_ok = confirm_by_higher_tf(df_slice, config)
            need_close = check_exit_condition(
                price,
                active_trade.trailing_sl,
                active_trade.tp,
                hold,
                100,
                active_trade.side,
            )
            if active_trade.side == "long" and short_ok:
                need_close = True
            if active_trade.side == "short" and long_ok:
                need_close = True

            if need_close:
                exit_price = price
                if active_trade.side == "long":
                    pnl = (exit_price - active_trade.entry_price) * active_trade.size
                else:
                    pnl = (active_trade.entry_price - exit_price) * active_trade.size
                capital += active_trade.margin + pnl
                active_trade.exit_price = exit_price
                active_trade.exit_time = time
                active_trade.pnl = pnl
                trades.append(active_trade)
                active_trade = None
                hold = 0

        if not active_trade:
            allow_long = direction in ("long", "both")
            allow_short = direction in ("short", "both")
            hour = df_slice.index[-1].hour
            start_h = config.get("trade_start_hour", 0) if config else 0
            end_h = config.get("trade_end_hour", 24) if config else 24
            if not (start_h <= hour < end_h):
                continue

            date_key = df_slice.index[-1].date().isoformat()
            max_trades = config.get("max_trades_per_day", 4) if config else 4
            count = trade_count.get((symbol, date_key), 0)
            if count >= max_trades:
                continue

            if allow_long and row.get("long_signal"):
                atr_val = row.get("atr", 0) or 0
                min_pct = (config.get("sl_min_pct", 1.0) if config else 1.0) / 100
                sl_atr_mult = config.get("sl_atr_multiplier", 1.5) if config else 1.5
                rr = config.get("tp_rr", 2.0) if config else 2.0
                sl_dist = max(price * min_pct, atr_val * sl_atr_mult)
                sl = price - sl_dist
                tp = price + rr * sl_dist
                risk_use = risk_pct
                conf = row.get("ml_confidence", 0)
                if row.get("signal_mode") == "swing" or conf >= (config.get("high_confidence_th", 0.9) if config else 0.9):
                    risk_use *= 2
                size = calculate_order_qty(symbol, price, sl, capital, risk_use, leverage)
                margin = price * size / leverage
                if size > 0 and margin <= capital:
                    trig = config.get("trailing_trigger_pct", 1.0) if config else 1.0
                    off = config.get("trailing_offset_pct", 0.3) if config else 0.3
                    mode = config.get("trailing_mode", "pct") if config else "pct"
                    atr_mult = config.get("atr_multiplier") if config else None
                    brk = config.get("breakeven_trigger_pct") if config else None
                    if row.get("signal_mode") == "swing":
                        if config:
                            trig = config.get("swing_trailing_trigger_pct", trig * 2)
                            off = config.get("swing_trailing_offset_pct", off * 2)
                            brk = config.get("swing_breakeven_trigger_pct", (brk * 2 if brk else None))
                            atr_mult = config.get("swing_atr_multiplier", atr_mult * 2 if atr_mult else None)
                        else:
                            trig *= 2
                            off *= 2
                            brk = brk * 2 if brk else None
                            atr_mult = atr_mult * 2 if atr_mult else None
                    active_trade = Trade(
                        symbol,
                        "long",
                        time,
                        price,
                        size,
                        sl,
                        tp,
                        trailing_sl=sl,
                        trailing_offset=off,
                        trigger_threshold=trig,
                        trailing_mode=mode,
                        atr_multiplier=atr_mult,
                        breakeven_threshold=brk,
                        atr=row.get("atr"),
                    )
                    active_trade.margin = margin
                    capital -= margin
                    trade_count[(symbol, date_key)] = count + 1
            elif allow_short and row.get("short_signal"):
                atr_val = row.get("atr", 0) or 0
                min_pct = (config.get("sl_min_pct", 1.0) if config else 1.0) / 100
                sl_atr_mult = config.get("sl_atr_multiplier", 1.5) if config else 1.5
                rr = config.get("tp_rr", 2.0) if config else 2.0
                sl_dist = max(price * min_pct, atr_val * sl_atr_mult)
                sl = price + sl_dist
                tp = price - rr * sl_dist
                risk_use = risk_pct
                conf = row.get("ml_confidence", 0)
                if row.get("signal_mode") == "swing" or conf >= (config.get("high_confidence_th", 0.9) if config else 0.9):
                    risk_use *= 2
                size = calculate_order_qty(symbol, price, sl, capital, risk_use, leverage)
                margin = price * size / leverage
                if size > 0 and margin <= capital:
                    trig = config.get("trailing_trigger_pct", 1.0) if config else 1.0
                    off = config.get("trailing_offset_pct", 0.3) if config else 0.3
                    mode = config.get("trailing_mode", "pct") if config else "pct"
                    atr_mult = config.get("atr_multiplier") if config else None
                    brk = config.get("breakeven_trigger_pct") if config else None
                    if row.get("signal_mode") == "swing":
                        if config:
                            trig = config.get("swing_trailing_trigger_pct", trig * 2)
                            off = config.get("swing_trailing_offset_pct", off * 2)
                            brk = config.get("swing_breakeven_trigger_pct", (brk * 2 if brk else None))
                            atr_mult = config.get("swing_atr_multiplier", atr_mult * 2 if atr_mult else None)
                        else:
                            trig *= 2
                            off *= 2
                            brk = brk * 2 if brk else None
                            atr_mult = atr_mult * 2 if atr_mult else None
                    active_trade = Trade(
                        symbol,
                        "short",
                        time,
                        price,
                        size,
                        sl,
                        tp,
                        trailing_sl=sl,
                        trailing_offset=off,
                        trigger_threshold=trig,
                        trailing_mode=mode,
                        atr_multiplier=atr_mult,
                        breakeven_threshold=brk,
                        atr=row.get("atr"),
                    )
                    active_trade.margin = margin
                    capital -= margin
                    trade_count[(symbol, date_key)] = count + 1

        if active_trade:
            if active_trade.side == "long":
                unreal = (price - active_trade.entry_price) * active_trade.size
            else:
                unreal = (active_trade.entry_price - price) * active_trade.size
            equity.append(capital + active_trade.margin + unreal)
        else:
            equity.append(capital)

    equity_df = pd.DataFrame({"equity": equity}, index=df.index[: len(equity)])
    return trades, equity_df, capital


def backtest_symbols(
    symbols: list[str],
    timeframe: str,
    start: str | None = None,
    end: str | None = None,
    export_path: str | None = None,
    **kwargs,
):
    """Jalankan backtest untuk banyak simbol dan simpan metrik.

    Parameter
    ---------
    symbols
        Daftar simbol yang akan diuji.
    timeframe
        Timeframe data (misal ``15m``).
    start, end
        Rentang waktu data.
    export_path
        Jika diberikan, hasil metrik disimpan ke berkas JSON ini.
    kwargs
        Parameter tambahan untuk `run_backtest`.
    """

    hasil: dict[str, dict[str, float]] = {}
    for sym in symbols:
        path = os.path.join(
            "data", "historical_data", timeframe, f"{sym}_{timeframe}.csv"
        )
        df = load_csv(path, start, end)
        trades, equity, _ = run_backtest(
            df,
            symbol=sym,
            start=start,
            end=end,
            timeframe=timeframe,
            **kwargs,
        )
        met = calculate_metrics(trades)
        hasil[sym] = {
            "winrate": met.get("Persentase Menang", 0.0),
            "profit_factor": met.get("Profit Factor", 0.0),
            "trades": met.get("Total Transaksi", 0),
            "avg_win": met.get("Rata-rata Profit", 0.0),
            "avg_loss": met.get("Rata-rata Rugi", 0.0),
        }

    if export_path:
        os.makedirs(os.path.dirname(export_path), exist_ok=True)
        with open(export_path, "w") as fh:
            json.dump(hasil, fh, indent=2)

    return hasil

