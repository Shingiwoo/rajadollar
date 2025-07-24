from strategies.scalping_strategy import apply_indicators, generate_signals
from risk_management.position_manager import apply_trailing_sl
from execution.order_monitor import check_exit_condition
from models.trade import Trade
import pandas as pd

def run_backtest(df, initial_capital=1000, score_threshold=1.4, direction='long'):
    df = apply_indicators(df)
    df = generate_signals(df, score_threshold)

    capital = initial_capital
    trades = []
    active_trade = None
    hold = 0

    for i in range(1, len(df)):
        row = df.iloc[i]
        price = row['close']
        time = df.index[i].isoformat()

        if active_trade:
            hold += 1
            active_trade.trailing_sl = apply_trailing_sl(price, active_trade.entry_price, direction, active_trade.trailing_sl, 0.5, 0.25)

            if check_exit_condition(price, active_trade.trailing_sl, active_trade.tp, hold, 100, direction):
                exit_price = price
                pnl = (exit_price - active_trade.entry_price) * active_trade.size if direction == 'long' else (active_trade.entry_price - exit_price) * active_trade.size
                capital += pnl
                active_trade.exit_price = exit_price
                active_trade.exit_time = time
                active_trade.pnl = pnl
                trades.append(active_trade)
                active_trade = None
                hold = 0

        elif direction == 'long' and row['long_signal']:
            size = capital * 0.05 / row['close']
            sl = row['close'] - 0.01 * row['close']
            tp = row['close'] + 0.02 * row['close']
            active_trade = Trade(row.name, 'long', time, row['close'], size, sl, tp, trailing_sl=sl)

        elif direction == 'short' and row['short_signal']:
            size = capital * 0.05 / row['close']
            sl = row['close'] + 0.01 * row['close']
            tp = row['close'] - 0.02 * row['close']
            active_trade = Trade(row.name, 'short', time, row['close'], size, sl, tp, trailing_sl=sl)

    return trades, capital