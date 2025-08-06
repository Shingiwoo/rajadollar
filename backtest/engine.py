import pandas as pd

from strategies.scalping_strategy import (
    apply_indicators,
    generate_signals,
    confirm_by_higher_tf,
)
from risk_management.position_manager import apply_trailing_sl
from execution.order_monitor import check_exit_condition
from risk_management.risk_calculator import calculate_order_qty
from models.trade import Trade


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = 1000,
    score_threshold: float = 1.8,
    symbol: str = "",
    direction: str = "both",
    start: str | None = None,
    end: str | None = None,
    config: dict | None = None,
    timeframe: str = "5m",
    risk_per_trade: float = 1.0,
    leverage: int = 20,
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

    df = apply_indicators(df, config)

    capital = initial_capital
    risk_pct = risk_per_trade / 100
    trades: list[Trade] = []
    active_trade: Trade | None = None
    equity: list[float] = []
    hold = 0

    for i in range(len(df)):
        df_slice = df.iloc[: i + 1].copy()
        df_slice = generate_signals(df_slice, score_threshold, symbol, config)
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
            if allow_long and row.get("long_signal"):
                sl = price * (1 - 0.01)
                tp = price * (1 + 0.02)
                size = calculate_order_qty(symbol, price, sl, capital, risk_pct, leverage)
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
            elif allow_short and row.get("short_signal"):
                sl = price * (1 + 0.01)
                tp = price * (1 - 0.02)
                size = calculate_order_qty(symbol, price, sl, capital, risk_pct, leverage)
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

