import pandas as pd

from strategies.scalping_strategy import apply_indicators, generate_signals
from risk_management.position_manager import apply_trailing_sl
from execution.order_monitor import check_exit_condition
from risk_management.risk_calculator import calculate_order_qty
from models.trade import Trade


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = 1000,
    score_threshold: float = 1.4,
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

    trig_pct = config.get("trailing_trigger_pct", 0.5) if config else 0.5
    off_pct = config.get("trailing_offset_pct", 0.25) if config else 0.25

    for i in range(len(df)):
        df_slice = df.iloc[: i + 1].copy()
        df_slice = generate_signals(df_slice, score_threshold, symbol, config)
        row = df_slice.iloc[-1]
        price = row["close"]
        time = df_slice.index[-1].isoformat()

        if active_trade:
            hold += 1
            active_trade.trailing_sl = apply_trailing_sl(
                price,
                active_trade.entry_price,
                active_trade.side,
                active_trade.trailing_sl,
                trig_pct,
                off_pct,
            )

            if check_exit_condition(
                price,
                active_trade.trailing_sl,
                active_trade.tp,
                hold,
                100,
                active_trade.side,
            ):
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
                    active_trade = Trade(symbol, "long", time, price, size, sl, tp, trailing_sl=sl)
                    active_trade.margin = margin
                    capital -= margin
            elif allow_short and row.get("short_signal"):
                sl = price * (1 + 0.01)
                tp = price * (1 - 0.02)
                size = calculate_order_qty(symbol, price, sl, capital, risk_pct, leverage)
                margin = price * size / leverage
                if size > 0 and margin <= capital:
                    active_trade = Trade(symbol, "short", time, price, size, sl, tp, trailing_sl=sl)
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

